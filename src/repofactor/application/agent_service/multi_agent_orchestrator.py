from repofactor.application.agent_service.analysis_agent import CodeAnalysisAgent
from repofactor.application.agent_service.agent_orchestrator_decision import orchestrator_decide_next
from repofactor.domain.models.integration_models import OrchestratorState
from repofactor.application.agent_service.implementation_agent import ImplementationAgent
from repofactor.application.agent_service.diff_agent import DiffAgent
from repofactor.application.agent_service.research_agent import ResearchAgent
from repofactor.application.services.lightning_ai_service import LightningAIClient


MAX_RETRIES = 3

class MultiAgentOrchestrator:
    def __init__(self):
        self.analysis_agent = CodeAnalysisAgent()
        self.diff_agent = DiffAgent()
        self.implementation_agent = ImplementationAgent(LightningAIClient())
        self.research_agent = ResearchAgent()
        self.state = OrchestratorState()

        self.repo_content = None
        self.instructions = None
        self.latest_implementation_result = None

        # self.validator_agent = ValidatorAgent()
        # self.doc_agent = DocAgent()

    def get_next_agent_name(self):
        return orchestrator_decide_next(self.state)

    async def run_next_agent(self):
        agent_name = self.get_next_agent_name()

        if agent_name == "wait_for_approval":
            print("Waiting for approval...")
            return None

        elif agent_name == "analyzer_agent":
            print("Running Analysis Agent...")
            result = await self.analysis_agent.analyze_repository(
                repo_content=self.repo_content,
                user_instructions=self.instructions
            )
            self.state.current_stage = "analysis_complete"
            return result

        elif agent_name == "implementation_agent":
            print("Running Implementation Agent...")
            result = await self.implementation_agent.implement_changes(
                repo_content=self.repo_content,
                instructions=self.instructions
            )
            self.latest_implementation_result = result
            if result.success:
                self.state.current_stage = "implementation_complete"
            else:
                self.state.current_stage = "implementation_failed"
                self.state.last_error_message = getattr(result, "error_message", "Unknown error")
            return result

        elif agent_name == "research_agent":
            print(f"Running Research Agent for error: {self.state.last_error_message}")
            context = {
                "repo": "local_project",
                "user_instructions": self.instructions or "",
                "studio_logs": getattr(self.latest_implementation_result, "execution_logs", []),
            }
            best_snippet, research_result = await self.research_agent.best_fix_snippet(
                error_message=self.state.last_error_message or "",
                failed_code="",
                context=context,
            )
            if best_snippet:
                self.instructions = (self.instructions or "") + (
                    "\n\n# Suggested fix from research:\n" + best_snippet
                )
            self.state.current_stage = "implementation_retry"
            return research_result

        elif agent_name == "implementation_retry":
            if self.state.retry_count >= MAX_RETRIES:
                print("Exceeded maximum retries, reporting failure.")
                self.state.current_stage = "report_failure"
                return None
            self.state.retry_count += 1
            print(f"Retrying implementation attempt #{self.state.retry_count}...")
            result = await self.implementation_agent.implement_changes(
                repo_content=self.repo_content,
                instructions=self.instructions
            )
            self.latest_implementation_result = result
            if result.success:
                self.state.current_stage = "implementation_complete"
            else:
                self.state.current_stage = "implementation_failed"
                self.state.last_error_message = getattr(result, "error_message", "Unknown error")
            return result

        elif agent_name == "diff_agent":
            modified_files = {
                file.path: file.modified_content for file in self.latest_implementation_result.modified_files
            }
            print("Running Diff Agent...")
            result = await self.diff_agent.generate_diff(
                base_files=self.repo_content,
                modified_files=modified_files
            )
            self.state.current_stage = "diff_complete"
            return result

        else:
            raise Exception(f"Unknown agent name: {agent_name}")

    async def run_full_flow(self, repo_content_old, instructions):
        self.repo_content = repo_content_old
        self.instructions = instructions

        results = {}
        while True:
            next_agent = self.get_next_agent_name()
            if next_agent in ("finalize", "error", "report_failure"):
                print(f"Stopping flow at stage: {next_agent}")
                break
            res = await self.run_next_agent()
            results[next_agent] = res

        return results


import asyncio


async def example_run():
    orchestrator = MultiAgentOrchestrator()
    old_repo = {"main.py": "print('Hello')"}
    instructions = "Modernize code output"
    results = await orchestrator.run_full_flow(old_repo, instructions)
    print(results)


if __name__ == "__main__":
    asyncio.run(example_run())
