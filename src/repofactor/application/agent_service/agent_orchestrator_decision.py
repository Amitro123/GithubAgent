from repofactor.domain.models.integration_models import OrchestratorState


def orchestrator_decide_next(state: OrchestratorState) -> str:
    """Decide which agent to call next"""

    if not state.approval_received:
        return "wait_for_approval"
    if state.current_stage == "init":
        return "analyzer_agent"
    
    elif state.current_stage == "analysis_complete":
        return "implementation_agent"
    
    elif state.current_stage == "implementation_failed":
        if state.retry_count < 3:
            return "research_agent"  # Try to find solutions
        else:
            return "report_failure"
    
    elif state.current_stage == "implementation_complete":
        return "diff_agent"
    
    elif state.current_stage == "diff_complete":
        return "summary_agent"
    
    elif state.current_stage == "summary_complete":
        return "testing_agent"
    
    elif state.current_stage == "testing_complete":
        return "finalize"
    
    return "error"
