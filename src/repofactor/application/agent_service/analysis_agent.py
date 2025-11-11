# application/agents/analysis_agent.py
"""
Code Analysis Agent - handles all analysis logic using Pydantic AI
"""

import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel

from repofactor.domain.prompts.prompt_agent_analyze import PROMPT_REPO_ANALYSIS
from repofactor.application.services.lightning_ai_service import LightningAIClient

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================

class AffectedFileSchema(BaseModel):
    """Schema for a single affected file"""
    path: str = Field(description="Relative file path in target project")
    reason: str = Field(description="Why this file needs changes")
    confidence: int = Field(ge=0, le=100, description="Confidence score 0-100")
    changes: List[str] = Field(description="List of specific changes needed")


class RepositoryAnalysisSchema(BaseModel):
    """Complete repository analysis output - enforces structure"""
    main_modules: List[str] = Field(
        default_factory=list,
        description="Key modules from source repository"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Required pip packages (e.g., 'fastapi>=0.100.0')"
    )
    affected_files: List[AffectedFileSchema] = Field(
        default_factory=list,
        description="Files that need modification"
    )
    risks: List[str] = Field(
        default_factory=list,
        description="Potential issues or warnings"
    )
    implementation_steps: List[str] = Field(
        default_factory=list,
        description="Ordered implementation steps"
    )


# ============================================================================
# Analysis Agent
# ============================================================================

