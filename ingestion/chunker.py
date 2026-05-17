"""
ingestion/chunker.py
Produces 3 chunk types per profile as natural language passages:
  1. profile_summary    — identity + aggregate signals
  2. skills_and_stack   — languages, topics, tech evolution
  3. repo_detail        — one chunk per repo (top N by stars)

Each chunk returns: { id, type, text, metadata }
"""
from typing import Any

MAX_REPOS_TO_CHUNK = 20  # cap to avoid excessive chunks for prolific devs


def _safe_str_list(items: list) -> list[str]:
    """Convert a list of str or dict to a list of strings safely."""
    result = []
    for item in items:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            # Try common name fields
            val = item.get("name") or item.get("login") or item.get("full_name") or str(item)
            result.append(val)
        else:
            result.append(str(item))
    return result


def build_chunks(profile: dict) -> list[dict]:
    chunks = []
    username = profile.get("username", "unknown")

    chunks.append(_profile_summary_chunk(profile, username))
    chunks.append(_skills_stack_chunk(profile, username))

    repos = sorted(
        profile.get("repositories", []),
        key=lambda r: r.get("stars", 0),
        reverse=True
    )[:MAX_REPOS_TO_CHUNK]

    for i, repo in enumerate(repos):
        chunk = _repo_detail_chunk(repo, profile, username, i)
        if chunk:
            chunks.append(chunk)

    return chunks


# ── Chunk builders ──────────────────────────────────────────────────────────

def _profile_summary_chunk(p: dict, username: str) -> dict:
    name = p.get("name") or username
    bio = p.get("bio", "") or ""
    company = p.get("company", "") or ""
    location = p.get("location", "") or ""
    years = p.get("years_on_github", 0)
    exp_years = p.get("experience_years_approx", years)
    followers = p.get("followers", 0)
    commits = p.get("total_commits", 0)
    prs_merged = p.get("total_prs_merged", 0)
    issues_closed = p.get("total_issues_closed", 0)
    streak = p.get("longest_streak_months", 0)
    trend = p.get("activity_trend", "stable")
    recent = p.get("recent_6m_commits", 0)
    seniority = p.get("seniority_tier", "unknown")
    leadership = p.get("leadership_signals", "none")
    readme = (p.get("profile_readme", "") or "")[:500]
    pinned = ", ".join(_safe_str_list(p.get("pinned_repositories", [])))
    orgs = ", ".join(_safe_str_list(p.get("organisations", [])))
    ext = p.get("external_contributions", 0)

    text = f"""{name} (GitHub: @{username}) is a software developer with approximately \
{exp_years} years of experience on GitHub, categorised as {seniority} level. \
{f'Based at {location}. ' if location else ''}\
{f'Works at {company}. ' if company else ''}\
{bio + ' ' if bio else ''}\
They have {followers} followers and have made {commits} total commits, \
merged {prs_merged} pull requests, and closed {issues_closed} issues. \
Their longest contribution streak is {streak} months, with {recent} commits \
in the last 6 months. Activity trend: {trend}. \
External contributions to other projects: {ext}. \
Leadership signals: {leadership}. \
{f'Pinned repositories: {pinned}. ' if pinned else ''}\
{f'Member of organisations: {orgs}. ' if orgs else ''}\
{f'Profile README: {readme}' if readme else ''}""".strip()

    return {
        "id": f"{username}__profile_summary",
        "type": "profile_summary",
        "text": text,
        "metadata": _base_metadata(p, username, "profile_summary"),
    }


