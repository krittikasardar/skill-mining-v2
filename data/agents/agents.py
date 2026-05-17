import json
import os
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from .tools import (
    get_github_profile,
    retrieve_leadership_evidence,
    retrieve_role_evidence,
    retrieve_skill_evidence,
)

load_dotenv()

# Initialize the LLM once — all agents share it
llm = ChatGroq(
    model="llama-3.1-8b-instant",  # Using current LLaMA 3.1 instant model
    api_key=os.getenv("GROQ_API_KEY")
)


def _strip_json_wrappers(text: str) -> str:
    content = text.strip()
    if "```" in content:
        if "```json" in content:
            start_idx = content.find("```json") + 7
        else:
            start_idx = content.find("```") + 3
        end_idx = content.find("```", start_idx)
        if end_idx != -1:
            content = content[start_idx:end_idx].strip()
        else:
            content = content[start_idx:].strip()

    # Trim to the last closing bracket/brace
    last_idx = max(content.rfind("}"), content.rfind("]"))
    if last_idx != -1:
        content = content[: last_idx + 1]
    return content


def safe_json_parse(
    text: str,
    expected_type: type,
    required_keys: Optional[List[str]] = None,
) -> Tuple[Optional[Any], Optional[str]]:
    try:
        content = _strip_json_wrappers(text)
        parsed = json.loads(content)
    except Exception as exc:
        return None, f"json_parse_error: {exc}"

    if not isinstance(parsed, expected_type):
        return None, f"json_type_error: expected {expected_type.__name__}"

    if required_keys:
        if isinstance(parsed, dict):
            missing = [k for k in required_keys if k not in parsed]
            if missing:
                return None, f"json_missing_keys: {', '.join(missing)}"
        if isinstance(parsed, list):
            for idx, item in enumerate(parsed):
                if not isinstance(item, dict):
                    return None, f"json_item_type_error: index {idx}"
                missing = [k for k in required_keys if k not in item]
                if missing:
                    return None, f"json_missing_keys: index {idx} -> {', '.join(missing)}"

    return parsed, None


def _ensure_state(state: Dict[str, Any]) -> Dict[str, Any]:
    state.setdefault("retrieved_evidence", {})
    state.setdefault("skills", [])
    state.setdefault("roles", {})
    state.setdefault("leadership", {})
    state.setdefault("summary", "")
    return state


def _format_evidence(chunks: List[Dict[str, Any]], max_items: int = 25) -> str:
    seen = set()
    lines: List[str] = []
    for chunk in chunks:
        key = (chunk.get("source"), chunk.get("type"), chunk.get("content"))
        if key in seen:
            continue
        seen.add(key)
        lines.append(
            f"- source={chunk.get('source')} type={chunk.get('type')} content={chunk.get('content')}"
        )
        if len(lines) >= max_items:
            break
    return "\n".join(lines)


SKILL_SYSTEM_PROMPT = """
You are a skill extraction expert.
Return a JSON array of objects with:
- name
- category
- confidence (0 to 1)
- justification
- evidence: array of {source, text}

Rules:
- Only infer skills supported by evidence.
- Prioritize frameworks, libraries, and tools over generic terms.
- No duplicate or redundant evidence per skill.
- Confidence must reflect evidence strength and consistency.
- Return JSON only. No markdown. No extra text.
""".strip()


ROLE_SYSTEM_PROMPT = """
You are a developer role analyst.
Classify the developer as one primary role: creator, contributor, maintainer, or learner.
Return JSON with:
- primary_role
- confidence (0 to 1)
- supporting_signals: array of {type, evidence, impact}
- justification

Rules:
- Use only the provided evidence.
- Do not make assumptions beyond evidence.
- Return JSON only. No markdown. No extra text.
""".strip()


LEADERSHIP_SYSTEM_PROMPT = """
You are a leadership and ownership analyst.
Evaluate leadership signals using evidence only.
Return JSON with:
- leadership_level (high|medium|low|none)
- confidence (0 to 1)
- signals: array of {type, evidence, impact}
- justification

Rules:
- Do not inflate leadership claims.
- Use only the provided evidence.
- Return JSON only. No markdown. No extra text.
""".strip()


