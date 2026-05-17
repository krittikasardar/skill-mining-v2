"""
ui/app.py — Streamlit frontend v2
Adds: LangSmith tracing toggle, Save Responses toggle, Eval Log viewer tab.
"""
import streamlit as st
import requests
import json
import time
from pathlib import Path

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="GitHub Profile Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Shared render helper ──────────────────────────────────────────────────────

def _render_result(data: dict, mode: str):
    output = data.get("output", "")
    latency = data.get("latency_seconds", 0)
    version = data.get("agent_version", "")
    error = data.get("error")

    if error:
        st.error(f"Agent error: {error}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Agent", version)
    col2.metric("Mode", data.get("mode", mode))
    col3.metric("Latency", f"{latency}s")

    st.divider()
    st.markdown(output)

    trace = data.get("pipeline_trace", [])
    if trace:
        with st.expander("🔬 Pipeline Trace (V2)"):
            for step in trace:
                st.json(step)

    steps = data.get("intermediate_steps", [])
    if steps:
        with st.expander(f"🔧 Agent Steps ({len(steps)} tool calls)"):
            for i, step in enumerate(steps, 1):
                st.markdown(f"**Step {i}: {step.get('tool')}**")
                st.caption(f"Input: {step.get('input', '')[:200]}")
                st.caption(f"Output: {step.get('output', '')[:300]}")
                st.divider()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Settings")

    agent_version = st.radio(
        "Agent Version",
        options=["v1", "v2"],
        index=0,
        horizontal=True,
    )

    st.divider()

    if agent_version == "v1":
        st.info("**V1 — Single Agent**\nOne LangChain agent + all tools.")
    else:
        st.info("**V2 — Hierarchical**\nOrchestrator → Retrieval → Analysis/Ranking → Synthesis")

    st.divider()

    # ── LangSmith Toggle ──
    st.subheader("🔭 LangSmith Tracing")
    try:
        root = requests.get(f"{API_BASE}/", timeout=3).json()
        tracing_on = root.get("tracing", False)
        save_on = root.get("save_responses", False)
        if tracing_on:
            st.success("✓ Tracing enabled")
            st.caption(f"Project: {root.get('langsmith_project', '')}")
        else:
            st.warning("Tracing disabled")
            st.caption("Set LANGSMITH_TRACING=true in .env to enable")
    except Exception:
        st.error("API offline")
        tracing_on = False
        save_on = False

    st.divider()

    # ── Save Responses Toggle ──
    st.subheader("💾 Response Saving")
    if save_on:
        st.success("✓ Saving responses for DeepEval")
        st.caption("Logs saved to ./eval_logs/")
    else:
        st.warning("Response saving disabled")
        st.caption("Set SAVE_RESPONSES=true in .env to enable")

    st.divider()

    # ── Collection Stats ──
    st.subheader("📊 Index Stats")
    if st.button("Refresh Stats"):
        try:
            stats = requests.get(f"{API_BASE}/stats", timeout=5).json()
            st.metric("Total Chunks", stats.get("total_chunks", 0))
            st.caption(f"Collection: {stats.get('collection', 'N/A')}")
        except Exception as e:
            st.error(f"API unavailable: {e}")


# ── Main tabs ─────────────────────────────────────────────────────────────────

st.title("🔍 GitHub Profile Intelligence")
st.caption(f"Agent: **{agent_version.upper()}**")

tab1, tab2, tab3, tab4 = st.tabs([
    "👤 Profile Deep Dive",
    "🎯 Candidate Search",
    "💬 Free Query",
    "📋 Eval Logs",
])

# ── Tab 1: Profile Deep Dive ──────────────────────────────────────────────────

with tab1:
    st.header("Profile Deep Dive")
    st.caption("Analyze a specific GitHub developer — skills, roles, leadership, experience")

    col1, col2 = st.columns([3, 1])
    with col1:
        username_input = st.text_input("GitHub Username", placeholder="e.g. karpathy", key="username_input")
    with col2:
        st.write("")
        st.write("")
        analyze_btn = st.button("Analyze", type="primary", key="analyze_btn", use_container_width=True)

    if analyze_btn and username_input:
        with st.spinner(f"Analyzing @{username_input} with {agent_version.upper()}..."):
            try:
                response = requests.get(
                    f"{API_BASE}/profile/{username_input.strip()}",
                    params={"agent_version": agent_version},
                    timeout=120,
                )
                if response.status_code == 200:
                    _render_result(response.json(), mode="profile")
                else:
                    st.error(f"API Error {response.status_code}: {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to API. Is the FastAPI server running on port 8000?")
            except Exception as e:
                st.error(f"Error: {e}")
    elif analyze_btn:
        st.warning("Please enter a GitHub username.")


# ── Tab 2: Candidate Search ───────────────────────────────────────────────────

