"""
api/main.py — FastAPI app with LangSmith tracing + eval log endpoints.

Run:
    uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tracing import setup_tracing
from api.routes import health, profile, search, eval_logs
from config import settings

# Enable LangSmith tracing if configured
setup_tracing()

app = FastAPI(
    title="GitHub Profile Intelligence API",
    description="AI-powered GitHub profile analysis and candidate search",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(profile.router, tags=["Profile"])
app.include_router(search.router, tags=["Search"])
app.include_router(eval_logs.router, tags=["Evaluation"])


@app.get("/")
def root():
    return {
        "service": "GitHub Profile Intelligence v2",
        "docs": "/docs",
        "tracing": settings.langsmith_tracing,
        "save_responses": settings.save_responses,
        "endpoints": {
            "profile_dive": "GET /profile/{username}?agent_version=v1|v2",
            "candidate_search": "POST /search",
            "free_query": "POST /query",
            "stats": "GET /stats",
            "eval_logs": "GET /eval/logs",
            "eval_download": "GET /eval/download/{agent_version}",
            "eval_clear": "DELETE /eval/logs",
        }
    }
