import json
import importlib.util
import pathlib
import os
import sys
import types

# Load agents module by file path to avoid package/import issues
project_root = pathlib.Path(__file__).resolve().parents[1]
agents_file = project_root / "data" / "agents" / "agents.py"

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

# Stub LLM response object
class DummyResponse:
    def __init__(self, content):
        self.content = content

# Dummy LLM that returns canned outputs based on the system prompt
class DummyLLM:
    def invoke(self, messages):
        system = messages[0].content.lower()
        if 'skill extraction' in system or 'skill extraction expert' in system:
            # Return JSON (possibly wrapped in code fences to simulate real LLM)
            content = '''```json
[
  {
    "name": "Python",
    "confidence": 0.95,
    "justification": "Used across multiple top repos and common in descriptions.",
    "evidence": [
      "repo-a uses Python (web backend)",
      "repo-b uses Python (data processing)"
    ]
  }
]
```'''
            return DummyResponse(content)
        if 'developer role analyst' in system or 'role analyst' in system:
            return DummyResponse("This developer appears to be a creator/maintainer with multiple original repos.")
        if 'professional technical writer' in system or 'technical writer' in system:
            return DummyResponse("Jane Doe is a backend engineer with strong Python skills and experience building data pipelines.")
        # fallback
        return DummyResponse("{}")

# Replace real LLM and GitHub tools with stubs
agents.llm = DummyLLM()
agents.get_github_profile = lambda u: {"name": "Jane Doe", "bio": "Backend engineer.", "public_repos": 12, "followers": 42}
agents.get_github_repos = lambda u: [
    {"name": "repo-a", "description": "Web backend", "language": "Python", "stars": 150, "forks": 10, "is_fork": False},
    {"name": "repo-b", "description": "Data processing", "language": "Python", "stars": 80, "forks": 5, "is_fork": False},
]
agents.get_github_languages = lambda u: [("Python", 5), ("JavaScript", 2)]

# Run the agents
state = {"username": "janedoe"}
state = agents.skill_extractor_agent(state)
state = agents.role_analyzer_agent(state)
state = agents.summarizer_agent(state)

print(json.dumps(state, indent=2))
