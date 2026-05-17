from typing import Any, Dict, List, TypedDict
from langgraph.graph import StateGraph, END

from .agents import (
    leadership_detector_agent,
    role_analyzer_agent,
    skill_extractor_agent,
    summarizer_agent,
)


# Define what the shared state looks like
# Every agent reads from and writes to this state
class DeveloperState(TypedDict):
    username: str
    retrieved_evidence: Dict[str, Any]
    skills: List[Dict[str, Any]]
    roles: Dict[str, Any]
    leadership: Dict[str, Any]
    summary: str


def build_pipeline():
    # Create the graph (DAG) with a typed shared state.
    graph = StateGraph(DeveloperState)

    # Add each agent as a node (sequential workflow).
    graph.add_node("skill_extractor", skill_extractor_agent)
    graph.add_node("role_analyzer", role_analyzer_agent)
    graph.add_node("leadership_detector", leadership_detector_agent)
    graph.add_node("summarizer", summarizer_agent)

    # Define the flow: who runs after who.
    graph.set_entry_point("skill_extractor")
    graph.add_edge("skill_extractor", "role_analyzer")
    graph.add_edge("role_analyzer", "leadership_detector")
    graph.add_edge("leadership_detector", "summarizer")
    graph.add_edge("summarizer", END)

    return graph.compile()