# Skill Mining – GitHub Profile Evidence Pipeline

A Python pipeline for collecting public GitHub profile and repository evidence, enriching it with activity/collaboration signals, and converting it into cleaned, chunked JSON for downstream retrieval, analysis, or reporting.

The current pipeline focuses on **evidence collection and preprocessing**:

1. collect profile-level GitHub data,
2. collect repository-level evidence,
3. build an evidence-preserving raw JSON document,
4. add historical/month-level activity analysis,
5. clean and chunk the evidence for retrieval,
6. write raw and processed v2 output files.

---

## Project structure

```text
skill_mining/
├── main.py                           # Main entry point for collection + preprocessing
├── config.py                         # Environment variables, paths, feature flags, scoring weights
├── github_client.py                  # GitHub client, retry, and rate-limit helpers
├── requirements.txt                  # Python dependencies
├── .env.example                      # Example environment configuration
├── .gitignore
├── usernames.txt                     # Optional list of GitHub usernames
│
├── collectors/
│   ├── profile_collector.py          # Profile metadata, README, pinned repos, orgs, sponsorship signals
│   └── repo_collector.py             # Repos, languages, commits, PRs/issues, releases, tooling, scoring
│
├── transformers_local/
│   └── schema_builder.py             # Builds the raw evidence-preserving JSON schema
│
├── preprocessor/
│   ├── cleaner.py                    # Cleans evidence text while preserving metadata
│   ├── chunker.py                    # Splits evidence into RAG-friendly chunks
│   ├── historical.py                 # Builds temporal activity and tech-evolution signals
│   └── pipeline.py                   # Orchestrates cleaning, chunking, and processed output
│
├── utils/
│   └── helpers.py                    # Shared helper functions
│
├── data/
│   ├── raw/                          # <username>_raw_v2.json
│   ├── processed/                    # <username>_processed_v2.json
│
└── logs/                             # Runtime logs
```

> The current code imports `schema_builder.py` flexibly from `transformers_local/`, `transformers/`, or the project root. Keep the folder name consistent with the version used in your repository.

---

## What the pipeline collects

### Profile-level evidence

The profile collector gathers public GitHub user information such as:

- login, name, bio, company, location, email, blog, avatar URL, and profile URL
- followers, following, public repositories, and public gists
- account creation/update dates
- hireable status
- years on GitHub
- followers-to-following ratio
- profile README from the special `<username>/<username>` repository
- pinned repositories through GitHub GraphQL
- public organisation memberships
- GitHub Sponsors-related signals, when available

### Repository-level evidence

For each public repository, the repository collector gathers:

- repository metadata such as name, description, URL, language, stars, forks, size, license, dates, topics, and default branch
- language breakdown
- README excerpt
- commit samples and commit-depth statistics
- yearly and monthly commit counts
- total lines added/deleted from sampled commits
- commit message quality proxy score
- ownership/fork information
- PR and issue statistics
- contributor count
- release count and latest release information
- CI/CD, tests, contributing guide, code of conduct, and dependency indicators
- detected frameworks, DevOps tools, testing tools, CI platforms, cloud platforms, databases, and API patterns
- documentation quality score
- relevance score for ranking repositories

---

## Setup

### 1. Clone the repository and enter the project folder

