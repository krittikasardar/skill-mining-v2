"""
api/routes/eval_logs.py
Endpoints for viewing and downloading DeepEval response logs.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from response_logger import load_responses, list_log_files, clear_logs
from config import settings

router = APIRouter()


@router.get("/eval/logs")
def get_eval_logs():
    """List available eval log files and record counts."""
    files = list_log_files()
    result = {}
    for f in files:
        agent = Path(f).stem.replace("_responses", "")
        records = load_responses(agent)
        result[agent] = {"file": f, "record_count": len(records)}
    return {
        "save_responses_enabled": settings.save_responses,
        "eval_log_dir": settings.eval_log_dir,
        "logs": result,
    }


@router.get("/eval/download/{agent_version}")
def download_eval_log(agent_version: str):
    """Download the JSONL eval log for a specific agent version."""
    log_dir = Path(settings.eval_log_dir)
    path = log_dir / f"{agent_version}_responses.jsonl"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No log found for {agent_version}")
    return FileResponse(
        path=str(path),
        media_type="application/x-ndjson",
        filename=f"{agent_version}_responses.jsonl",
    )


@router.get("/eval/preview/{agent_version}")
def preview_eval_log(agent_version: str, limit: int = 5):
    """Preview the last N records from an eval log."""
    records = load_responses(agent_version)
    if not records:
        raise HTTPException(status_code=404, detail=f"No records for {agent_version}")
    return {"total": len(records), "preview": records[-limit:]}


@router.delete("/eval/logs")
def clear_eval_logs(agent_version: str | None = None):
    """Clear eval logs. Pass agent_version to clear one, or clear all."""
    clear_logs(agent_version)
    return {"status": "cleared", "agent_version": agent_version or "all"}
