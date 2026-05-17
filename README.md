# GitHub Profile Intelligence

AI-powered system for ingesting, indexing, and querying GitHub developer profiles.
Built with LangChain, ChromaDB, FastAPI, and Streamlit.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   INGESTION PIPELINE                     │
│   JSON files → parse → enrich → chunk → embed → Chroma  │
│   (standalone, manual trigger, uv managed)               │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│                 CHROMA (local persistent)                │
│   3 chunk types: profile_summary | skills_and_stack |    │
│   repo_detail  — rich metadata for pre-filtering         │
└──────────────────────────────────────────────────────────┘
              ↓                           ↓
  ┌───────────────────┐       ┌────────────────────────┐
  │  V1: Single Agent │       │  V2: Hierarchical       │
  │  One LangChain    │       │  Orchestrator           │
  │  agent + all tools│       │  ├── Retrieval Agent   │
  └───────────────────┘       │  ├── Analysis Agent    │
              ↓               │  ├── Ranking Agent     │
              └───────┬───────│  └── Synthesis Agent   │
                      ↓       └────────────────────────┘
           ┌──────────────────────┐
           │    FastAPI Backend   │
           │  GET /profile/{user} │
           │  POST /search        │
           │  POST /query         │
           └──────────────────────┘
                      ↓
           ┌──────────────────────┐
           │  Streamlit Frontend  │
           │  - Profile Deep Dive │
           │  - Candidate Search  │
           │  - Free Query Chat   │
           └──────────────────────┘
```

---

## Project Structure

```
github-profile-intelligence/
├── pyproject.toml              # uv managed dependencies
├── .env.example                # environment variable template
├── config.py                   # central settings (pydantic-settings)
│
├── ingestion/                  # standalone ingestion pipeline
│   ├── parser.py               # JSON field extraction (ijson stream support)
│   ├── enricher.py             # derived metadata: seniority, leadership, etc.
│   ├── chunker.py              # 3 chunk types with NL passage construction
│   ├── embedder.py             # OpenAI / Nomic embedding (batched)
│   ├── indexer.py              # Chroma upsert / query / delete
│   └── run.py                  # CLI entrypoint
│
├── agents/
│   ├── tools.py                # shared LangChain tools (search, get_profile)
│   ├── v1_single/
│   │   ├── agent.py            # single AgentExecutor, both modes
│   │   └── prompts.py
│   └── v2_hierarchical/
│       ├── orchestrator.py     # routing + pipeline coordination
│       ├── retrieval_agent.py  # tool-using retrieval specialist
│       ├── analysis_agent.py   # profile analysis (Mode 1)
│       ├── ranking_agent.py    # candidate scoring (Mode 2)
│       ├── synthesis_agent.py  # final report generation
│       └── prompts.py
│
├── api/
│   ├── main.py                 # FastAPI app + CORS
│   ├── schemas.py              # Pydantic request/response models
│   └── routes/
│       ├── health.py           # GET /health, GET /stats
│       ├── profile.py          # GET /profile/{username}
│       └── search.py           # POST /search, POST /query
│
├── ui/
│   └── app.py                  # Streamlit UI (3 tabs)
│
├── data/                       # place processed JSON files here
└── chroma_store/               # local Chroma persistence (auto-created)
```

---

## Setup

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Install uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install dependencies
```bash
cd github-profile-intelligence
uv sync
```

### Configure environment
```bash
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

`.env` options:
| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | required | OpenAI API key |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Or `nomic-embed-text` |
| `LLM_MODEL` | `gpt-4o` | LLM for agents |
| `CHROMA_PERSIST_DIR` | `./chroma_store` | Local Chroma storage path |
| `CHROMA_COLLECTION` | `github_profiles` | Chroma collection name |
| `DATA_DIR` | `./data` | Folder containing processed JSON files |

---

## Ingestion Pipeline

The ingestion pipeline is **fully standalone** from the agent stack. Run it manually to index profiles.

### Place your JSON files
```bash
mkdir -p data
cp /path/to/jakubroztocil_processed_v2.json data/
```

### Run ingestion
```bash
# Ingest all JSON files in DATA_DIR
uv run ingest

# Ingest a single file
uv run ingest --file data/jakubroztocil_processed_v2.json

# Re-ingest specific username
uv run ingest --username jakubroztocil

# Check collection stats
uv run ingest --stats

# Remove a profile from the index
uv run ingest --delete jakubroztocil
```

### What ingestion does
1. **Parse** — extracts signal-bearing fields from JSON (streaming for large files)
2. **Enrich** — computes derived metadata: `seniority_tier`, `experience_years_approx`, `leadership_signals`, `primary_languages`, etc.
3. **Chunk** — produces 3 chunk types as natural language passages:
   - `profile_summary`: identity + aggregate activity signals
   - `skills_and_stack`: languages, topics, tech evolution
   - `repo_detail`: one chunk per repo (top 20 by stars)
4. **Embed** — batched embedding via OpenAI or Nomic
5. **Index** — upsert into Chroma with rich metadata for pre-filtering