```bash
git clone <your-repo-url>
cd skill_mining
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Main dependencies include:

- `PyGithub`
- `python-dotenv`
- `requests`
- `typer`
- `rich`
- `tenacity`
- `diskcache`
- `pandas`

### 4. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and set your GitHub token:

```env
GITHUB_TOKEN=your_github_token_here
COMMITS_PER_REPO=20
MAX_REPOS_PER_USER=100
```

A GitHub token is strongly recommended. The pipeline can make some unauthenticated calls, but rate limits will be much lower and GraphQL-only fields such as pinned repositories may be skipped.

Never commit your `.env` file.

---

## Configuration reference

Important configuration values are read in `config.py`.

| Variable | Default | Purpose |
|---|---:|---|
| `GITHUB_TOKEN` | empty | GitHub API token. Recommended for higher rate limits and GraphQL features |
| `OUTPUT_DIR` | `./data` | Base output directory |
| `MAX_REPOS_PER_USER` | `200` | Maximum public repositories collected per user |
| `COMMITS_PER_REPO` | `30` | Number of representative commit samples stored per repository |
| `MAX_COMMITS_TO_SCAN_PER_REPO` | `500` | Maximum commits scanned per repository for statistics |
| `README_MAX_CHARS` | `4000` | Maximum README characters stored as evidence |
| `PROFILE_README_MAX_CHARS` | `5000` | Maximum profile README characters stored |
| `ENABLE_COLLABORATION_COLLECTION` | `true` | Enables PR/issue-related collection flags |
| `ENABLE_RELEASE_COLLECTION` | `true` | Enables release metadata collection flags |
| `ENABLE_ENGINEERING_MATURITY_COLLECTION` | `true` | Enables CI/test/docs/dependency collection flags |
| `ENABLE_TOOLING_DETECTION` | `true` | Enables framework/tool/cloud/database/API detection flags |
| `ENABLE_PROFILE_README` | `true` | Enables profile README collection flags |
| `ENABLE_PINNED_REPOSITORIES` | `true` | Enables pinned repository collection flags |
| `ENABLE_ORGANISATION_COLLECTION` | `true` | Enables public organisation collection flags |
| `ENABLE_SPONSORSHIP_COLLECTION` | `true` | Enables sponsorship signal collection flags |
| `ENABLE_HISTORICAL_MONTHLY_ANALYSIS` | `true` | Enables monthly historical activity fields |
| `INACTIVE_GAP_THRESHOLD_MONTHS` | `3` | Minimum inactive gap length to report |
| `RECENT_ACTIVITY_MONTHS` | `6` | Recent activity window |
| `ENABLE_CACHE` | `false` | Enables disk cache |
| `CACHE_TTL_SECONDS` | `86400` | Cache lifetime in seconds |
| `SCORE_THRESHOLD` | `0.0` | Minimum repository relevance score |
| `LOG_LEVEL` | `INFO` | Logging level |

Repository relevance scoring uses these default weights:

| Signal | Weight |
|---|---:|
| Stars | `0.25` |
| Forks | `0.20` |
| Repository size | `0.10` |
| Ownership | `0.20` |
| Recency | `0.15` |
| Age bonus | `0.10` |

---

## Usage

### Option 1: Collect profiles listed in `usernames.txt`

Add one GitHub username per line:

```text
torvalds
octocat
karpathy
```

Then run:

```bash
python main.py
```

### Option 2: Collect specific profiles from the command line

```bash
python main.py torvalds octocat
```

You can pass multiple usernames in one run:

```bash
python main.py tiangolo nayafia hnarayanan
```

For each username, the pipeline automatically:

1. collects the profile,
2. collects repositories,
3. builds the raw v2 schema,
4. adds historical analysis,
5. writes the raw JSON file,
6. runs the preprocessing pipeline,
7. writes the processed JSON file.

---

## Output files

For each username, the main pipeline writes:

| File | Description |
|---|---|
| `data/raw/<username>_raw_v2.json` | Full evidence-preserving raw document |
| `data/processed/<username>_processed_v2.json` | Cleaned and chunked processed document for retrieval/LLM use |

The file-based preprocessing API can also write:

| File | Description |
|---|---|
| `data/preprocessed/<username>_preprocessed.json` | Optional output when preprocessing an existing raw JSON file directly |

---

## Raw v2 JSON structure

The raw output contains the complete collected evidence before cleaning/chunking.

```json
{
  "schema_version": "2.0",
  "profile": {},
  "repositories": [],
  "aggregate_signals": {},
  "historical_analysis": {},
  "evidence_index": [],
  "collection_metadata": {}
}
```

### Main raw sections

| Section | Description |
|---|---|
| `profile` | GitHub profile metadata, profile README, pinned repos, organisations, sponsorship signals |
| `repositories` | Per-repository metadata, skill evidence, role evidence, leadership evidence, and text evidence |
| `aggregate_signals` | Cross-repository signals such as languages, stars, forks, commits, PRs, issues, and activity patterns |
| `historical_analysis` | Commit trends, language evolution, monthly heatmap, inactive periods, and repo creation cadence |
| `evidence_index` | Flat list of citable evidence snippets used for downstream chunking |
| `collection_metadata` | Runtime metadata such as username, elapsed time, repo count, and output file names |

---

## Repository record structure

Each repository in `repositories` follows this high-level structure:

```json
{
  "repository_metadata": {},
  "relevance_score": 0.0,
  "skill_evidence": {},
  "role_evidence": {},
  "leadership_evidence": {},
  "raw_text_evidence": {}
}
```

### `repository_metadata`

Contains core repository information and engineering maturity signals:

```json
{
  "name": "...",
  "full_name": "...",
  "description": "...",
  "html_url": "...",
  "language": "Python",
  "stargazers_count": 0,
  "forks_count": 0,
  "size": 0,
  "default_branch": "main",
  "fork": false,
  "archived": false,
  "created_at": "...",
  "updated_at": "...",
  "pushed_at": "...",
  "license": "...",
  "topics": [],
  "has_ci_cd": false,
  "has_tests": false,
  "has_contributing_guide": false,
  "has_code_of_conduct": false,
  "dependency_count": 0,
  "releases_count": 0,
  "latest_release_tag": null,
  "latest_release_date": null,
  "contributor_count": 0
}
```

### `skill_evidence`

Contains technical and activity-related evidence:

```json
{
  "primary_language": "Python",
  "languages_used": [],
  "language_breakdown": {},
  "readme_keywords": [],
  "commit_count_sampled": 0,
  "total_commit_count": 0,
  "commit_frequency_per_year": {},
  "avg_commits_per_active_month": 0.0,
  "last_commit_date": null,
  "total_lines_added": 0,
  "total_lines_deleted": 0,
  "commit_message_quality_score": 0.0,
  "contribution_gap_months": 0,
  "frameworks_detected": [],
  "devops_tools_detected": [],
  "testing_frameworks_detected": [],
  "ci_platforms_detected": [],
  "cloud_platforms_detected": [],
  "db_technologies_detected": [],
  "api_patterns_detected": [],
  "documentation_quality_score": 0
}
```

### `role_evidence`

Contains ownership, collaboration, and maintainer-related evidence:

```json
{
  "is_owner": true,
  "is_fork": false,
  "forked_from": null,
  "stars_received": 0,
  "forks_received": 0,
  "issues_opened_count": 0,
  "closed_issues_count": 0,
  "pr_open_count": 0,
  "pr_closed_count": 0,
  "pr_merged_count": 0,
  "pr_merge_rate_pct": null,
  "avg_issue_close_time_days": null,
  "contributor_count": 0
}
```

### `leadership_evidence`

Contains leadership-style repository signals:

```json
{
  "signals": [],
  "commit_year_span": {}
}
```

### `raw_text_evidence`

Contains README and commit text evidence:

```json
{
  "readme_excerpt": "...",
  "commit_samples": [],
  "description": "..."
}
```

---

## Historical analysis

The historical module produces temporal and technology-evolution signals.

```json
{
  "commits_by_year": {},
  "languages_by_year": {},
  "activity_trend": "stable",
  "peak_activity_year": null,
  "tech_evolution": [],
  "monthly_commit_heatmap": {},
  "weekday_vs_weekend_ratio": {},
  "most_active_month_of_year": null,
  "inactive_periods": [],
  "recent_6_month_commit_count": 0,
  "repo_creation_cadence": {}
}
```

### Historical fields

| Field | Meaning |
|---|---|
| `commits_by_year` | Commit counts per year |
| `languages_by_year` | Dominant languages by year |
| `activity_trend` | `growing`, `stable`, or `declining` |
| `peak_activity_year` | Year with the highest commit count |
| `tech_evolution` | Language shifts from early to recent periods |
| `monthly_commit_heatmap` | Commit counts by `YYYY-MM` |
| `weekday_vs_weekend_ratio` | Weekday/weekend commit distribution from sampled commits |
| `most_active_month_of_year` | Calendar month with highest total activity |
| `inactive_periods` | Gaps between active commit months |
| `recent_6_month_commit_count` | Recent activity count |
| `repo_creation_cadence` | Repository creation counts and average repos/year |

---

## Processed v2 JSON structure

The processed output is created by `preprocessor/pipeline.py`.

```json
{
  "schema_version": "2.0",
  "username": "...",
  "preprocessed_at": "...",
  "source_schema_version": "2.0",
  "profile": {},
  "aggregate_signals": {},
  "historical_analysis": {},
  "repositories": [],
  "evidence_index": [],
  "chunks": [],
  "stats": {},
  "collection_metadata": {},
  "preprocessing_metadata": {}
}
```

The processed file preserves high-value context from the raw file while adding cleaned and chunked evidence for retrieval.

---

## Evidence cleaning

The cleaner:

- removes Unicode replacement corruption,
- strips simple HTML tags,
- removes badge/shield noise lines,
- collapses excessive whitespace,
- preserves metadata,
- keeps short but useful structured evidence such as commit and contribution signals,
- drops only genuinely empty or very low-signal items.

Supported evidence types include:

```text
profile
skill
role
leadership
commit
contribution
```

---

## Evidence chunking

The chunker splits cleaned evidence into RAG-friendly chunks while preserving traceability.

Each chunk contains:

```json
{
  "chunk_id": "ev_0001_c00",
  "evidence_id": "ev_0001",
  "chunk_index": 0,
  "total_chunks": 1,
  "type": "skill",
  "source": "repo:owner/name",
  "content": "...",
  "metadata": {}
}
```

Default chunk settings:

| Evidence type | Max characters |
|---|---:|
| `profile` | `1800` |
| `skill` | `1500` |
| `role` | `1200` |
| `leadership` | `1200` |
| `commit` | `900` |
| `contribution` | `1000` |

---

## Loading chunks for retrieval

Example:

```python
import json

