# application/services/git_operations_service.py
"""
Git operations: clone, list files, read content
Works with local filesystem
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional, List
import asyncio
from dataclasses import dataclass
import logging

from repofactor.infrastructure.utils.cleanup_tools import cleanup_folder

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
            logger.info(f"Cleaned up: {self.local_path}")


class GitOperationsService:
    """
    Service for local Git operations.
    Use this for:
    - Cloning repositories
    - Reading files from cloned repos
    - Listing files
    - Working with local code
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.getenv("REPO_CACHE_DIR", "./cache/repos")
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def cleanup_cache(self, days_old: int = 7) -> List[str]:
        """Clean old cached repositories"""
        return cleanup_folder(self.cache_dir, days_old=days_old)
    
    def cleanup_temp_files(self) -> List[str]:
        """Clean temporary files from system temp directory"""
        temp_dir = tempfile.gettempdir()
        return cleanup_folder(temp_dir, patterns=[".tmp", ".temp"], days_old=1)
    
    async def clone_repository(
        self,
        repo_url: str,
        use_cache: bool = True,
        branch: str = "main"
    ) -> RepoMetadata:
        """
        Clone repository with optional caching
        
        Args:
            repo_url: GitHub URL
            use_cache: Use cached version if exists
            branch: Branch to clone (default: main)
        
        Returns:
            RepoMetadata with local path
            
        Example:
            >>> service = GitOperationsService()
            >>> repo = await service.clone_repository(
            ...     "https://github.com/user/repo"
            ... )
            >>> print(repo.local_path)
        """
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
        
        # Clone to temp, then move to cache
        temp_dir = tempfile.mkdtemp(prefix="repo_clone_")
        
        try:
            from git import Repo
            
            logger.info(f"Cloning {repo_url}")
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            def do_clone():
                try:
                    Repo.clone_from(
                        repo_url,
                        temp_dir,
                        depth=1,
                        branch=branch
                    )
                except Exception as e:
                    # Try 'master' if 'main' fails
                    if branch == "main":
                        logger.info("Trying 'master' branch")
                        Repo.clone_from(
                            repo_url,
                            temp_dir,
                            depth=1,
                            branch="master"
                        )
                    else:
                        raise
            
            await loop.run_in_executor(None, do_clone)
            
            # Move to cache
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            if os.path.exists(cache_path):
                shutil.rmtree(cache_path)
            shutil.move(temp_dir, cache_path)
            
            logger.info(f"Cached at: {cache_path}")
            
            return RepoMetadata(
                local_path=cache_path,
                repo_url=repo_url,
                owner=owner,
                name=repo_name
            )
        
        except Exception as e:
            logger.error(f"Clone failed: {e}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise
    
    def list_python_files(
        self,
        repo_path: str,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[str]:
        """
        List all Python files in repo
        
        Args:
            repo_path: Path to cloned repo
            exclude_patterns: Patterns to exclude
            
        Returns:
            List of relative file paths
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
                    rel_path = os.path.relpath(full_path, repo_path)
                    py_files.append(rel_path)
        
        return sorted(py_files)
    
    def read_file(self, repo_path: str, file_path: str) -> str:
        """
        Read file content
        
        Args:
            repo_path: Path to repo
            file_path: Relative path to file
            
        Returns:
            File content as string
        """
        full_path = os.path.join(repo_path, file_path)
        
        # Security: prevent path traversal
        if not os.path.abspath(full_path).startswith(os.path.abspath(repo_path)):
            raise ValueError(f"Invalid path: {file_path}")
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(full_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    def read_multiple_files(
        self,
        repo_path: str,
        file_paths: List[str],
        max_size: int = 100_000  # 100KB per file
    ) -> Dict[str, str]:
        """
        Read multiple files at once
        
        Args:
            repo_path: Path to repo
            file_paths: List of relative paths
            max_size: Max file size in bytes
            
        Returns:
            Dict mapping path to content
        """
        result = {}
        
        for path in file_paths:
            try:
                full_path = os.path.join(repo_path, path)
                
                # Check file size
                if os.path.getsize(full_path) > max_size:
                    logger.warning(f"Skipping large file: {path}")
                    continue
                
                result[path] = self.read_file(repo_path, path)
            except Exception as e:
                logger.warning(f"Failed to read {path}: {e}")
                continue
        
        return result
    
    def get_repo_structure(self, repo_path: str) -> Dict:
        """
        Get repository structure as tree
        
        Returns:
            Dict representing file tree
        """
        structure = {}
        
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden and system dirs
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            rel_root = os.path.relpath(root, repo_path)
            if rel_root == '.':
                rel_root = ''
            
            structure[rel_root] = {
                'dirs': sorted(dirs),
                'files': sorted(files)
            }
        
        return structure
    
    def _extract_repo_info(self, repo_url: str) -> tuple:
        """Extract owner/repo from URL"""
        parts = repo_url.rstrip('/').split('/')
        repo_name = parts[-1].replace('.git', '')
        owner = parts[-2]
        return owner, repo_name