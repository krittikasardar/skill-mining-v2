"""
response_logger.py
Save agent responses to JSONL files for DeepEval evaluation.
Enabled when SAVE_RESPONSES=true in .env.

DeepEval-compatible format:
  Each line is a JSON object with: input, actual_output, context, metadata
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from config import settings


def _get_log_path(agent_version: str) -> Path:
    log_dir = Path(settings.eval_log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{agent_version}_responses.jsonl"


def save_response(
    query: str,
    response: str,
    agent_version: str,
    mode: str,
    context: list[str] | None = None,
    metadata: dict | None = None,
):
    """
    Save a single query/response pair to the eval log.

    Args:
        query:         The user's input query
        response:      The agent's final output
        agent_version: 'v1_single' or 'v2_hierarchical'
        mode:          'profile' or 'search'
        context:       Retrieved context chunks (for RAG evaluation)
        metadata:      Any extra fields (latency, username, etc.)
    """
    if not settings.save_responses:
        return

    record = {
        "input": query,
        "actual_output": response,
        "context": context or [],
        "metadata": {
            "agent_version": agent_version,
            "mode": mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        },
    }

    log_path = _get_log_path(agent_version)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_responses(agent_version: str) -> list[dict]:
    """Load all saved responses for a given agent version."""
    log_path = _get_log_path(agent_version)
    if not log_path.exists():
        return []
    with open(log_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def list_log_files() -> list[str]:
    """List all eval log files."""
    log_dir = Path(settings.eval_log_dir)
    if not log_dir.exists():
        return []
    return [str(p) for p in log_dir.glob("*.jsonl")]


def clear_logs(agent_version: str | None = None):
    """Clear log files. If agent_version is None, clears all."""
    log_dir = Path(settings.eval_log_dir)
    if not log_dir.exists():
        return
    if agent_version:
        path = _get_log_path(agent_version)
        if path.exists():
            path.unlink()
    else:
        for f in log_dir.glob("*.jsonl"):
            f.unlink()
