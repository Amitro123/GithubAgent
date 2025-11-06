# application/services/github_api_service.py
"""
GitHub API operations: search, validate, metadata
Uses GitHub REST API - no local cloning
"""

import httpx
from typing import List, Dict, Optional
import os
from datetime import datetime, timedelta, timezone
import re


class GitHubAPIService:
    """
    Service for GitHub API operations.
    Use this for:
    - Searching repositories
    - Validating repo URLs
    - Getting metadata (stars, language, etc.)
    - Checking rate limits
    """
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RepoIntegrator/1.0"
        }
        
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
    
    async def search_repositories(
        self, 
        query: str, 
        limit: int = 5,
        language: Optional[str] = None
    ) -> List[Dict]:
        """
        Search GitHub repositories via API
        
        Example:
            >>> service = GitHubAPIService()
            >>> results = await service.search_repositories("llmlingua")
        """
        search_query = query
        if language:
            search_query += f" language:{language}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/search/repositories",
                    params={
                        "q": search_query,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": limit
                    },
                    headers=self.headers,
                    timeout=10.0,
                    follow_redirects=True
                )
                
                response.raise_for_status()
                data = response.json()
                
                return [
                    {
                        "full_name": repo["full_name"],
                        "owner": repo["owner"]["login"],
                        "name": repo["name"],
                        "description": repo["description"] or "No description",
                        "stars": repo["stargazers_count"],
                        "language": repo["language"] or "Unknown",
                        "updated": self._format_date(repo["updated_at"]),
                        "html_url": repo["html_url"],
                        "clone_url": repo["clone_url"],
                        "default_branch": repo["default_branch"],
                        "size": repo["size"],
                    }
                    for repo in data.get("items", [])[:limit]
                ]
                
            except Exception as e:
                print(f"GitHub API error: {e}")
                return []
    
    async def validate_repository(self, owner: str, repo: str) -> bool:
        """Check if repository exists and is accessible"""
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.base_url}/repos/{owner}/{repo}"
                
                # Try with token first if available
                if self.token:
                    response = await client.get(
                        url,
                        headers=self.headers,
                        timeout=5.0,
                        follow_redirects=True
                    )
                    if response.status_code == 200:
                        return True
                
                # Try without token for public repos
                headers_no_auth = {
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "RepoIntegrator/1.0"
                }
                
                response = await client.get(
                    url,
                    headers=headers_no_auth,
                    timeout=5.0,
                    follow_redirects=True
                )
                
                return response.status_code == 200
                
            except Exception as e:
                print(f"validate_repository exception: {e}")
                return False
    
    async def get_repository_info(self, owner: str, repo: str) -> Optional[Dict]:
        """Get detailed repository information"""
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.base_url}/repos/{owner}/{repo}"
                
                # Try with token first if available
                if self.token:
                    try:
                        response = await client.get(
                            url,
                            headers=self.headers,
                            timeout=10.0,
                            follow_redirects=True
                        )
                        if response.status_code == 200:
                            repo_data = response.json()
                            return self._format_repo_data(repo_data)
                    except:
                        pass
                
                # Try without token for public repos
                headers_no_auth = {
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "RepoIntegrator/1.0"
                }
                
                response = await client.get(
                    url,
                    headers=headers_no_auth,
                    timeout=10.0,
                    follow_redirects=True
                )
                response.raise_for_status()
                
                repo_data = response.json()
                return self._format_repo_data(repo_data)
                
            except Exception as e:
                print(f"get_repository_info exception: {e}")
                return None
    
    def _format_repo_data(self, repo_data: Dict) -> Dict:
        """Format repository data from GitHub API"""
        return {
            "full_name": repo_data["full_name"],
            "description": repo_data["description"],
            "stars": repo_data["stargazers_count"],
            "language": repo_data["language"],
            "size": repo_data["size"],
            "default_branch": repo_data["default_branch"],
            "topics": repo_data.get("topics", []),
        }
    
    def parse_repo_url(self, url: str) -> tuple[str, str]:
        """Parse owner and repo name from GitHub URL"""
        url = url.rstrip('/').replace('.git', '')
        pattern = r'github\.com/([^/]+)/([^/]+)'
        match = re.search(pattern, url)
        
        if match:
            return match.group(1), match.group(2)
        
        parts = url.split('/')
        if len(parts) >= 2:
            return parts[-2], parts[-1]
        
        raise ValueError(f"Invalid GitHub URL: {url}")
    
    def is_valid_github_url(self, url: str) -> bool:
        """Validate if string is a valid GitHub repository URL"""
        pattern = r'(https?://)?(www\.)?github\.com/[\w-]+/[\w.-]+'
        return bool(re.match(pattern, url))
    
    def _format_date(self, date_str: str) -> str:
        """Format ISO date to human readable"""
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            delta = now - date
            
            if delta < timedelta(hours=1):
                minutes = int(delta.total_seconds() / 60)
                return f"{minutes}m ago" if minutes > 0 else "just now"
            elif delta < timedelta(days=1):
                hours = int(delta.total_seconds() / 3600)
                return f"{hours}h ago"
            elif delta < timedelta(days=7):
                return f"{delta.days}d ago"
            elif delta < timedelta(days=30):
                weeks = delta.days // 7
                return f"{weeks}w ago"
            else:
                months = delta.days // 30
                return f"{months}mo ago"
        except:
            return "recently"