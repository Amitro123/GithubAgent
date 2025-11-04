# services/repo_integrator_service.py
"""
Orchestrator for repository analysis.
This is the 'conductor' that manages the entire flow
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
from repofactor.application.services.repo_service import RepoService

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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class RepoIntegratorService:
    """
    Main orchestration service for repository integration.
    
    This is what the UI/API should call.
    
    Flow:
    1. Search/validate repo (via RepoService)
    2. Clone repo (via RepoService) 
    3. List and read files (via RepoService)
    4. Analyze with Lightning AI (via CodeAnalysisAgent)
    5. Return structured results
    
    Example:
        >>> service = RepoIntegratorService()
        >>> result = await service.analyze_repository(
        ...     repo_url="https://github.com/user/repo",
        ...     user_instructions="Add async support"
        ... )
        >>> print(f"Files to modify: {len(result.affected_files)}")
    """
    
    def __init__(
        self,
        repo_service: Optional[RepoService] = None,
        lightning_client: Optional[LightningAIClient] = None,
        preferred_model: LightningModel = LightningModel.CODE_LLAMA_34B
    ):
        # Services
        self.repo_service = repo_service or RepoService()
        self.lightning_client = lightning_client
        self.model = preferred_model
        
        # Agent core (will be updated with repo path)
        self.agent_core = AgentCore(".")
    
    async def analyze_repository(
        self,
        repo_url: str,
        target_file: Optional[str] = None,
        user_instructions: str = "",
        use_cache: bool = True,
        max_files: int = 10
    ) -> AnalysisResult:
        """
        Main entry point for repository analysis.
        
        Args:
            repo_url: GitHub repository URL
            target_file: Specific file to modify (optional)
            user_instructions: User's integration instructions
            use_cache: Whether to use cached clone
            max_files: Maximum number of files to analyze
        
        Returns:
            AnalysisResult with all findings
            
        Raises:
            ValueError: If repo_url is invalid
            RuntimeError: If analysis fails
        """
        
        logger.info(f"Starting analysis for {repo_url}")
        
        try:
            # Step 1: Validate URL format
            if not self.repo_service.api.is_valid_github_url(repo_url):
                raise ValueError(f"Invalid GitHub URL: {repo_url}")
            
            # Step 2: Clone repository
            logger.info("Cloning repository...")
            repo_metadata = await self.repo_service.git.clone_repository(
                repo_url,
                use_cache=use_cache
            )
            logger.info(f"Cloned to: {repo_metadata.local_path}")
            
            # Step 3: Update agent with repo path
            self.agent_core = AgentCore(repo_metadata.local_path)
            
            # Step 4: List Python files
            logger.info("Listing Python files...")
            py_files = self.repo_service.git.list_python_files(
                repo_metadata.local_path
            )
            logger.info(f"Found {len(py_files)} Python files")
            
            if not py_files:
                logger.warning("No Python files found in repository")
                return AnalysisResult(
                    repo_url=repo_url,
                    repo_name=repo_metadata.name,
                    affected_files=[],
                    dependencies=[],
                    risks=["No Python files found"],
                    estimated_time="N/A",
                    implementation_steps=[]
                )
            
            # Step 5: Select most relevant files
            # TODO: Smart file selection based on target_file and instructions
            relevant_files = self._select_relevant_files(
                py_files, 
                target_file, 
                max_files
            )
            logger.info(f"Selected {len(relevant_files)} files for analysis")
            
            # Step 6: Read file contents
            logger.info("Reading file contents...")
            file_contents = self.repo_service.git.read_multiple_files(
                repo_metadata.local_path,
                relevant_files
            )
            logger.info(f"Read {len(file_contents)} files successfully")
            
            # Step 7: Analyze with Lightning AI
            logger.info("Analyzing with Lightning AI...")
            analysis_agent = CodeAnalysisAgent(
                lightning_client=self.lightning_client,
                preferred_model=self.model
            )
            
            analysis_dict = await analysis_agent.analyze_repository(
                repo_content=file_contents,
                target_context=target_file,
                user_instructions=user_instructions
            )
            
            # Step 8: Format and return results
            result = AnalysisResult(
                repo_url=repo_url,
                repo_name=repo_metadata.name,
                affected_files=analysis_dict.get("affected_files", []),
                dependencies=analysis_dict.get("dependencies", []),
                risks=analysis_dict.get("risks", []),
                estimated_time=self._estimate_time(analysis_dict),
                implementation_steps=analysis_dict.get("implementation_steps", []),
                raw_llm_response=analysis_dict.get("raw_response")
            )
            
            logger.info(
                f"Analysis complete: {len(result.affected_files)} files to modify, "
                f"{len(result.dependencies)} dependencies"
            )
            
            return result
        
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise RuntimeError(f"Repository analysis failed: {str(e)}")
    
    def _select_relevant_files(
        self,
        all_files: List[str],
        target_file: Optional[str],
        max_files: int
    ) -> List[str]:
        """
        Select most relevant files for analysis.
        
        Strategy:
        1. If target_file specified, prioritize it
        2. Prioritize files in src/, core/, main directories
        3. Avoid test files (for now)
        4. Limit to max_files
        """
        selected = []
        
        # Priority 1: Target file
        if target_file and target_file in all_files:
            selected.append(target_file)
        
        # Priority 2: Main/core files
        priority_patterns = ['main.py', 'app.py', 'core/', 'src/']
        for pattern in priority_patterns:
            for file in all_files:
                if pattern in file and file not in selected:
                    selected.append(file)
                    if len(selected) >= max_files:
                        return selected
        
        # Priority 3: Other files (excluding tests)
        for file in all_files:
            if 'test' not in file.lower() and file not in selected:
                selected.append(file)
                if len(selected) >= max_files:
                    return selected
        
        return selected[:max_files]
    
    def _estimate_time(self, analysis: Dict) -> str:
        """
        Estimate integration time based on analysis.
        
        Simple heuristic for MVP:
        - 1 file = 5 minutes
        - Each dependency = +2 minutes
        """
        num_files = len(analysis.get("affected_files", []))
        num_deps = len(analysis.get("dependencies", []))
        
        minutes = (num_files * 5) + (num_deps * 2)
        
        if minutes < 10:
            return "5-10 minutes"
        elif minutes < 30:
            return "10-30 minutes"
        elif minutes < 60:
            return "30-60 minutes"
        else:
            return "1+ hours"
    
    async def validate_repository(self, repo_url: str) -> bool:
        """
        Quick validation that repository exists and is accessible.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            True if valid and accessible
        """
        try:
            if not self.repo_service.api.is_valid_github_url(repo_url):
                return False
            
            owner, repo = self.repo_service.api.parse_repo_url(repo_url)
            return await self.repo_service.api.validate_repository(owner, repo)
        
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False
    
    async def get_repository_info(self, repo_url: str) -> Optional[Dict]:
        """
        Get repository metadata without cloning.
        
        Useful for displaying info before analysis.
        """
        try:
            owner, repo = self.repo_service.api.parse_repo_url(repo_url)
            return await self.repo_service.api.get_repository_info(owner, repo)
        except Exception as e:
            logger.error(f"Failed to get repo info: {e}")
            return None
    
    async def close(self):
        """Cleanup resources"""
        if self.lightning_client:
            await self.lightning_client.close()


# ============================================================================
# Testing & Examples
# ============================================================================

async def test_integration():
    """
    Simple test to verify the entire flow.
    
    Run with: python -m repofactor.application.services.repo_integrator_service
    """
    
    print("🧪 Testing RepoIntegratorService...")
    
    service = RepoIntegratorService()
    
    try:
        # Test with a small, well-known repo
        result = await service.analyze_repository(
            repo_url="https://github.com/pydantic/pydantic",
            user_instructions="Add async support to validators",
            max_files=5  # Limit for testing
        )
        
        print("\n✅ Analysis complete!")
        print(f"📦 Repository: {result.repo_name}")
        print(f"📝 Files to modify: {len(result.affected_files)}")
        print(f"📦 Dependencies: {', '.join(result.dependencies) or 'None'}")
        print(f"⚠️  Risks: {len(result.risks)}")
        print(f"⏱️  Estimated time: {result.estimated_time}")
        
        if result.affected_files:
            print("\n📋 Affected files:")
            for file_info in result.affected_files[:3]:  # Show first 3
                print(f"  • {file_info.get('path', 'unknown')}")
                print(f"    Reason: {file_info.get('reason', 'N/A')}")
                print(f"    Confidence: {file_info.get('confidence', 0)}%")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
    
    finally:
        await service.close()


async def quick_validate_test():
    """Quick validation test"""
    
    service = RepoIntegratorService()
    
    test_urls = [
        "https://github.com/microsoft/LLMLingua",
        "https://github.com/invalid/nonexistent",
        "not-a-url"
    ]
    
    for url in test_urls:
        is_valid = await service.validate_repository(url)
        print(f"{'✅' if is_valid else '❌'} {url}")


if __name__ == "__main__":
    import asyncio
    
    # Run tests
    print("Running integration test...\n")
    asyncio.run(test_integration())
    
    print("\n" + "="*50 + "\n")
    print("Running validation test...\n")
    asyncio.run(quick_validate_test())