SUMMARY_SYSTEM_PROMPT = """
You are a professional technical writer.
Write a 4-6 sentence developer profile summary.
Rules:
- Ground every claim in the provided evidence.
- Avoid marketing exaggeration or unsupported claims.
- Tone: professional, concise, technical.
""".strip()


def skill_extractor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts technical skills with evidence + confidence."""
    state = _ensure_state(state)
    username = state["username"]

    evidence_chunks = retrieve_skill_evidence(username)
    state["retrieved_evidence"]["skills"] = evidence_chunks

    context = _format_evidence(evidence_chunks)
    messages = [
        SystemMessage(content=SKILL_SYSTEM_PROMPT),
        HumanMessage(content=f"Username: {username}\nEvidence:\n{context}\n"),
    ]

    response = llm.invoke(messages)
    parsed, error = safe_json_parse(
        response.content,
        expected_type=list,
        required_keys=["name", "category", "confidence", "justification", "evidence"],
    )

    if error:
        state["retrieved_evidence"]["skills_error"] = {
            "error": error,
            "raw": response.content,
        }
        state["skills"] = []
    else:
        state["skills"] = parsed

    return state


# ── Agent 2: Role Analyzer ────────────────────────────────────────────
def role_analyzer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes repos to determine developer role."""
    state = _ensure_state(state)
    username = state["username"]

    evidence_chunks = retrieve_role_evidence(username)
    state["retrieved_evidence"]["roles"] = evidence_chunks

    context = _format_evidence(evidence_chunks)
    messages = [
        SystemMessage(content=ROLE_SYSTEM_PROMPT),
        HumanMessage(content=f"Username: {username}\nEvidence:\n{context}\n"),
    ]

    response = llm.invoke(messages)
    parsed, error = safe_json_parse(
        response.content,
        expected_type=dict,
        required_keys=["primary_role", "confidence", "supporting_signals", "justification"],
    )

    if error:
        state["retrieved_evidence"]["roles_error"] = {
            "error": error,
            "raw": response.content,
        }
        state["roles"] = {}
    else:
        state["roles"] = parsed

    return state


def leadership_detector_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Detects leadership and ownership signals."""
    state = _ensure_state(state)
    username = state["username"]

    evidence_chunks = retrieve_leadership_evidence(username)
    state["retrieved_evidence"]["leadership"] = evidence_chunks

    context = _format_evidence(evidence_chunks)
    messages = [
        SystemMessage(content=LEADERSHIP_SYSTEM_PROMPT),
        HumanMessage(content=f"Username: {username}\nEvidence:\n{context}\n"),
    ]

    response = llm.invoke(messages)
    parsed, error = safe_json_parse(
        response.content,
        expected_type=dict,
        required_keys=["leadership_level", "confidence", "signals", "justification"],
    )

    if error:
        state["retrieved_evidence"]["leadership_error"] = {
            "error": error,
            "raw": response.content,
        }
        state["leadership"] = {}
    else:
        state["leadership"] = parsed

    return state


# ── Agent 3: Profile Summarizer ───────────────────────────────────────
def summarizer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Synthesizes skills, roles, and leadership into a profile summary."""
    state = _ensure_state(state)
    profile = get_github_profile(state["username"])

    messages = [
        SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                "Developer profile data:\n"
                f"name={profile.get('name')}\n"
                f"bio={profile.get('bio')}\n"
                f"public_repos={profile.get('public_repos')}\n"
                f"followers={profile.get('followers')}\n\n"
                "Skills output:\n"
                f"{state.get('skills')}\n\n"
                "Role output:\n"
                f"{state.get('roles')}\n\n"
                "Leadership output:\n"
                f"{state.get('leadership')}\n"
            )
        ),
    ]

    response = llm.invoke(messages)
    state["summary"] = response.content.strip()
    return state