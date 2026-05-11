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
    
    
if __name__ == "__main__":
    print("Script is running...")
    print(get_github_profile("torvalds"))
    print(get_github_languages("torvalds"))