class CodeAnalysisAgent:
    """
    Agent for analyzing repositories and suggesting integration changes.
    Uses Pydantic AI for structured outputs.
    """
    
    def __init__(
        self,
        lightning_client: Optional[LightningAIClient] = None,
        model: str = "google/gemini-2.5-flash-lite-preview-06-17"
    ):
        self.client = lightning_client or LightningAIClient()
        self.model = model
        
        # Create Pydantic AI agent with structured output
        self.agent = Agent(
            model=self._create_model_adapter(),
            result_type=RepositoryAnalysisSchema,
            system_prompt=self._get_system_prompt()
        )
    
    def _create_model_adapter(self):
        """
        Create a model adapter for Pydantic AI.
        Since Lightning AI uses custom SDK, we'll use a wrapper.
        """
        # For now, use OpenAI as fallback
        # TODO: Create custom LightningAI adapter for pydantic-ai
        return OpenAIModel('gpt-4o-mini')  # or use Lightning via custom adapter
    
    def _get_system_prompt(self) -> str:
        """System prompt for the agent"""
        return """You are an expert code integration assistant.

Your task is to analyze source code repositories and provide detailed integration recommendations.

Key responsibilities:
- Identify main modules and their purposes
- List all required dependencies with versions
- Determine which files in the target project need modifications
- Highlight potential risks and compatibility issues
- Provide clear, actionable implementation steps

Always be specific and practical. Focus on real integration challenges."""
    
    async def analyze_repository(
        self,
        repo_content: Dict[str, str],
        target_context: Optional[str] = None,
        user_instructions: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze repository and return structured results.
        
        Args:
            repo_content: Dict of {filepath: content}
            target_context: Context about target project
            user_instructions: User's integration instructions
        
        Returns:
            Dict with structured analysis (matches RepositoryAnalysisSchema)
        """
        
        # Build prompt
        prompt = self._build_analysis_prompt(
            repo_content,
            target_context,
            user_instructions
        )
        
        logger.debug(f"Prompt length: {len(prompt)} chars")
        logger.debug(f"First 500 chars:\n{prompt[:500]}")
        
        try:
            # Option 1: Use Pydantic AI (recommended for structured output)
            result = await self._analyze_with_pydantic_ai(prompt)
            
        except Exception as e:
            logger.warning(f"Pydantic AI failed, falling back to manual parsing: {e}")
            # Option 2: Fallback to direct LLM call + manual parsing
            result = await self._analyze_with_fallback(prompt)
        
        logger.info(
            f"✅ Analysis complete: "
            f"{len(result.get('affected_files', []))} files, "
            f"{len(result.get('dependencies', []))} deps"
        )
        
        return result
    
    async def _analyze_with_pydantic_ai(self, prompt: str) -> Dict[str, Any]:
        """Use Pydantic AI for guaranteed structured output"""
        
        # Run agent
        result = await self.agent.run(prompt)
        
        # Convert Pydantic model to dict
        analysis = result.data.model_dump()
        
        logger.info("✅ Pydantic AI returned structured output")
        
        return analysis
    
    async def _analyze_with_fallback(self, prompt: str) -> Dict[str, Any]:
        """Fallback: Direct LLM call + robust parsing"""
        
        # Call Lightning AI directly
        response = await self.client.generate(
            prompt=prompt,
            model=self.model,
            max_tokens=2000,
            temperature=0.1
        )
        
        logger.debug(f"Raw LLM response:\n{response.text[:500]}")
        
        # Parse with robust logic
        parsed = self._parse_llm_response(response.text)
        
        # Validate with Pydantic
        validated = RepositoryAnalysisSchema(**parsed)
        
        return validated.model_dump()
    
    def _build_analysis_prompt(
        self,
        repo_content: Dict[str, str],
        target_context: Optional[str],
        instructions: str
    ) -> str:
        """Build the analysis prompt"""
        
        # Select most relevant files (limit to avoid token limits)
        relevant_files = self._select_relevant_files(repo_content, limit=5)
        
        # Use centralized prompt builder
        return PROMPT_REPO_ANALYSIS(instructions, relevant_files, target_context)
    
    def _select_relevant_files(
        self,
        repo_content: Dict[str, str],
        limit: int = 5
    ) -> Dict[str, str]:
        """Select most relevant files for analysis"""
        
        priority_patterns = [
            'main.py', 'app.py', '__init__.py',
            'core', 'api', 'model', 'agent'
        ]
        
        scored_files = []
        for filepath, content in repo_content.items():
            score = 0
            
            # Score by filename patterns
            for pattern in priority_patterns:
                if pattern in filepath.lower():
                    score += 10
            
            # Score by file size (prefer medium-sized)
            size = len(content)
            if 500 < size < 5000:
                score += 5
            elif size > 10000:
                score -= 3  # Too large
            
            # Penalize test files
            if 'test' in filepath.lower():
                score -= 10
            
            scored_files.append((score, filepath, content))
        
        # Sort and select top files
        scored_files.sort(reverse=True, key=lambda x: x[0])
        
        return {
            filepath: content
            for _, filepath, content in scored_files[:limit]
        }
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Robust parsing of LLM response.
        Tries multiple strategies to extract structured data.
        """
        
        import json
        import re
        
        # Default structure
        default = {
            "main_modules": [],
            "dependencies": [],
            "affected_files": [],
            "risks": ["Failed to parse LLM response"],
            "implementation_steps": []
        }
        
        if not response_text or not response_text.strip():
            logger.error("Empty LLM response")
            return default
        
        # Strategy 1: Direct JSON parse
        try:
            result = json.loads(response_text.strip())
            logger.info("✅ Parsed JSON directly")
            return self._fill_defaults(result)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract from markdown code block
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
                logger.info("✅ Extracted JSON from markdown")
                return self._fill_defaults(result)
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Find JSON anywhere in text
        matches = list(re.finditer(
            r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}',
            response_text,
            re.DOTALL
        ))
        
        # Try largest matches first
        matches.sort(key=lambda m: len(m.group(0)), reverse=True)
        
        for match in matches:
            try:
                result = json.loads(match.group(0))
                if any(k in result for k in ["affected_files", "dependencies"]):
                    logger.info("✅ Extracted JSON from text")
                    return self._fill_defaults(result)
            except json.JSONDecodeError:
                continue
        
        # Strategy 4: Manual extraction (last resort)
        logger.warning("⚠️ Using manual extraction")
        extracted = self._manual_extraction(response_text)
        return self._fill_defaults(extracted)
    
    def _fill_defaults(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required fields exist"""
        
        result = {
            "main_modules": data.get("main_modules", []),
            "dependencies": data.get("dependencies", []),
            "affected_files": [],
            "risks": data.get("risks", []),
            "implementation_steps": data.get("implementation_steps", [])
        }
        
        # Ensure lists
        for key in ["main_modules", "dependencies", "risks", "implementation_steps"]:
            if not isinstance(result[key], list):
                result[key] = []
        
        # Validate affected_files
        raw_files = data.get("affected_files", [])
        if isinstance(raw_files, list):
            for file_info in raw_files:
                if isinstance(file_info, dict) and "path" in file_info:
                    result["affected_files"].append({
                        "path": str(file_info.get("path", "")),
                        "reason": str(file_info.get("reason", "")),
                        "confidence": int(file_info.get("confidence", 50)),
                        "changes": file_info.get("changes", [])
                    })
        
        return result
    
    def _manual_extraction(self, text: str) -> Dict[str, Any]:
        """Extract data from free-form text (last resort)"""
        
        import re
        
        result = {
            "main_modules": [],
            "dependencies": [],
            "affected_files": [],
            "risks": [],
            "implementation_steps": []
        }
        
        # Extract dependencies
        deps = re.findall(
            r'(?:install|pip|require)\s+([a-zA-Z0-9_-]+(?:>=?[0-9.]+)?)',
            text,
            re.IGNORECASE
        )
        result["dependencies"] = list(set(deps))
        
        # Extract file paths
        files = re.findall(r'([a-zA-Z0-9_/.-]+\.py)', text)
        for filepath in set(files):
            result["affected_files"].append({
                "path": filepath,
                "reason": "Extracted from text",
                "confidence": 30,
                "changes": []
            })
        
        # Extract numbered steps
        steps = re.findall(r'^\s*\d+[\.)]\s+(.+)$', text, re.MULTILINE)
        result["implementation_steps"] = steps[:10]
        
        logger.info(
            f"Manual extraction: {len(result['dependencies'])} deps, "
            f"{len(result['affected_files'])} files"
        )
        
        return result
    
    async def close(self):
        """Cleanup"""
        await self.client.close()


# ============================================================================
# Testing
# ============================================================================

async def test_analysis_agent():
    """Test the analysis agent"""
    
    print("🧪 Testing CodeAnalysisAgent with Pydantic AI...\n")
    
    agent = CodeAnalysisAgent()
    
    test_repo = {
        "main.py": """
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
""",
        "models.py": """
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
"""
    }
    
    try:
        result = await agent.analyze_repository(
            repo_content=test_repo,
            user_instructions="Add logging to all endpoints"
        )
        
        print("✅ Analysis complete!\n")
        print(f"Main modules: {result['main_modules']}")
        print(f"Dependencies: {result['dependencies']}")
        print(f"Affected files: {len(result['affected_files'])}")
        print(f"Risks: {result['risks']}")
        print(f"Steps: {len(result['implementation_steps'])}")
        
        if result['affected_files']:
            print("\n📋 Files to modify:")
            for file in result['affected_files']:
                print(f"  • {file['path']} (confidence: {file['confidence']}%)")
                print(f"    Reason: {file['reason']}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await agent.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_analysis_agent())