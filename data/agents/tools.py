from typing import Any, Dict, List
import requests

def get_github_profile(username):
    """Fetches basic profile info of a GitHub user"""
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url)
    data = response.json()
    
    return {
        "name": data.get("name", username),
        "bio": data.get("bio", ""),
        "public_repos": data.get("public_repos", 0),
        "followers": data.get("followers", 0)
    }

def get_github_repos(username):
    """Fetches top 10 public repos of a GitHub user"""
    url = f"https://api.github.com/users/{username}/repos"
    params = {"sort": "stars", "per_page": 10}
    response = requests.get(url, params=params)
    repos = response.json()
    
    result = []
    for repo in repos:
        result.append({
            "name": repo["name"],
            "description": repo.get("description", ""),
            "language": repo.get("language", "Unknown"),
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "is_fork": repo["fork"]  # True means they forked it, not created it
        })
    
    return result

def get_github_languages(username):
    """Gets all languages used across repos and counts them"""
    url = f"https://api.github.com/users/{username}/repos"
    params = {"per_page": 30}
    response = requests.get(url, params=params)
    repos = response.json()
    
    language_count = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            language_count[lang] = language_count.get(lang, 0) + 1
    
    # Sort by frequency
    sorted_langs = sorted(language_count.items(), key=lambda x: x[1], reverse=True)
    return sorted_langs


def _repo_to_chunk(repo: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": f"repo:{repo['name']}",
        "type": "metadata",
        "content": (
            f"Repo {repo['name']} uses {repo.get('language') or 'Unknown'}; "
            f"stars={repo.get('stars', 0)}, forks={repo.get('forks', 0)}; "
            f"fork={repo.get('is_fork', False)}; "
            f"description={repo.get('description') or ''}"
        ),
        "metadata": {
            "name": repo.get("name"),
            "language": repo.get("language"),
            "stars": repo.get("stars", 0),
            "forks": repo.get("forks", 0),
            "is_fork": repo.get("is_fork", False),
        },
    }


def _languages_to_chunk(languages: List[Any]) -> Dict[str, Any]:
    summary = ", ".join([f"{lang}({count})" for lang, count in languages])
    return {
        "source": "summary:languages",
        "type": "metadata",
        "content": f"Languages used across repos: {summary}",
        "metadata": {"counts": dict(languages)},
    }


def retrieve_skill_evidence(username: str) -> List[Dict[str, Any]]:
    """
    Placeholder retrieval function for skill evidence.
    Structured to support future vector retrieval (ChromaDB).
    """
    repos = get_github_repos(username)
    languages = get_github_languages(username)

    chunks: List[Dict[str, Any]] = []
    for repo in repos:
        chunks.append(_repo_to_chunk(repo))

    if languages:
        chunks.append(_languages_to_chunk(languages))

    return chunks


def retrieve_role_evidence(username: str) -> List[Dict[str, Any]]:
    """
    Placeholder retrieval function for role evidence.
    Structured to support future vector retrieval (ChromaDB).
    """
    repos = get_github_repos(username)
    chunks: List[Dict[str, Any]] = []

    for repo in repos:
        chunks.append(_repo_to_chunk(repo))

    return chunks


def retrieve_leadership_evidence(username: str) -> List[Dict[str, Any]]:
    """
    Placeholder retrieval function for leadership evidence.
    Structured to support future vector retrieval (ChromaDB).
    """
    profile = get_github_profile(username)
    repos = get_github_repos(username)

    chunks: List[Dict[str, Any]] = []
    chunks.append({
        "source": "profile:github",
        "type": "metadata",
        "content": (
            f"Public repos={profile.get('public_repos', 0)}, "
            f"followers={profile.get('followers', 0)}"
        ),
        "metadata": {
            "public_repos": profile.get("public_repos", 0),
            "followers": profile.get("followers", 0),
        },
    })

    for repo in repos:
        chunks.append(_repo_to_chunk(repo))

    return chunks
    
    
if __name__ == "__main__":
    print("Script is running...")
    print(get_github_profile("torvalds"))
    print(get_github_languages("torvalds"))