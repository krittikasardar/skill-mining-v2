from langgraph.graph import StateGraph, END
from typing import TypedDict
from .agents import skill_extractor_agent, role_analyzer_agent, summarizer_agent


# Define what the shared state looks like
# Every agent reads from and writes to this state
class DeveloperState(TypedDict):
    username: str
    skills: str
    roles: str
    summary: str


def build_pipeline():
    # Create the graph
    graph = StateGraph(DeveloperState)
    
    # Add each agent as a node
    graph.add_node("skill_extractor", skill_extractor_agent)
    graph.add_node("role_analyzer", role_analyzer_agent)
    graph.add_node("summarizer", summarizer_agent)
    
    # Define the flow: who runs after who
    graph.set_entry_point("skill_extractor")
    graph.add_edge("skill_extractor", "role_analyzer")
    graph.add_edge("role_analyzer", "summarizer")
    graph.add_edge("summarizer", END)
    
    return graph.compile()