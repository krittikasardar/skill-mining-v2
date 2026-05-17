"""
agents/v2_hierarchical/synthesis_agent.py
Final report synthesis — direct LLM invocation, no template parsing.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agents.v2_hierarchical.prompts import (
    SYNTHESIS_SYSTEM, SYNTHESIS_HUMAN_PROFILE, SYNTHESIS_HUMAN_SEARCH,
)
from config import settings


def _llm():
    return ChatOpenAI(model=settings.llm_model, temperature=0.1, api_key=settings.openai_api_key)


def synthesize_profile_report(analysis: str, original_query: str) -> str:
    result = _llm().invoke([
        SystemMessage(content=SYNTHESIS_SYSTEM),
        HumanMessage(content=SYNTHESIS_HUMAN_PROFILE.format(analysis=analysis, original_query=original_query)),
    ])
    return result.content


def synthesize_search_report(ranking: str, original_query: str) -> str:
    result = _llm().invoke([
        SystemMessage(content=SYNTHESIS_SYSTEM),
        HumanMessage(content=SYNTHESIS_HUMAN_SEARCH.format(ranking=ranking, original_query=original_query)),
    ])
    return result.content