with open("data/processed/karpathy_processed_v2.json", encoding="utf-8") as f:
    doc = json.load(f)

texts = [chunk["content"] for chunk in doc["chunks"]]
ids = [chunk["chunk_id"] for chunk in doc["chunks"]]
metadatas = [chunk["metadata"] for chunk in doc["chunks"]]
```

These `texts`, `ids`, and `metadatas` can be passed to an embedding model or vector database.

---

## Programmatic preprocessing

The main pipeline already runs preprocessing automatically.

If you want to preprocess an existing raw JSON file manually from Python:

```python
from pathlib import Path
from preprocessor.pipeline import preprocess

preprocess(Path("data/raw/karpathy_raw_v2.json"))
```

To preprocess all raw JSON files programmatically:

```python
from preprocessor.pipeline import preprocess_all

preprocess_all()
```

---

## Recommended run checklist

Before running the pipeline, compile-check the main modules:

```bash
python -m py_compile config.py github_client.py main.py collectors/profile_collector.py collectors/repo_collector.py preprocessor/*.py utils/helpers.py
```

Then run:

```bash
python main.py <github_username>
```

Check that these files were created:

```text
data/raw/<username>_raw_v2.json
data/processed/<username>_processed_v2.json
```

---

## Notes and current limitations

- The pipeline only collects public GitHub data.
- A GitHub token is strongly recommended because some fields depend on authenticated requests or GraphQL.
- Commit statistics are bounded by configured scan/sample limits, so they should be treated as evidence signals rather than a perfect complete history.
- Tooling detection and documentation quality scores are heuristic signals based on README text and repository file paths.
- Relevance scoring is transparent and configurable, but it is still a heuristic ranking method.

---

## Security notes

- Do not commit `.env`.
- Do not expose your GitHub token.
- Keep raw collected data out of public repositories if it contains information you do not want to redistribute.
- This project should be used only with public GitHub data and in compliance with GitHub's API terms.
