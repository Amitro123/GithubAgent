import pytest
from repofactor.application.agent_service.agent_orchestrator_decision import OrchestratorState, orchestrator_decide_next

@pytest.mark.parametrize("state,expected_agent", [
    (OrchestratorState(approval_received=False, current_stage="init", retry_count=0), "wait_for_approval"),
    (OrchestratorState(approval_received=True, current_stage="init", retry_count=0), "analyzer_agent"),
    (OrchestratorState(approval_received=True, current_stage="analysis_complete", retry_count=0), "implementation_agent"),
    (OrchestratorState(approval_received=True, current_stage="implementation_failed", retry_count=2), "research_agent"),
    (OrchestratorState(approval_received=True, current_stage="implementation_failed", retry_count=3), "report_failure"),
    (OrchestratorState(approval_received=True, current_stage="implementation_complete", retry_count=0), "diff_agent"),
    (OrchestratorState(approval_received=True, current_stage="diff_complete", retry_count=0), "summary_agent"),
    (OrchestratorState(approval_received=True, current_stage="summary_complete", retry_count=0), "testing_agent"),
    (OrchestratorState(approval_received=True, current_stage="testing_complete", retry_count=0), "finalize"),
    (OrchestratorState(approval_received=True, current_stage="unknown", retry_count=0), "error"),
])
def test_orchestrator_decide_next(state, expected_agent):
    result = orchestrator_decide_next(state)
    assert result == expected_agent
