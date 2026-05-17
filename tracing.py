"""
tracing.py
LangSmith tracing setup. Call setup_tracing() once at app startup.
Reads LANGSMITH_TRACING from .env — if false, does nothing.
"""
import os
from config import settings


def setup_tracing():
    """
    Enable LangSmith tracing if LANGSMITH_TRACING=true in .env.
    LangChain automatically picks up LANGCHAIN_* env vars.
    """
    if not settings.langsmith_tracing:
        return

    if not settings.langsmith_api_key:
        print("⚠️  LANGSMITH_TRACING=true but LANGSMITH_API_KEY is not set. Tracing disabled.")
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint

    print(f"✓ LangSmith tracing enabled → project: {settings.langsmith_project}")


def tracing_enabled() -> bool:
    return settings.langsmith_tracing and bool(settings.langsmith_api_key)
