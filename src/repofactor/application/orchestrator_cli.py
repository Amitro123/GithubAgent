import argparse
from repofactor.application.agent_service.agent_orchestrator_decision import OrchestratorState, orchestrator_decide_next


def main():
    parser = argparse.ArgumentParser(description="Orchestrator decision CLI")
    parser.add_argument("--approval_received", action="store_true", help="Approval received flag")
    parser.add_argument("--current_stage", type=str, default="init", help="Current stage of orchestrator")
    parser.add_argument("--retry_count", type=int, default=0, help="Retry count")

    args = parser.parse_args()

    state = OrchestratorState(
        approval_received=args.approval_received,
        current_stage=args.current_stage,
        retry_count=args.retry_count
    )

    next_agent = orchestrator_decide_next(state)
    print(f"Next agent to call: {next_agent}")

if __name__ == "__main__":
    main()