---

## Running the Services

Start both services in separate terminals:

### Terminal 1 — FastAPI
```bash
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

### Terminal 2 — Streamlit
```bash
uv run streamlit run ui/app.py
```

UI available at: http://localhost:8501

---

## API Endpoints

### `GET /profile/{username}`
Deep dive on a specific developer.
```bash
curl "http://localhost:8000/profile/jakubroztocil?agent_version=v1"
curl "http://localhost:8000/profile/jakubroztocil?agent_version=v2"
```

### `POST /search`
Find top 3 matching profiles for a role/requirement.
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Senior Python engineer with open source experience",
    "agent_version": "v1",
    "min_experience_years": 5,
    "required_language": "Python",
    "seniority_tier": "senior",
    "has_leadership": true
  }'
```

### `POST /query`
Free-form query — agent auto-detects mode.
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Who is best suited for a DevOps lead role?", "agent_version": "v2"}'
```

### `GET /stats`
Collection stats.
```bash
curl http://localhost:8000/stats
```

---

## Query Modes

### Mode 1: Profile Deep Dive
Triggered when a specific username is mentioned.

**Example queries:**
- `"Analyze @jakubroztocil"`
- `"Tell me about torvalds"`
- `"What are the technical skills of gaearon?"`

**Output covers:**
- Technical skills (languages, frameworks, tools, domains)
- Project roles (creator / contributor / learner patterns)
- Leadership signals (maintainer, org owner, reviewer, open source author)
- Experience assessment (seniority, trend, consistency)
- Strengths and best-fit roles

### Mode 2: Candidate Search
Triggered for role/requirement queries. Returns top 3 profiles.

**Example queries:**
- `"Who is suitable for a senior backend role with Python and Docker?"`
- `"Find candidates with 7+ years experience in the React ecosystem"`
- `"Which profiles are suitable for a technical lead or engineering manager role?"`

**Output includes:**
- Ranked list of top 3 candidates with match scores
- Per-candidate: evidence for match, skill alignment, gaps
- Final hiring recommendation

---

## Agent Versions

### V1 — Single Agent
One LangChain `AgentExecutor` with all 4 tools. Handles mode detection and both query types.

- **Pros:** Simple, lower latency, fewer LLM calls
- **Cons:** Less specialized reasoning per step; single point of failure

### V2 — Hierarchical Multi-Agent
Coordinated pipeline of 4 specialized agents:

| Agent | Role | LLM Calls |
|---|---|---|
| Orchestrator | Route query, extract filters | 1 |
| Retrieval Agent | Fetch from Chroma via tools | 1–3 |
| Analysis Agent (Mode 1) | Deep profile reasoning | 1 |
| Ranking Agent (Mode 2) | Score + rank candidates | 1 |
| Synthesis Agent | Final report generation | 1 |

- **Pros:** Each agent is specialized; better reasoning quality; traceable pipeline
- **Cons:** Higher latency (4–5 LLM calls); more tokens consumed

**When to use V2:** Complex queries, leadership assessment, multi-criteria candidate ranking.

---

## Chunk Metadata Schema

All chunks are indexed with these filterable metadata fields:

| Field | Type | Description |
|---|---|---|
| `username` | str | GitHub username |
| `chunk_type` | str | `profile_summary` / `skills_and_stack` / `repo_detail` |
| `seniority_tier` | str | `junior` / `mid` / `senior` / `staff` |
| `experience_years_approx` | int | Derived from `years_on_github` + activity |
| `total_commits` | int | Lifetime commit count |
| `total_prs_merged` | int | Merged PR count |
| `recent_6m_commits` | int | Activity recency signal |
| `longest_streak_months` | int | Consistency signal |
| `activity_trend` | str | `stable` / `growing` / `declining` |
| `primary_languages` | str | Comma-joined top 3 languages by lines written |
| `all_topics` | str | Comma-joined union of all repo topics |
| `leadership_signals` | str | Comma-joined: `maintainer`, `org_member`, `thought_leader`, etc. |
| `has_open_source_impact` | bool | Stars > 500 or external contributions > 10 |
| `max_repo_stars` | int | Highest star count across repos |
| `hireable` | bool | From GitHub profile |
| `location` | str | Developer location |
| `followers` | int | GitHub followers |

---

## Extending

### Add a new embedding model
Edit `EMBEDDING_MODEL` in `.env`. Nomic requires the `nomic-embed-text` model string; the embedder auto-applies task-type prefixes.

### Add new metadata filters
1. Add the derivation logic in `ingestion/enricher.py`
2. Add the field to `_base_metadata()` in `ingestion/chunker.py`
3. Expose the filter parameter in `agents/tools.py:search_profiles`
4. Add the UI control in `ui/app.py`

### Scale beyond hundreds of profiles
- Switch to Chroma Cloud or Qdrant for production scale
- Add an async ingestion queue (Celery + Redis) instead of manual trigger
- Use `text-embedding-3-large` for higher-recall search

---

## License

MIT
