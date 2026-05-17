"""
agents/v2_hierarchical/ranking_agent.py
Candidate ranking — direct LLM invocation, no template parsing.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agents.v2_hierarchical.prompts import RANKING_SYSTEM, RANKING_HUMAN
from config import settings


def rank_candidates(requirement: str, candidates: str) -> str:
    llm = ChatOpenAI(model=settings.llm_model, temperature=0, api_key=settings.openai_api_key)
    result = llm.invoke([
        SystemMessage(content=RANKING_SYSTEM),
        HumanMessage(content=RANKING_HUMAN.format(requirement=requirement, candidates=candidates)),
    ])
    return result.content