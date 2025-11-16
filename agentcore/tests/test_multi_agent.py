import pytest
from unittest.mock import AsyncMock, patch
from repofactor.application.services.repo_integrator_service import RepoIntegratorService
from repofactor.domain.models.integration_models import AnalysisResult

@pytest.mark.asyncio
@patch("repofactor.application.agent_service.multi_agent_orchestrator.MultiAgentOrchestrator.run_full_flow")
@patch("repofactor.application.agent_service.analysis_agent.LightningAIClient")
@patch("repofactor.application.services.repo_integrator_service.AgentCore")
@patch("repofactor.application.services.repo_integrator_service.RepoService")
async def test_analyze_repository_with_orchestrator(
        mock_repo_service,
        mock_agent_core,
        mock_lightning_client,  # Mock LightningAIClient calls
        mock_run_full_flow):
    service = RepoIntegratorService()
    service.repo_service = mock_repo_service
    service.agent_core = mock_agent_core

    # Mock git and API validations
    mock_repo_service.api.is_valid_github_url.return_value = True
    mock_repo_service.git.clone_repository = AsyncMock(
        return_value=type("Meta", (), {"local_path": "/tmp/repo", "name": "repo"})
    )
    mock_repo_service.git.list_python_files.return_value = ["file1.py", "file2.py"]
    mock_repo_service.git.read_multiple_files.return_value = {
        "file1.py": "print('hello')",
        "file2.py": "print('world')"
    }

    # Mock orchestrator full flow response
    mock_run_full_flow.return_value = {
        "analysis": {
            "file_count": 2,
            "affected_files": [
                {"path": "file1.py", "reason": "test change", "confidence": 90, "changes": []},
                {"path": "file2.py", "reason": "another change", "confidence": 95, "changes": []}
            ],
            "dependencies": [],
            "risks": [],
            "estimated_time": "1min",
            "implementation_steps": []
        },
        "diff": {}
    }

    result = await service.analyze_repository("https://github.com/test/repo")
    assert isinstance(result, AnalysisResult)
    assert result.repo_url == "https://github.com/test/repo"
    assert result.repo_name == "repo"
    assert result.file_count == 2
