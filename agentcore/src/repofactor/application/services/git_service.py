# services/git_service.py
"""
Git operations: clone, list files, extract content
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional, List
import asyncio
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RepoMetadata:
    """Metadata about cloned repo"""
    local_path: str
    repo_url: str
    owner: str
    name: str
    
    def cleanup(self):
        """Remove cloned repo"""
        if os.path.exists(self.local_path):
            shutil.rmtree(self.local_path)
            logger.info(f"Cleaned up repo: {self.local_path}")


class GitService:
    """
    Handles Git operations with caching.
    זה דומה למה שעשית ב-AutoFix עם file operations
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.getenv("REPO_CACHE_DIR", "./cache/repos")
        os.makedirs(self.cache_dir, exist_ok=True)
    
    async def clone_repository(
        self,
        repo_url: str,
        use_cache: bool = True
    ) -> RepoMetadata:
        """
        Clone repository with optional caching.
        
        Args:
            repo_url: GitHub URL (https://github.com/user/repo)
            use_cache: Whether to use cached version if exists
        
        Returns:
            RepoMetadata with local path
        """
        
        # Extract owner/repo from URL
        owner, repo_name = self._extract_repo_info(repo_url)
        
        # Check cache
        cache_path = os.path.join(self.cache_dir, owner, repo_name)
        if use_cache and os.path.exists(cache_path):
            logger.info(f"Using cached repo: {cache_path}")
            return RepoMetadata(
                local_path=cache_path,
                repo_url=repo_url,
                owner=owner,
                name=repo_name
            )
        
        # Clone to temp location, then move to cache
        temp_dir = tempfile.mkdtemp(prefix="repo_clone_")
        
        try:
            # Use GitPython (install: pip install GitPython)
            from git import Repo
            
            logger.info(f"Cloning {repo_url} to {temp_dir}")
            
            # Run clone in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: Repo.clone_from(
                    repo_url,
                    temp_dir,
                    depth=1,  # Shallow clone for speed
                    branch='main'
                )
            )
            
            # Move to cache
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            shutil.move(temp_dir, cache_path)
            
            logger.info(f"Cached repo at: {cache_path}")
            
            return RepoMetadata(
                local_path=cache_path,
                repo_url=repo_url,
                owner=owner,
                name=repo_name
            )
        
        except Exception as e:
            logger.error(f"Failed to clone repo: {e}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise
    
    def _extract_repo_info(self, repo_url: str) -> tuple:
        """Extract owner/repo from GitHub URL"""
        # https://github.com/user/repo → ('user', 'repo')
        parts = repo_url.rstrip('/').split('/')
        repo_name = parts[-1].replace('.git', '')
        owner = parts[-2]
        return owner, repo_name
    
    def list_python_files(
        self,
        repo_path: str,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[str]:
        """
        List all Python files in repo.
        זה כמו agent.list_py_files אבל עם filtering
        """
        
        exclude_patterns = exclude_patterns or [
            '__pycache__', '.git', 'venv', '.venv',
            'node_modules', '.egg-info', 'dist', 'build'
        ]
        
        py_files = []
        for root, dirs, files in os.walk(repo_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(
                pattern in d for pattern in exclude_patterns
            )]
            
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    # Store relative path
                    rel_path = os.path.relpath(full_path, repo_path)
                    py_files.append(rel_path)
        
        return sorted(py_files)
    
    def read_file(self, repo_path: str, file_path: str) -> str:
        """Read file content"""
        full_path = os.path.join(repo_path, file_path)
        
        # Security: prevent path traversal
        if not os.path.abspath(full_path).startswith(os.path.abspath(repo_path)):
            raise ValueError(f"Invalid path: {file_path}")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def read_multiple_files(
        self,
        repo_path: str,
        file_paths: List[str]
    ) -> Dict[str, str]:
        """Read multiple files at once"""
        return {
            path: self.read_file(repo_path, path)
            for path in file_paths
        }


# Example usage
async def test_git_service():
    service = GitService()
    
    # Clone repo
    metadata = await service.clone_repository(
        "https://github.com/your/repo"
    )
    
    # List files
    files = service.list_python_files(metadata.local_path)
    print(f"Found {len(files)} Python files")
    
    # Read files
    if files:
        content = service.read_file(metadata.local_path, files[0])
        print(f"First file ({files[0]}) has {len(content)} characters")
    
    # Cleanup
    metadata.cleanup()
