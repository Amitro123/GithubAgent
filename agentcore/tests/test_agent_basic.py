# agentcore/tests/test_agent_basic.py
"""
Basic MVP tests with mocks
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Imports (path setup handled by conftest.py)
from src.repofactor.application.services.git_service import GitService
from src.repofactor.application.services.repo_integrator_service import (
    RepoIntegratorService,
    AnalysisResult
)
from src.repofactor.application.agent_service.agent import AgentCore


class TestGitService:
    """Test Git operations without actual cloning for MVP"""
    
    def test_extract_repo_info(self):
        """Test: URL parsing"""
        service = GitService()
        
        owner, repo = service._extract_repo_info(
            "https://github.com/pallets/flask"
        )
        
        assert owner == "pallets"
        assert repo == "flask"
    
    def test_extract_repo_info_with_git_suffix(self):
        """Test: URL parsing with .git"""
        service = GitService()
        
        owner, repo = service._extract_repo_info(
            "https://github.com/pallets/flask.git"
        )
        
        assert owner == "pallets"
        assert repo == "flask"
    
    def test_list_python_files_mock(self):
        """Test: List Python files from a temp directory"""
        service = GitService()
        
        # Create temp repo structure
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some Python files
            Path(tmpdir, "main.py").touch()
            Path(tmpdir, "utils.py").touch()
            Path(tmpdir, "src").mkdir()
            Path(tmpdir, "src", "core.py").touch()
            
            # Create non-Python files (should be ignored)
            Path(tmpdir, "README.md").touch()
            
            files = service.list_python_files(tmpdir)
            
            assert len(files) == 3
            assert "main.py" in files
            assert "utils.py" in files
            assert "src/core.py" in files or "src\\core.py" in files
            assert "README.md" not in files


class TestAgentCore:
    """Test the basic agent functionality"""
    
    def test_agent_initialization(self):
        """Test: Agent initializes with repo path"""
        agent = AgentCore(repo_path=".")
        
        assert agent.repo_path == "."
    
    def test_list_py_files_basic(self):
        """Test: List Python files in current directory"""
        agent = AgentCore(repo_path=".")
        
        # Should at least find this test file and others
        files = agent.list_py_files()
        
        assert isinstance(files, list)
        # Files should end with .py
        assert all(f.endswith(".py") for f in files)


class TestRepoIntegratorService:
    """Integration tests with mocks"""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test: Service initializes correctly"""
        service = RepoIntegratorService()
        
        assert service.git_service is not None
        assert service.agent_core is not None
    
    @pytest.mark.skip(reason="Complex integration test - needs full mock setup")
    @pytest.mark.asyncio
    async def test_analyze_repository_with_mock(self):
        """Test: Analysis flow with mocked Lightning AI"""
        
        # Mock the Lightning AI response (must be AsyncMock for async methods)
        with patch(
            'src.repofactor.application.services.lightning_ai_service.CodeAnalysisAgent.analyze_repository',
            new_callable=AsyncMock
        ) as mock_analyze:
            # Setup mock response
            mock_analyze.return_value = {
                "main_modules": ["core", "utils"],
                "dependencies": ["numpy", "pandas"],
                "affected_files": [
                    {
                        "path": "src/main.py",
                        "reason": "Main entry point",
                        "confidence": 95,
                        "changes": ["Add async support"]
                    }
                ],
                "risks": ["Check compatibility"],
                "implementation_steps": ["Step 1", "Step 2"],
                "raw_response": None
            }
            
            service = RepoIntegratorService()
            
            # Mock git clone to avoid actual cloning
            with patch.object(
                service.git_service,
                'clone_repository'
            ) as mock_clone:
                mock_clone.return_value = Mock(
                    local_path="/tmp/fake_repo",
                    repo_url="https://github.com/test/repo",
                    owner="test",
                    name="repo"
                )
                
                # Mock list_python_files
                with patch.object(
                    service.git_service,
                    'list_python_files',
                    return_value=["main.py", "utils.py"]
                ):
                    # Mock read_multiple_files
                    with patch.object(
                        service.git_service,
                        'read_multiple_files',
                        return_value={
                            "main.py": "# Sample code",
                            "utils.py": "# Utils code"
                        }
                    ):
                        result = await service.analyze_repository(
                            repo_url="https://github.com/test/repo",
                            user_instructions="Add async support"
                        )
            
            # Verify result
            assert result.repo_name == "repo"
            assert len(result.affected_files) > 0
            assert result.dependencies == ["numpy", "pandas"]


# ============ Test fixtures ============

@pytest.fixture
def temp_repo_path():
    """Create a temporary repo structure for testing"""
    tmpdir = tempfile.mkdtemp()
    
    # Create some sample files
    Path(tmpdir, "main.py").write_text("def main():\n    pass")
    Path(tmpdir, "utils.py").write_text("def helper():\n    pass")
    
    yield tmpdir
    
    # Cleanup
    shutil.rmtree(tmpdir)


@pytest.fixture
def git_service(temp_repo_path):
    """Provide GitService with temp repo"""
    return GitService(cache_dir=os.path.join(temp_repo_path, "cache"))


# ============ Main test runner ============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
