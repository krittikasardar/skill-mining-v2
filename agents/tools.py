"""
agents/tools.py
Shared LangChain tools used by both V1 and V2 agents.
"""
import json
from langchain_core.tools import tool
from ingestion.embedder import embed_query, embed_texts
from ingestion.indexer import query_collection, get_profile_chunks


# ── Tool 1: Semantic search across all profiles ─────────────────────────────

@tool
def search_profiles(
    query: str,
    n_results: int = 15,
    min_experience_years: int = 0,
    seniority_tier: str = "",
    required_language: str = "",
    has_leadership: bool = False,
) -> str:
    """
    Search GitHub profiles semantically. Use for candidate search queries.

    Args:
        query: natural language search query
        n_results: number of results to return (default 15)
        min_experience_years: filter profiles with at least N years experience
        seniority_tier: filter by tier: junior | mid | senior | staff
        required_language: filter profiles that use this language
        has_leadership: if True, filter for profiles with leadership signals
    """
    embedding = embed_query(query)

    # Build metadata filters
    where_clauses = []

    if min_experience_years > 0:
        where_clauses.append({"experience_years_approx": {"$gte": min_experience_years}})

    if seniority_tier in ("junior", "mid", "senior", "staff"):
        where_clauses.append({"seniority_tier": {"$eq": seniority_tier}})

    if required_language:
        where_clauses.append({"primary_languages": {"$contains": required_language}})

    if has_leadership:
        where_clauses.append({"leadership_signals": {"$ne": "none"}})

    where = None
    if len(where_clauses) == 1:
        where = where_clauses[0]
    elif len(where_clauses) > 1:
        where = {"$and": where_clauses}

    results = query_collection(
        query_embedding=embedding,
        n_results=n_results,
        where=where,
        chunk_types=["profile_summary", "skills_and_stack"],
    )

    return _format_search_results(results)


# ── Tool 2: Fetch all chunks for a specific profile ──────────────────────────

@tool
def get_profile(username: str) -> str:
    """
    Retrieve all indexed chunks for a specific GitHub username.
    Use this for deep profile analysis (Mode 1).

    Args:
        username: GitHub username (exact match)
    """
    result = get_profile_chunks(username)
    docs = result.get("documents", [])
    metas = result.get("metadatas", [])

    if not docs:
        return f"No profile found for username: {username}"

    output = [f"=== Profile: @{username} ===\n"]
    for doc, meta in zip(docs, metas):
        chunk_type = meta.get("chunk_type", "unknown")
        output.append(f"[{chunk_type.upper()}]\n{doc}\n")

    return "\n".join(output)


# ── Tool 3: Targeted skills search ──────────────────────────────────────────

@tool
def search_by_skills(
    skills: str,
    n_results: int = 10,
) -> str:
    """
    Search profiles specifically by technical skills, languages, or frameworks.

    Args:
        skills: comma-separated list of skills/languages/frameworks
        n_results: number of results
    """
    query = f"developer with skills in {skills}"
    embedding = embed_query(query)

    results = query_collection(
        query_embedding=embedding,
        n_results=n_results,
        chunk_types=["skills_and_stack"],
    )
    return _format_search_results(results)


# ── Tool 4: Leadership/role search ──────────────────────────────────────────

@tool
def search_leadership_profiles(
    role_description: str,
    n_results: int = 10,
) -> str:
    """
    Search for profiles with leadership signals: maintainers, org owners,
    open source authors, active code reviewers.

    Args:
        role_description: description of the leadership role needed
        n_results: number of results
    """
    query = f"technical leader {role_description} maintainer open source"
    embedding = embed_query(query)

    results = query_collection(
        query_embedding=embedding,
        n_results=n_results,
        where={"leadership_signals": {"$ne": "none"}},
        chunk_types=["profile_summary"],
    )
    return _format_search_results(results)


# ── Helper ───────────────────────────────────────────────────────────────────

def _format_search_results(results: dict) -> str:
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs:
        return "No matching profiles found."

    output = []
    seen_usernames = set()

    for doc, meta, dist in zip(docs, metas, distances):
        username = meta.get("username", "unknown")
        if username in seen_usernames:
            continue
        seen_usernames.add(username)

        similarity = round(1 - dist, 3)
        seniority = meta.get("seniority_tier", "unknown")
        exp = meta.get("experience_years_approx", 0)
        langs = meta.get("primary_languages", "")
        leadership = meta.get("leadership_signals", "none")

        output.append(
            f"--- @{username} (similarity: {similarity}) ---\n"
            f"Seniority: {seniority} | Experience: ~{exp} years | "
            f"Languages: {langs}\nLeadership: {leadership}\n"
            f"{doc[:600]}{'...' if len(doc) > 600 else ''}\n"
        )

    return "\n".join(output)


# ── Export all tools ─────────────────────────────────────────────────────────

ALL_TOOLS = [search_profiles, get_profile, search_by_skills, search_leadership_profiles]
