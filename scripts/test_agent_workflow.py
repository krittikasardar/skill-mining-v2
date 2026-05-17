import json
import importlib.util
import pathlib
import os
import sys
import types

# Load agents module by file path to avoid package/import issues
project_root = pathlib.Path(__file__).resolve().parents[1]
agents_file = project_root / "data" / "agents" / "agents.py"
pipeline_file = project_root / "data" / "agents" / "pipeline.py"

# Load .env if available (prefer python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv(str(project_root / '.env'))
except Exception:
    env_path = project_root / '.env'
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

# Ensure a minimal `dotenv` module exists so downstream imports succeed
if 'dotenv' not in sys.modules:
    dot = types.ModuleType("dotenv")
    dot.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = dot

GROQ_KEY = os.getenv('GROQ_API_KEY')

import sys
import types

if not GROQ_KEY:
    # Provide minimal dummy modules for optional dependencies so import succeeds
    dot = types.ModuleType("dotenv")
    dot.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = dot

    lg = types.ModuleType("langchain_groq")
    class _DummyLLM:
        def __init__(self, *a, **k):
            pass
        def invoke(self, messages):
            return type("R", (), {"content": ""})()
    lg.ChatGroq = _DummyLLM
    sys.modules["langchain_groq"] = lg

    lc = types.ModuleType("langchain_core.messages")
    class HumanMessage:
        def __init__(self, content):
            self.content = content
    class SystemMessage:
        def __init__(self, content):
            self.content = content
    lc.HumanMessage = HumanMessage
    lc.SystemMessage = SystemMessage
    sys.modules["langchain_core.messages"] = lc
else:
    # Attempt to import real packages; fallback to minimal message types if needed
    try:
        import langchain_groq  # noqa: F401
    except Exception:
        lg = types.ModuleType("langchain_groq")
        class _DummyLLM2:
            def __init__(self, *a, **k):
                pass
            def invoke(self, messages):
                return type("R", (), {"content": ""})()
        lg.ChatGroq = _DummyLLM2
        sys.modules["langchain_groq"] = lg

    try:
        import langchain_core.messages  # noqa: F401
    except Exception:
        lc = types.ModuleType("langchain_core.messages")
        class HumanMessage:
            def __init__(self, content):
                self.content = content
        class SystemMessage:
            def __init__(self, content):
                self.content = content
        lc.HumanMessage = HumanMessage
        lc.SystemMessage = SystemMessage
        sys.modules["langchain_core.messages"] = lc

# Prepare package modules so relative imports inside agents.py work
data_pkg = types.ModuleType("data")
data_pkg.__path__ = [str(project_root / "data")]
sys.modules["data"] = data_pkg
agents_pkg = types.ModuleType("data.agents")
agents_pkg.__path__ = [str(project_root / "data" / "agents")]
sys.modules["data.agents"] = agents_pkg

spec = importlib.util.spec_from_file_location("data.agents.agents", str(agents_file))
agents = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agents)

pipeline_spec = importlib.util.spec_from_file_location("data.agents.pipeline", str(pipeline_file))
pipeline = importlib.util.module_from_spec(pipeline_spec)
pipeline_spec.loader.exec_module(pipeline)

# Stub LLM response object
class DummyResponse:
    def __init__(self, content):
        self.content = content

# Dummy LLM that returns canned outputs based on the system prompt
class DummyLLM:
    def __init__(self, malformed_skill: bool = False):
        self.malformed_skill = malformed_skill

    def invoke(self, messages):
        system = messages[0].content.lower()
        if "skill extraction expert" in system:
            if self.malformed_skill:
                return DummyResponse("```json\n{not valid json}\n```")
            content = json.dumps([
                {
                    "name": "FastAPI",
                    "category": "backend_framework",
                    "confidence": 0.92,
                    "justification": "Appears in repo metadata and language summary.",
                    "evidence": [
                        {"source": "repo:repo-a", "text": "Repo repo-a uses FastAPI"},
                        {"source": "summary:languages", "text": "Python appears across repos"},
                    ],
                }
            ])
            return DummyResponse(content)
        if "developer role analyst" in system:
            content = json.dumps({
                "primary_role": "creator",
                "confidence": 0.88,
                "supporting_signals": [
                    {"type": "ownership", "evidence": "Multiple original repos", "impact": "high"}
                ],
                "justification": "Original repos dominate and have stars/forks."
            })
            return DummyResponse(content)
        if "leadership and ownership analyst" in system:
            content = json.dumps({
                "leadership_level": "medium",
                "confidence": 0.74,
                "signals": [
                    {"type": "repository_popularity", "evidence": "repo-a stars=150", "impact": "high"}
                ],
                "justification": "Evidence of popular original repositories."
            })
            return DummyResponse(content)
        if "professional technical writer" in system:
            return DummyResponse(
                "Jane Doe builds backend services with FastAPI, grounded in repo evidence. "
                "They primarily act as a creator, owning multiple original repositories. "
                "Their collaboration signals are moderate, based on repository popularity. "
                "Overall, they show consistent backend-focused contributions."
            )
        return DummyResponse("{}")

# Replace real LLM and GitHub tools with stubs
agents.llm = DummyLLM()
agents.get_github_profile = lambda u: {"name": "Jane Doe", "bio": "Backend engineer.", "public_repos": 12, "followers": 42}

agents.retrieve_skill_evidence = lambda u: [
    {"source": "repo:repo-a", "type": "metadata", "content": "Repo repo-a uses FastAPI", "metadata": {}},
    {"source": "summary:languages", "type": "metadata", "content": "Python appears across repos", "metadata": {}},
]
agents.retrieve_role_evidence = lambda u: [
    {"source": "repo:repo-a", "type": "metadata", "content": "repo-a stars=150 forks=10 fork=False", "metadata": {}},
]
agents.retrieve_leadership_evidence = lambda u: [
    {"source": "repo:repo-a", "type": "metadata", "content": "repo-a stars=150 forks=10", "metadata": {}},
]

# Run full DAG
graph = pipeline.build_pipeline()
state = {"username": "janedoe"}
final_state = graph.invoke(state)

assert "skills" in final_state
assert "roles" in final_state
assert "leadership" in final_state
assert "summary" in final_state
assert isinstance(final_state["skills"], list)
assert isinstance(final_state["roles"], dict)
assert isinstance(final_state["leadership"], dict)
assert isinstance(final_state["summary"], str)

# Malformed JSON handling
agents.llm = DummyLLM(malformed_skill=True)
bad_state = agents.skill_extractor_agent({"username": "janedoe"})
assert bad_state["skills"] == []
assert "skills_error" in bad_state.get("retrieved_evidence", {})

print(json.dumps(final_state, indent=2))
