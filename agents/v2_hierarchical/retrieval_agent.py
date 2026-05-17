"""
agents/v2_hierarchical/retrieval_agent.py
Retrieval specialist using LangChain 1.x create_agent.
"""
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

from agents.tools import ALL_TOOLS
from agents.v2_hierarchical.prompts import (
    RETRIEVAL_SYSTEM,
    RETRIEVAL_HUMAN_PROFILE,
    RETRIEVAL_HUMAN_SEARCH,
)
from config import settings


def _run_agent(system_prompt: str, human_msg: str) -> str:
    llm = ChatOpenAI(model=settings.llm_model, temperature=0, api_key=settings.openai_api_key)
    agent = create_agent(llm, ALL_TOOLS, system_prompt=system_prompt)
    result = agent.invoke({"messages": [HumanMessage(content=human_msg)]})
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content
    return ""


def retrieve_profile(username: str) -> str:
    return _run_agent(RETRIEVAL_SYSTEM, RETRIEVAL_HUMAN_PROFILE.format(username=username))


def retrieve_candidates(
    query: str,
    min_experience_years: int = 0,
    seniority_tier: str = "",
    required_language: str = "",
    has_leadership: bool = False,
) -> str:
    human_msg = RETRIEVAL_HUMAN_SEARCH.format(
        query=query,
        min_experience_years=min_experience_years,
        seniority_tier=seniority_tier,
        required_language=required_language,
        has_leadership=has_leadership,
    )
    return _run_agent(RETRIEVAL_SYSTEM, human_msg)