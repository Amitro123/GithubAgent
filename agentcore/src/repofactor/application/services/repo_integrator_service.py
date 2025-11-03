# services/repo_integrator_service.py
"""
Orchestrator for repository analysis.
זה ה-'conductor' שמנהל את כל ה-flow
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from repofactor.application.agent_service.agent import AgentCore
from repofactor.application.services.lightning_ai_service import (
    CodeAnalysisAgent,
    LightningAIClient,
    LightningModel
)
from .git_service import GitService, RepoMetadata

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Response from repo analysis"""
    repo_url: str
    repo_name: str
    affected_files: List[Dict[str, Any]]  # [{path, reason, confidence, changes}]
    dependencies: List[str]
    risks: List[str]
    estimated_time: str
    implementation_steps: List[str]
    raw_llm_response: Optional[str] = None


class RepoIntegratorService:
    """
    Main service orchestrating the analysis flow.
    
    Design pattern: דומה ל-AutoFix service שלך עם DI
    """
    
    def __init__(
        self,
        git_service: Optional[GitService] = None,
        lightning_client: Optional[LightningAIClient] = None,
        preferred_model: LightningModel = LightningModel.CODE_LLAMA_34B
    ):
        self.git_service = git_service or GitService()
        self.lightning_client = lightning_client
        self.model = preferred_model
        self.agent_core = AgentCore(".")  # Will update with repo path
    
    async def analyze_repository(
        self,
        repo_url: str,
        target_file: Optional[str] = None,
        user_instructions: str = "",
        use_cache: bool = True
    ) -> AnalysisResult:
        """
        Main entry point for analysis.
        
        Flow:
        1. Clone repo
        2. List Python files
        3. Read relevant files
        4. Send to Lightning AI for analysis
        5. Parse and return results
        """
        
        logger.info(f"Starting analysis for {repo_url}")
        
        try:
            # Step 1: Clone repository
            repo_metadata = await self.git_service.clone_repository(
                repo_url,
                use_cache=use_cache
            )
            
            # Step 2: Update agent with repo path
            self.agent_core = AgentCore(repo_metadata.local_path)
            
            # Step 3: List Python files
            py_files = self.git_service.list_python_files(
                repo_metadata.local_path
            )
            logger.info(f"Found {len(py_files)} Python files")
            
            # Step 4: Select most relevant files (limit 10 for MVP)
            relevant_files = py_files[:10]
            
            # Step 5: Read file contents
            file_contents = self.git_service.read_multiple_files(
                repo_metadata.local_path,
                relevant_files
            )
            
            # Step 6: Call Lightning AI for analysis
            analysis_agent = CodeAnalysisAgent(
                lightning_client=self.lightning_client,
                preferred_model=self.model
            )
            
            analysis_dict = await analysis_agent.analyze_repository(
                repo_content=file_contents,
                target_context=target_file,
                user_instructions=user_instructions
            )
            
            # Step 7: Format results
            result = AnalysisResult(
                repo_url=repo_url,
                repo_name=repo_metadata.name,
                affected_files=analysis_dict.get("affected_files", []),
                dependencies=analysis_dict.get("dependencies", []),
                risks=analysis_dict.get("risks", []),
                estimated_time="10 minutes",  # MVP hardcoded
                implementation_steps=analysis_dict.get("implementation_steps", []),
                raw_llm_response=analysis_dict.get("raw_response")
            )
            
            logger.info(f"Analysis complete: {len(result.affected_files)} files to modify")
            
            return result
        
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
    
    async def close(self):
        """Cleanup resources"""
        if self.lightning_client:
            await self.lightning_client.close()


# MVP Test function
async def test_integration():
    """Simple test to verify flow"""
    
    service = RepoIntegratorService()
    
    result = await service.analyze_repository(
        repo_url="https://github.com/pydantic/pydantic",
        user_instructions="Add async support to validators"
    )
    
    print(f"✅ Analysis complete")
    print(f"Affected files: {len(result.affected_files)}")
    print(f"Dependencies: {result.dependencies}")
    print(f"Risks: {result.risks}")
    
    await service.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_integration())
