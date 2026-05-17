"""
api/routes/search.py
POST /search — find top 3 matching profiles for a role/requirement.
POST /query  — general free-form query (auto-detects mode).
"""
from fastapi import APIRouter, HTTPException
from api.schemas import SearchRequest, QueryRequest, AgentResponse

router = APIRouter()


@router.post("/search", response_model=AgentResponse)
def search_candidates(req: SearchRequest):
    """
    Structured candidate search with optional filters.
    """
    # Enrich query with explicit constraints
    enriched = req.query
    constraints = []
    if req.min_experience_years > 0:
        constraints.append(f"at least {req.min_experience_years} years of experience")
    if req.required_language:
        constraints.append(f"expertise in {req.required_language}")
    if req.seniority_tier:
        constraints.append(f"{req.seniority_tier} level seniority")
    if req.has_leadership:
        constraints.append("leadership/maintainer background")
    if constraints:
        enriched = f"{req.query}. Requirements: {', '.join(constraints)}."

    try:
        if req.agent_version == "v2":
            from agents.v2_hierarchical.orchestrator import run_query
            result = run_query(enriched)
        else:
            from agents.v1_single.agent import run_query
            result = run_query(enriched)

        return AgentResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=AgentResponse)
def free_query(req: QueryRequest):
    """
    Free-form query — agent auto-detects whether it's a profile dive or candidate search.
    """
    try:
        if req.agent_version == "v2":
            from agents.v2_hierarchical.orchestrator import run_query
            result = run_query(req.query)
        else:
            from agents.v1_single.agent import run_query
            result = run_query(req.query, chat_history=req.chat_history)

        return AgentResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
