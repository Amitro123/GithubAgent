# src/repofactor/application/agent_service/multi_agent_orchestrator.py

from repofactor.application.agent_service.analysis_agent import CodeAnalysisAgent
from repofactor.application.agent_service.implementation_agent import ImplementationAgent
from repofactor.application.agent_service.diff_agent import DiffAgent
from repofactor.application.services.lightning_ai_service import (
    LightningAIClient,
    LightningModel
)


class MultiAgentOrchestrator:
    def __init__(self):
        self.analysis_agent = CodeAnalysisAgent()
        self.diff_agent = DiffAgent()
        self.implementation_agent = ImplementationAgent(LightningAIClient())
        # self.validator_agent = ValidatorAgent()
        # self.doc_agent = DocAgent()

    async def run_full_flow(self, repo_content_old, instructions):
        analysis = await self.analysis_agent.analyze_repository(
            repo_content=repo_content_old,
            user_instructions=instructions
        )

        implementation_result = self.implementation_agent.implement_changes(
            repo_content=repo_content_old,
            instructions=instructions
        )

        # Convert ImplementationResult to a dictionary of file contents
        repo_content_new = {
            file.path: file.modified_content
            for file in implementation_result.modified_files
        }

        diff_result = self.diff_agent.generate_diff(
            base_files=repo_content_old,
            modified_files=repo_content_new
        )

        # 3. שלבים נוספים אם יש

        results = {
            "analysis": analysis,
            "diff": diff_result,
            "implementation": implementation_result,
            # "validation": validation,
            # "documentation": doc,
        }
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