with tab2:
    st.header("Candidate Search")
    st.caption("Find top 3 matching profiles for a role or requirement")

    query_input = st.text_area(
        "Role / Requirement",
        placeholder="e.g. Senior backend engineer with 5+ years Python and open source experience",
        height=100,
        key="search_query",
    )

    with st.expander("🔧 Advanced Filters"):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            min_years = st.number_input("Min Experience (years)", min_value=0, max_value=30, value=0)
        with fc2:
            seniority = st.selectbox("Seniority", ["", "junior", "mid", "senior", "staff"])
        with fc3:
            language = st.text_input("Required Language", placeholder="Python")
        with fc4:
            st.write("")
            leadership = st.checkbox("Leadership Required")

    search_btn = st.button("Find Candidates", type="primary", key="search_btn")

    if search_btn and query_input:
        with st.spinner(f"Searching with {agent_version.upper()}..."):
            try:
                payload = {
                    "query": query_input,
                    "agent_version": agent_version,
                    "min_experience_years": min_years,
                    "seniority_tier": seniority,
                    "required_language": language,
                    "has_leadership": leadership,
                }
                response = requests.post(f"{API_BASE}/search", json=payload, timeout=120)
                if response.status_code == 200:
                    _render_result(response.json(), mode="search")
                else:
                    st.error(f"API Error {response.status_code}: {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to API.")
            except Exception as e:
                st.error(f"Error: {e}")
    elif search_btn:
        st.warning("Please enter a requirement query.")


# ── Tab 3: Free Query ─────────────────────────────────────────────────────────

with tab3:
    st.header("Free Query")
    st.caption("Ask anything — agent auto-detects profile dive vs candidate search")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    free_query = st.chat_input("Ask about developers or search for candidates...")

    if free_query:
        st.session_state.chat_history.append({"role": "user", "content": free_query})
        with st.chat_message("user"):
            st.markdown(free_query)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    payload = {
                        "query": free_query,
                        "agent_version": agent_version,
                        "chat_history": st.session_state.chat_history[:-1],
                    }
                    response = requests.post(f"{API_BASE}/query", json=payload, timeout=120)
                    if response.status_code == 200:
                        data = response.json()
                        output = data.get("output", "No response")
                        st.markdown(output)
                        st.caption(
                            f"Mode: {data.get('mode')} | "
                            f"Agent: {data.get('agent_version')} | "
                            f"⏱ {data.get('latency_seconds')}s"
                        )
                        st.session_state.chat_history.append({"role": "assistant", "content": output})
                    else:
                        st.error(f"API Error {response.status_code}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to API.")
                except Exception as e:
                    st.error(str(e))

    if st.session_state.chat_history:
        if st.button("Clear History", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()


# ── Tab 4: Eval Logs ──────────────────────────────────────────────────────────

with tab4:
    st.header("📋 Evaluation Logs")
    st.caption("DeepEval-compatible JSONL response logs. Enable with SAVE_RESPONSES=true in .env")

    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("🔄 Refresh Logs", key="refresh_logs"):
            st.rerun()
    with col2:
        if st.button("🗑️ Clear All Logs", type="secondary", key="clear_logs"):
            try:
                requests.delete(f"{API_BASE}/eval/logs", timeout=5)
                st.success("Logs cleared")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    try:
        logs_data = requests.get(f"{API_BASE}/eval/logs", timeout=5).json()
        save_enabled = logs_data.get("save_responses_enabled", False)
        logs = logs_data.get("logs", {})

        if not save_enabled:
            st.warning("⚠️ Response saving is disabled. Set `SAVE_RESPONSES=true` in your `.env` file and restart the API.")

        if not logs:
            st.info("No eval logs found yet. Run some queries with SAVE_RESPONSES=true enabled.")
        else:
            for agent_ver, info in logs.items():
                with st.expander(f"**{agent_ver}** — {info['record_count']} records", expanded=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.caption(f"File: {info['file']}")
                    with col2:
                        # Download button
                        try:
                            dl = requests.get(f"{API_BASE}/eval/download/{agent_ver}", timeout=10)
                            if dl.status_code == 200:
                                st.download_button(
                                    label="⬇️ Download JSONL",
                                    data=dl.content,
                                    file_name=f"{agent_ver}_responses.jsonl",
                                    mime="application/x-ndjson",
                                    key=f"dl_{agent_ver}",
                                )
                        except Exception:
                            pass

                    # Preview last 3 records
                    try:
                        preview = requests.get(
                            f"{API_BASE}/eval/preview/{agent_ver}",
                            params={"limit": 3},
                            timeout=10,
                        ).json()
                        st.caption(f"Showing last {min(3, len(preview.get('preview', [])))} of {preview.get('total', 0)} records:")
                        for rec in preview.get("preview", []):
                            with st.container():
                                st.markdown(f"**Q:** {rec.get('input', '')[:150]}")
                                st.markdown(f"**A:** {rec.get('actual_output', '')[:300]}{'...' if len(rec.get('actual_output','')) > 300 else ''}")
                                meta = rec.get("metadata", {})
                                st.caption(
                                    f"Mode: {meta.get('mode')} | "
                                    f"Latency: {meta.get('latency_seconds')}s | "
                                    f"Time: {meta.get('timestamp', '')[:19]}"
                                )
                                st.divider()
                    except Exception as e:
                        st.error(f"Could not load preview: {e}")

        # DeepEval usage hint
        with st.expander("📖 How to use with DeepEval"):
            st.markdown("""
```python
import json
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric

# Load saved responses
with open("eval_logs/v1_single_responses.jsonl") as f:
    records = [json.loads(line) for line in f]

# Build test cases
test_cases = [
    LLMTestCase(
        input=r["input"],
        actual_output=r["actual_output"],
        retrieval_context=r["context"],
    )
    for r in records
]

# Run evaluation
metric = AnswerRelevancyMetric(threshold=0.7)
for tc in test_cases:
    metric.measure(tc)
    print(tc.input, "→ score:", metric.score)
```
            """)

    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API.")
    except Exception as e:
        st.error(f"Error loading logs: {e}")
