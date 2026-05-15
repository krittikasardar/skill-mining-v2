import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from .tools import get_github_profile, get_github_repos, get_github_languages

load_dotenv()

# Initialize the LLM once — all agents share it
llm = ChatGroq(
    model="llama-3.1-8b-instant",  # Using current LLaMA 3.1 instant model
    api_key=os.getenv("GROQ_API_KEY")
)


# ── Agent 1: Skill Extractor ──────────────────────────────────────────
# def skill_extractor_agent(state):
#     """Looks at languages and repos, extracts technical skills"""
#     username = state["username"]
    
#     # Use the tool to get real data
#     languages = get_github_languages(username)
#     repos = get_github_repos(username)
    
#     # Format data for the LLM
#     repo_text = "\n".join([
#         f"- {r['name']} ({r['language']}): {r['description']}"
#         for r in repos
#     ])
    
#     lang_text = ", ".join([f"{lang}({count} repos)" for lang, count in languages])
    
#     messages = [
#         SystemMessage(content="""You are a skill extraction specialist.
#         Given GitHub data, extract the developer's technical skills.
#         Be specific. List programming languages, frameworks, and domains.
#         Keep it concise — maximum 5 bullet points."""),
        
#         HumanMessage(content=f"""
#         Languages used: {lang_text}
        
#         Top repositories:
#         {repo_text}
        
#         What are this developer's main technical skills?
#         """)
#     ]
    
#     response = llm.invoke(messages)
    
#     # Save result to state so next agents can use it
#     state["skills"] = response.content
#     print("Agent 1 done: Skills extracted")
#     return state

def skill_extractor_agent(state):
    """Extracts technical skills with evidence + confidence"""

    username = state["username"]
    
    # Temporary: still using API
    languages = get_github_languages(username)
    repos = get_github_repos(username)

    # Convert to "pseudo-evidence" (important for future RAG alignment)
    evidence_chunks = []
    
    for r in repos:
        evidence_chunks.append({
            "repo": r["name"],
            "type": "repo_metadata",
            "text": f"{r['name']} uses {r['language']}. Description: {r['description']}"
        })

    for lang, count in languages:
        evidence_chunks.append({
            "repo": "multiple",
            "type": "language_summary",
            "text": f"{lang} used in {count} repositories"
        })

    context = "\n".join([f"- {c['text']}" for c in evidence_chunks])

    messages = [
        SystemMessage(content="""
You are a skill extraction expert.

Extract technical skills from GitHub data.

IMPORTANT:
- Only include skills supported by evidence
- Do NOT assign all skills the same confidence
- Confidence should reflect:
  - frequency of use
  - consistency across repositories
- Select only the most representative evidence (max 4 per skill)
- Avoid repetition in evidence

For each skill return:
- name
- confidence (0 to 1)
- justification (must explain WHY confidence is high/low)
- evidence (diverse, non-redundant snippets)

Return JSON ONLY.
"""),
        HumanMessage(content=f"""
GitHub Evidence:
{context}

Extract the developer's skills.
""")
    ]

    response = llm.invoke(messages)

    try:
        # Clean the response content - extract JSON from markdown code blocks
        content = response.content.strip()
        
        # Look for JSON code block
        if '```json' in content:
            # Find the start of the JSON block
            start_idx = content.find('```json') + 7
            # Find the end of the JSON block
            end_idx = content.find('```', start_idx)
            if end_idx != -1:
                content = content[start_idx:end_idx].strip()
            else:
                # If no closing ```, take everything after ```json
                content = content[start_idx:].strip()
        elif content.startswith('```'):
            # Handle case where it's just ``` without json
            start_idx = content.find('```') + 3
            end_idx = content.find('```', start_idx)
            if end_idx != -1:
                content = content[start_idx:end_idx].strip()
            else:
                content = content[start_idx:].strip()
        
        # Remove any trailing text after the JSON
        # Find the last } or ] to get just the JSON
        last_brace = max(content.rfind('}'), content.rfind(']'))
        if last_brace != -1:
            content = content[:last_brace + 1]
        
        state["skills"] = json.loads(content)
    except Exception as e:
        print(f"JSON parsing error: {e}")
        state["skills"] = {"error": response.content}

    print("Skill agent upgraded (structured + grounded)")
    return state


# ── Agent 2: Role Analyzer ────────────────────────────────────────────
def role_analyzer_agent(state):
    """Looks at repos to determine if developer is creator or contributor"""
    username = state["username"]
    repos = get_github_repos(username)
    
    original = [r for r in repos if not r["is_fork"]]
    forked = [r for r in repos if r["is_fork"]]
    
    repo_summary = f"""
    Total repos: {len(repos)}
    Original repos (created by them): {len(original)}
    Forked repos (contributed to others): {len(forked)}
    
    Their original repos:
    """ + "\n".join([f"- {r['name']}: {r['stars']} stars, {r['forks']} forks" for r in original[:5]])
    
    messages = [
        SystemMessage(content="""You are a developer role analyst.
        Based on GitHub repository data, determine what role this developer
        typically takes: creator, contributor, maintainer, or learner.
        Give a short 2-3 sentence analysis."""),
        
        HumanMessage(content=repo_summary)
    ]
    
    response = llm.invoke(messages)
    state["roles"] = response.content
    print("Agent 2 done: Roles analyzed")
    return state


# ── Agent 3: Profile Summarizer ───────────────────────────────────────
def summarizer_agent(state):
    """Takes skills + roles and writes the final developer profile"""
    profile = get_github_profile(state["username"])
    
    messages = [
        SystemMessage(content="""You are a professional technical writer.
        Write a short, clear developer profile summary (3-4 sentences).
        Make it sound professional, like something on a portfolio site."""),
        
        HumanMessage(content=f"""
        Developer name: {profile['name']}
        Bio: {profile['bio']}
        Public repos: {profile['public_repos']}
        Followers: {profile['followers']}
        
        Skills analysis:
        {state['skills']}
        
        Role analysis:
        {state['roles']}
        
        Write a professional summary of this developer.
        """)
    ]
    
    response = llm.invoke(messages)
    state["summary"] = response.content
    print("Agent 3 done: Summary written")
    return state