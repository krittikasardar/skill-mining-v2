"""
ingestion/parser.py
Extract only signal-bearing fields from a processed GitHub profile JSON.
Supports large files via ijson streaming.
Handles both flat schema and nested repository_metadata schema.
"""
import ijson
import json
from pathlib import Path


def _safe_get(d: dict, *keys, default=None):
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)
        if d is None:
            return default
    return d


def parse_profile_file(filepath: str | Path) -> dict:
    filepath = Path(filepath)
    file_size_mb = filepath.stat().st_size / (1024 * 1024)
    if file_size_mb > 5:
        return _stream_parse(filepath)
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return _extract_fields(raw)


def _stream_parse(filepath: Path) -> dict:
    raw = {}
    with open(filepath, "rb") as f:
        parser = ijson.kvitems(f, "")
        for key, value in parser:
            if key in ("profile", "aggregate_signals", "repositories",
                       "historical_analysis", "schema_version", "username"):
                raw[key] = value
    return _extract_fields(raw)


def _extract_fields(raw: dict) -> dict:
    profile = raw.get("profile", {})
    agg = raw.get("aggregate_signals", {})
    repos_raw = raw.get("repositories", [])

    extracted = {
        "username": profile.get("login") or raw.get("username", "unknown"),
        "name": profile.get("name", ""),
        "bio": profile.get("bio", "") or "",
        "company": profile.get("company", ""),
        "location": profile.get("location", ""),
        "blog": profile.get("blog", ""),
        "followers": profile.get("followers", 0),
        "following": profile.get("following", 0),
        "followers_to_following_ratio": profile.get("followers_to_following_ratio", 0.0),
        "years_on_github": profile.get("years_on_github", 0),
        "hireable": profile.get("hireable"),
        "is_sponsored": profile.get("is_sponsored", False),
        "sponsoring_count": profile.get("sponsoring_count", 0),
        "profile_readme": profile.get("profile_readme_content", "") or "",
        "pinned_repositories": profile.get("pinned_repositories", []),
        "organisations": profile.get("organisations", []),
    }

    extracted.update({
        "total_commits": agg.get("total_commits_all_repos", 0),
        "total_lines_added": agg.get("total_lines_added_all_repos", 0),
        "total_lines_deleted": agg.get("total_lines_deleted_all_repos", 0),
        "total_prs_opened": agg.get("total_prs_opened", 0),
        "total_prs_merged": agg.get("total_prs_merged", 0),
        "total_issues_opened": agg.get("total_issues_opened", 0),
        "total_issues_closed": agg.get("total_issues_closed", 0),
        "external_contributions": agg.get("external_contributions_count", 0),
        "longest_streak_months": agg.get("longest_contribution_streak_months", 0),
        "most_active_year": agg.get("most_active_year"),
        "activity_trend": agg.get("activity_trend", "stable"),
        "recent_6m_commits": agg.get("recent_6_month_commit_count", 0),
        "tech_evolution": agg.get("tech_evolution", []),
        "peak_activity_year": agg.get("peak_activity_year"),
    })

    repos = []
    for r in repos_raw:
        if not isinstance(r, dict):
            continue

        if "repository_metadata" in r:
            # Nested schema
            meta = r.get("repository_metadata", {})
            skill = r.get("skill_evidence", {})
            role = r.get("role_evidence", {})
            leadership = r.get("leadership_evidence", {})

            commit_count = skill.get("commit_count_sampled", 0) or 0
            lang_breakdown = skill.get("language_breakdown", {})
            total_bytes = sum(
                v.get("bytes", 0) if isinstance(v, dict) else 0
                for v in lang_breakdown.values()
            )
            leadership_signals = leadership.get("signals", [])
            leadership_text = "; ".join(
                s if isinstance(s, str) else str(s) for s in leadership_signals
            )
            repos.append({
                "name": meta.get("name", ""),
                "description": meta.get("description", "") or "",
                "language": meta.get("language", "") or "",
                "topics": meta.get("topics", []) or skill.get("topics", []),
                "stars": meta.get("stargazers_count", 0) or role.get("stars_received", 0),
                "forks": meta.get("forks_count", 0) or role.get("forks_received", 0),
                "is_fork": meta.get("fork", False) or role.get("is_fork", False),
                "created_at": meta.get("created_at", ""),
                "updated_at": meta.get("updated_at", ""),
                "commit_count": commit_count,
                "lines_added": total_bytes,
                "lines_deleted": 0,
                "readme_summary": leadership_text,
            })
        else:
            # Flat schema
            repos.append({
                "name": r.get("name", ""),
                "description": r.get("description", "") or "",
                "language": r.get("language", "") or "",
                "topics": r.get("topics", []),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "is_fork": r.get("is_fork", False),
                "created_at": r.get("created_at", ""),
                "updated_at": r.get("updated_at", ""),
                "commit_count": r.get("commit_count", 0),
                "lines_added": r.get("lines_added", 0),
                "lines_deleted": r.get("lines_deleted", 0),
                "readme_summary": r.get("readme_summary", "") or "",
            })

    extracted["repositories"] = repos
    return extracted
