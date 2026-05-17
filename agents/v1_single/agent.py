"""
agents/v1_single/agent.py
Single LangChain 1.x agent using create_agent (langgraph-backed).
Handles both Mode 1 (profile deep dive) and Mode 2 (candidate search).
"""
import re
import time
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

from agents.tools import ALL_TOOLS
from agents.v1_single.prompts import (
    SYSTEM_PROMPT,
    PROFILE_ANALYSIS_PROMPT,
    CANDIDATE_SEARCH_PROMPT,
)
from config import settings
from response_logger import save_response

_USERNAME_PATTERNS = [
    r"@([a-zA-Z0-9_-]+)",
    r"profile\s+(?:of\s+|for\s+)?([a-zA-Z0-9_-]+)",
    r"analyze\s+([a-zA-Z0-9_-]+)",
    r"about\s+([a-zA-Z0-9_-]+)",
    r"tell me about\s+([a-zA-Z0-9_-]+)",
]

_MODE1_KEYWORDS = [
    "analyze", "profile of", "tell me about", "deep dive", "skills of",
    "what does", "who is", "about @", "roles of", "experience of",
]


def _detect_mode(query: str) -> tuple[str, str | None]:
    q_lower = query.lower()
    for pattern in _USERNAME_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return "profile", match.group(1)
    if any(kw in q_lower for kw in _MODE1_KEYWORDS):
        return "profile", None
    return "search", None


def _extract_output(result: dict) -> tuple[str, list]:
    """
    Extract final text output and tool call steps from agent state.
    LangChain 1.x returns {"messages": [HumanMessage, ..., AIMessage]}
    """
    messages = result.get("messages", [])
    
    # Final output = last AIMessage content
    output = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            output = msg.content
            break
    
    # Intermediate steps = tool calls from messages
    steps = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                steps.append({
                    "tool": tc.get("name", ""),
                    "input": str(tc.get("args", ""))[:200],
                    "output": "",
                })
    
    return output, steps


def run_query(query: str, chat_history: list | None = None) -> dict:
    start = time.time()
    mode, username = _detect_mode(query)

    if mode == "profile" and username:
        enriched_query = PROFILE_ANALYSIS_PROMPT.format(username=username)
    elif mode == "search":
        enriched_query = CANDIDATE_SEARCH_PROMPT.format(query=query)
    else:
        enriched_query = query

    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=0,
        api_key=settings.openai_api_key,
    )

    agent = create_agent(
        llm,
        ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )

    # Build message history
    messages = []
    for h in (chat_history or []):
        if h.get("role") == "user":
            messages.append(HumanMessage(content=h["content"]))
        elif h.get("role") == "assistant":
            messages.append(AIMessage(content=h["content"]))
    messages.append(HumanMessage(content=enriched_query))

    result = agent.invoke({"messages": messages})
    output, steps = _extract_output(result)

    latency = round(time.time() - start, 2)

    save_response(
        query=query,
        response=output,
        agent_version="v1_single",
        mode=mode,
        metadata={"latency_seconds": latency, "username": username},
    )

    return {
        "mode": mode,
        "username": username,
        "output": output,
        "intermediate_steps": steps,
        "latency_seconds": latency,
        "agent_version": "v1_single",
    }