def _skills_stack_chunk(p: dict, username: str) -> dict:
    name = p.get("name") or username
    primary_langs = p.get("primary_languages", "") or ""
    all_topics = p.get("all_topics", "") or ""
    tech_evolution = p.get("tech_evolution", [])
    top_repos = p.get("top_repos_summary", "") or ""
    seniority = p.get("seniority_tier", "unknown")
    impact = p.get("has_open_source_impact", False)

    tech_evo_text = ""
    if tech_evolution:
        evo_items = []
        for t in tech_evolution:
            if isinstance(t, dict):
                evo_items.append(t.get("language") or t.get("name") or t.get("year") or str(t))
            else:
                evo_items.append(str(t))
        tech_evo_text = f"Technology evolution over time: {', '.join(evo_items)}. "

    topics_text = ""
    if all_topics:
        topics_text = f"Known domains and topics: {all_topics.replace(',', ', ')}. "

    text = f"""{name} (@{username}) primarily works with: {primary_langs.replace(',', ', ')}. \
{topics_text}\
{tech_evo_text}\
Seniority level: {seniority}. \
{'Has notable open source impact. ' if impact else ''}\
Top repositories: {top_repos}""".strip()

    return {
        "id": f"{username}__skills_and_stack",
        "type": "skills_and_stack",
        "text": text,
        "metadata": _base_metadata(p, username, "skills_and_stack"),
    }


def _repo_detail_chunk(repo: dict, p: dict, username: str, index: int) -> dict | None:
    name = repo.get("name", "")
    if not name:
        return None

    desc = repo.get("description", "") or ""
    lang = repo.get("language", "") or ""
    topics = ", ".join(_safe_str_list(repo.get("topics", [])))
    stars = repo.get("stars", 0)
    forks = repo.get("forks", 0)
    commits = repo.get("commit_count", 0)
    is_fork = repo.get("is_fork", False)
    readme = (repo.get("readme_summary", "") or "")[:400]
    lines_added = repo.get("lines_added", 0)

    role = "forked and contributed to" if is_fork else "created and maintains"

    text = f"""{username} {role} {name}\
{f': {desc}' if desc else ''}. \
{f'Built with {lang}. ' if lang else ''}\
{f'Topics: {topics}. ' if topics else ''}\
{stars} stars, {forks} forks, {commits} commits, {lines_added} lines added. \
{f'Summary: {readme}' if readme else ''}""".strip()

    meta = _base_metadata(p, username, "repo_detail")
    meta.update({
        "repo_name": name,
        "repo_stars": stars,
        "repo_language": lang,
        "repo_is_fork": is_fork,
        "repo_topics": topics,
    })

    return {
        "id": f"{username}__repo__{name}",
        "type": "repo_detail",
        "text": text,
        "metadata": meta,
    }


# ── Shared metadata ──────────────────────────────────────────────────────────

def _base_metadata(p: dict, username: str, chunk_type: str) -> dict:
    """
    Chroma-compatible metadata: only str, int, float, bool values.
    Arrays stored as comma-joined strings.
    """
    return {
        "username": username,
        "chunk_type": chunk_type,
        "name": str(p.get("name", "") or ""),
        "seniority_tier": str(p.get("seniority_tier", "junior")),
        "experience_years_approx": int(p.get("experience_years_approx", 0)),
        "years_on_github": int(p.get("years_on_github", 0)),
        "total_commits": int(p.get("total_commits", 0)),
        "total_prs_merged": int(p.get("total_prs_merged", 0)),
        "recent_6m_commits": int(p.get("recent_6m_commits", 0)),
        "longest_streak_months": int(p.get("longest_streak_months", 0)),
        "activity_trend": str(p.get("activity_trend", "stable")),
        "hireable": bool(p.get("hireable") or False),
        "is_sponsored": bool(p.get("is_sponsored", False)),
        "has_open_source_impact": bool(p.get("has_open_source_impact", False)),
        "external_contributions": int(p.get("external_contributions", 0)),
        "primary_languages": str(p.get("primary_languages", "") or ""),
        "all_topics": str(p.get("all_topics", "") or ""),
        "leadership_signals": str(p.get("leadership_signals", "none")),
        "max_repo_stars": int(p.get("max_repo_stars", 0)),
        "owned_repo_count": int(p.get("owned_repo_count", 0)),
        "location": str(p.get("location", "") or ""),
        "company": str(p.get("company", "") or ""),
        "followers": int(p.get("followers", 0)),
    }
