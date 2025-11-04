# application/services/repo_service.py
"""
Combined service that uses both API and Git operations
This is what you import in your UI/API
"""

from .github_api_service import GitHubAPIService
from .git_operations_service import GitOperationsService, RepoMetadata
from typing import Dict, Optional, List


class RepoService:
    """
    Unified service for all repository operations.
    
    Use this in your UI/API - it combines both services intelligently.
    """
    
    def __init__(self):
        self.api = GitHubAPIService()
        self.git = GitOperationsService()
    
    async def search_and_validate(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search repos and validate they're accessible
        
        Example:
            >>> service = RepoService()
            >>> results = await service.search_and_validate("llmlingua")
        """
        # Search using API
        results = await self.api.search_repositories(query, limit)
        
        # Optionally validate each (costs API calls)
        # for repo in results:
        #     repo['validated'] = await self.api.validate_repository(
        #         repo['owner'], repo['name']
        #     )
        
        return results
    
    async def prepare_repository(
        self,
        repo_url: str,
        use_cache: bool = True
    ) -> tuple[Dict, RepoMetadata]:
        """
        Get repo info (API) + clone it (Git)
        
        Returns:
            Tuple of (repo_info, cloned_metadata)
            
        Example:
            >>> info, metadata = await service.prepare_repository(
            ...     "https://github.com/user/repo"
            ... )
            >>> print(f"Repo has {info['stars']} stars")
            >>> print(f"Cloned to {metadata.local_path}")
        """
        # Parse URL
        owner, name = self.api.parse_repo_url(repo_url)
        
        # Get info from API
        info = await self.api.get_repository_info(owner, name)
        
        # Clone repo
        metadata = await self.git.clone_repository(repo_url, use_cache)
        
        return info, metadata
    
    async def analyze_repository_content(
        self,
        repo_url: str,
        max_files: int = 10
    ) -> Dict:
        """
        Complete analysis: clone + read files + return content
        
        This is what you'd call from the analyzer agent
        """
        # Clone
        metadata = await self.git.clone_repository(repo_url)
        
        try:
            # List Python files
            py_files = self.git.list_python_files(metadata.local_path)
            
            # Read up to max_files
            files_to_read = py_files[:max_files]
            file_contents = self.git.read_multiple_files(
                metadata.local_path,
                files_to_read
            )
            
            # Get structure
            structure = self.git.get_repo_structure(metadata.local_path)
            
            return {
                "success": True,
                "repo_url": repo_url,
                "local_path": metadata.local_path,
                "total_py_files": len(py_files),
                "analyzed_files": len(file_contents),
                "file_contents": file_contents,
                "structure": structure
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }