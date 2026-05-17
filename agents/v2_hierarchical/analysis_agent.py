"""
agents/v2_hierarchical/analysis_agent.py
Profile analysis — direct LLM invocation, no template parsing.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agents.v2_hierarchical.prompts import ANALYSIS_SYSTEM, ANALYSIS_HUMAN
from config import settings


def analyze_profile(profile_data: str, focus: str = "full profile analysis") -> str:
    llm = ChatOpenAI(model=settings.llm_model, temperature=0, api_key=settings.openai_api_key)
    result = llm.invoke([
        SystemMessage(content=ANALYSIS_SYSTEM),
        HumanMessage(content=ANALYSIS_HUMAN.format(profile_data=profile_data, focus=focus)),
    ])
    return result.content