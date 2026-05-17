"""
api/routes/profile.py
GET /profile/{username} — deep dive on a specific developer.
Supports both V1 and V2 via query param.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Literal

from api.schemas import AgentResponse

router = APIRouter()


@router.get("/profile/{username}", response_model=AgentResponse)
def get_profile_analysis(
    username: str,
    agent_version: Literal["v1", "v2"] = Query("v1"),
):
    try:
        if agent_version == "v2":
            from agents.v2_hierarchical.orchestrator import run_query
            result = run_query(f"Analyze the GitHub profile of @{username}")
        else:
            from agents.v1_single.agent import run_query
            result = run_query(f"Analyze the GitHub profile of @{username}")

        return AgentResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
