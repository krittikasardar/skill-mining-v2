"""
agents/v2_hierarchical/orchestrator.py
V2 hierarchical pipeline. Uses SystemMessage directly to avoid
ChatPromptTemplate parsing issues with JSON in prompt text.
"""
import json
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.v2_hierarchical.prompts import (
    ORCHESTRATOR_SYSTEM, ORCHESTRATOR_HUMAN,
    ANALYSIS_SYSTEM, ANALYSIS_HUMAN,
    RANKING_SYSTEM, RANKING_HUMAN,
    SYNTHESIS_SYSTEM, SYNTHESIS_HUMAN_PROFILE, SYNTHESIS_HUMAN_SEARCH,
)
from agents.v2_hierarchical.retrieval_agent import retrieve_profile, retrieve_candidates
from config import settings
from response_logger import save_response


def _llm():
    return ChatOpenAI(model=settings.llm_model, temperature=0, api_key=settings.openai_api_key)


def _invoke(system: str, human: str) -> str:
    """Call LLM directly with system + human messages. No template parsing."""
    result = _llm().invoke([
        SystemMessage(content=system),
        HumanMessage(content=human),
    ])
    return result.content


def _orchestrate(query: str) -> dict:
    human = ORCHESTRATOR_HUMAN.format(query=query)
    content = _invoke(ORCHESTRATOR_SYSTEM, human).strip()

    # Strip markdown fences if present
    if "```" in content:
        parts = content.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                content = part
                break

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "mode": "search",
            "username": None,
            "retrieval_query": query,
            "filters": {
                "min_experience_years": 0,
                "seniority_tier": "",
                "required_language": "",
                "has_leadership": False,
            },
            "analysis_focus": "general analysis",
            "original_query": query,
        }


def run_query(query: str) -> dict:
    start = time.time()
    pipeline_trace = []

    # Step 1: Orchestrate
    t0 = time.time()
    routing = _orchestrate(query)
    pipeline_trace.append({
        "step": "orchestrator",
        "latency": round(time.time() - t0, 2),
        "decision": routing,
    })

    mode = routing.get("mode", "search")
    filters = routing.get("filters", {})
    original_query = routing.get("original_query", query)

    # Step 2: Retrieve
    t0 = time.time()
    if mode == "profile":
        username = routing.get("username")
        if not username:
            mode = "search"
            retrieved = retrieve_candidates(
                query=routing.get("retrieval_query", query),
                min_experience_years=filters.get("min_experience_years", 0),
                seniority_tier=filters.get("seniority_tier", ""),
                required_language=filters.get("required_language", ""),
                has_leadership=filters.get("has_leadership", False),
            )
        else:
            retrieved = retrieve_profile(username)
    else:
        retrieved = retrieve_candidates(
            query=routing.get("retrieval_query", query),
            min_experience_years=filters.get("min_experience_years", 0),
            seniority_tier=filters.get("seniority_tier", ""),
            required_language=filters.get("required_language", ""),
            has_leadership=filters.get("has_leadership", False),
        )
    pipeline_trace.append({
        "step": "retrieval_agent",
        "latency": round(time.time() - t0, 2),
        "retrieved_length": len(retrieved),
    })

    # Step 3: Analyse or Rank
    t0 = time.time()
    if mode == "profile":
        analysis = _invoke(
            ANALYSIS_SYSTEM,
            ANALYSIS_HUMAN.format(
                profile_data=retrieved,
                focus=routing.get("analysis_focus", "full profile analysis"),
            ),
        )
        pipeline_trace.append({"step": "analysis_agent", "latency": round(time.time() - t0, 2)})
    else:
        analysis = _invoke(
            RANKING_SYSTEM,
            RANKING_HUMAN.format(requirement=original_query, candidates=retrieved),
        )
        pipeline_trace.append({"step": "ranking_agent", "latency": round(time.time() - t0, 2)})

    # Step 4: Synthesise
    t0 = time.time()
    if mode == "profile":
        final_output = _invoke(
            SYNTHESIS_SYSTEM,
            SYNTHESIS_HUMAN_PROFILE.format(analysis=analysis, original_query=original_query),
        )
    else:
        final_output = _invoke(
            SYNTHESIS_SYSTEM,
            SYNTHESIS_HUMAN_SEARCH.format(ranking=analysis, original_query=original_query),
        )
    pipeline_trace.append({"step": "synthesis_agent", "latency": round(time.time() - t0, 2)})

    total_latency = round(time.time() - start, 2)

    # Save for DeepEval — always attempt, logger checks the flag internally
    save_response(
        query=query,
        response=final_output,
        agent_version="v2_hierarchical",
        mode=mode,
        metadata={
            "latency_seconds": total_latency,
            "username": routing.get("username"),
            "pipeline_steps": len(pipeline_trace),
        },
    )

    return {
        "mode": mode,
        "username": routing.get("username"),
        "output": final_output,
        "pipeline_trace": pipeline_trace,
        "latency_seconds": total_latency,
        "agent_version": "v2_hierarchical",
    }