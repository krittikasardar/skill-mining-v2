"""
ingestion/enricher.py
Compute derived/enriched metadata fields used for Chroma pre-filtering.
All fields are scalar or comma-joined strings (Chroma compatible).
"""
from typing import Any


def enrich(profile: dict) -> dict:
    """
    Add derived fields to the parsed profile dict.
    Returns the same dict with additional keys prefixed with no namespace.
    """
    profile = profile.copy()

    profile["experience_years_approx"] = _experience_years(profile)
    profile["seniority_tier"] = _seniority_tier(profile)
    profile["leadership_signals"] = _leadership_signals(profile)
    profile["has_open_source_impact"] = _open_source_impact(profile)
    profile["primary_languages"] = _primary_languages(profile)
    profile["all_topics"] = _all_topics(profile)
    profile["max_repo_stars"] = _max_stars(profile)
    profile["owned_repo_count"] = _owned_repo_count(profile)
    profile["top_repos_summary"] = _top_repos_summary(profile)

    return profile


# ── Derived field helpers ──────────────────────────────────────────────────

def _experience_years(p: dict) -> int:
    base = p.get("years_on_github", 0)
    total_commits = p.get("total_commits", 0)
    # Penalise ghost accounts with no activity
    if total_commits == 0 and p.get("recent_6m_commits", 0) == 0:
        return max(1, int(base * 0.4))
    return base


def _seniority_tier(p: dict) -> str:
    max_stars = _max_stars(p)
    ext = p.get("external_contributions", 0)
    commits = p.get("total_commits", 0)
    streak = p.get("longest_streak_months", 0)
    prs_merged = p.get("total_prs_merged", 0)

    if max_stars > 1000 or ext > 20 or prs_merged > 100:
        return "staff"
    elif commits > 2000 or streak > 18 or max_stars > 200:
        return "senior"
    elif commits > 500 or streak > 6:
        return "mid"
    else:
        return "junior"


def _leadership_signals(p: dict) -> str:
    signals = []
    orgs = p.get("organisations", [])
    pinned = p.get("pinned_repositories", [])
    readme = p.get("profile_readme", "")
    max_stars = _max_stars(p)
    prs_merged = p.get("total_prs_merged", 0)
    ext = p.get("external_contributions", 0)

    if orgs:
        signals.append("org_member")
    if pinned and max_stars > 100:
        signals.append("maintainer")
    if readme and len(readme) > 100:
        signals.append("thought_leader")
    if prs_merged > 50:
        signals.append("active_merger")
    if ext > 10:
        signals.append("external_contributor")
    if max_stars > 500:
        signals.append("open_source_author")

    return ",".join(signals) if signals else "none"


def _open_source_impact(p: dict) -> bool:
    return _max_stars(p) > 500 or p.get("external_contributions", 0) > 10


def _primary_languages(p: dict) -> str:
    """
    Top 3 languages by lines written across repos.
    Falls back to language field if lines data missing.
    """
    lang_lines: dict[str, int] = {}
    for repo in p.get("repositories", []):
        lang = repo.get("language", "")
        if not lang:
            continue
        lines = repo.get("lines_added", 0) + repo.get("lines_deleted", 0)
        lang_lines[lang] = lang_lines.get(lang, 0) + max(lines, 1)

    top = sorted(lang_lines.items(), key=lambda x: x[1], reverse=True)[:3]
    return ",".join(l for l, _ in top)


def _all_topics(p: dict) -> str:
    """Deduplicated union of all repo topics."""
    seen = set()
    for repo in p.get("repositories", []):
        for t in repo.get("topics", []):
            if t and isinstance(t, str):
                seen.add(t.lower())
    return ",".join(sorted(seen))


def _max_stars(p: dict) -> int:
    repos = p.get("repositories", [])
    if not repos:
        return 0
    return max((r.get("stars", 0) for r in repos), default=0)


def _owned_repo_count(p: dict) -> int:
    return sum(1 for r in p.get("repositories", []) if not r.get("is_fork", False))


def _top_repos_summary(p: dict) -> str:
    """Short text summary of top 5 repos by stars for embedding."""
    repos = sorted(p.get("repositories", []), key=lambda r: r.get("stars", 0), reverse=True)[:5]
    parts = []
    for r in repos:
        name = r.get("name", "")
        desc = r.get("description", "")
        lang = r.get("language", "")
        stars = r.get("stars", 0)
        topics = ", ".join(r.get("topics", [])[:5])
        parts.append(f"{name} ({lang}, ★{stars}): {desc}. Topics: {topics}")
    return " | ".join(parts)
