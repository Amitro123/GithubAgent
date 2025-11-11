# services/lightning_ai_service.py
"""
Integration with Lightning AI using LitAI SDK
https://lightning.ai/models
"""

import os, sys, re
from dotenv import load_dotenv; load_dotenv()

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from repofactor.application.agent_service.analysis_agent import _build_analysis_prompt


# Import LitAI SDK instead of httpx
from litai import LLM

logger = logging.getLogger(__name__)

from repofactor.domain.prompts.prompt_agent_analyze import (
    PROMPT_AGENT_ANALYZE,
    PROMPT_REPO_ANALYSIS
)


class LightningModel(Enum):
    """Available models on Lightning AI"""
    GEMINI_2_5_FLASH = "google/gemini-2.5-flash-lite-preview-06-17"


@dataclass
class LightningResponse:
    """Response from Lightning AI"""
    text: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: str = "stop"
    metadata: Optional[Dict] = None


class LightningAIClient:
    """
    Client for Lightning AI inference using LitAI SDK and pydantic-ai Agent.
    Manages authentication, quota and parsing.

    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = "google/gemini-2.5-flash-lite-preview-06-17",
    ):
        self.api_key = api_key or os.getenv("LIGHTNING_API_KEY")
        
        if not self.api_key:
            raise ValueError("LIGHTNING_API_KEY not found in environment")
        
        # Set API key in environment for LitAI
        os.environ["LIGHTNING_API_KEY"] = self.api_key
        
        # Default model
        self.model_name = model or os.getenv("LLM_MODEL", "google/gemini-2.5-flash-lite-preview-06-17")
        
        # Initialize LLM with LitAI SDK
        self.llm = LLM(model=self.model_name)
        
        # Rate limiting (20 calls per month for free tier)
        self.monthly_quota = 20
        self.calls_made = 0
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.1,
        stream: bool = False
    ) -> LightningResponse:
        """
        Generate completion using Lightning AI via LitAI SDK.
        
        Args:
            prompt: Input prompt
            model: Model to use (model name or LightningModel enum)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream response (not implemented yet)
        
        Returns:
            LightningResponse with generated text
        """
        
        if self.calls_made >= self.monthly_quota:
            raise RuntimeError(
                f"Monthly quota exceeded ({self.monthly_quota} calls). "
                "Consider upgrading your Lightning AI plan."
            )
        
        # Get model name
        if model:
            if isinstance(model, LightningModel):
                use_model = model.value
            else:
                use_model = model
        else:
            use_model = self.model_name
        
        # Switch model if different
        if use_model != self.llm.model:
            self.llm = LLM(model=use_model)
        
        try:
            # Use LitAI SDK - runs in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response_text = await loop.run_in_executor(
                None,
                self.llm.chat,
                prompt
            )
            
            self.calls_made += 1
            
            return LightningResponse(
                text=response_text,
                model=use_model,
                usage={"total_tokens": len(response_text.split())},  # Approximate
                finish_reason="stop"
            )
            
        except Exception as e:
            raise RuntimeError(f"Lightning AI request failed: {str(e)}")
    
    async def generate_streaming(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.1
    ):
        """
        Stream response from Lightning AI.
        
        Note: Streaming not yet supported by LitAI SDK.
        Falls back to regular generation and yields the whole response.
        """
        
        response = await self.generate(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Simulate streaming by yielding chunks
        words = response.text.split()
        chunk_size = 5
        
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size]) + ' '
            yield chunk
            await asyncio.sleep(0.1)  # Small delay to simulate streaming
    
    def get_remaining_quota(self) -> int:
        """Get remaining API calls for the month"""
        return self.monthly_quota - self.calls_made
    
    async def close(self):
        """Cleanup - LitAI SDK handles this internally"""
        pass


class CodeAnalysisAgent:
    """
    Agent specialized for code analysis using Lightning AI models.
    Optimized for repo integration tasks.
    """
    
    def __init__(
        self,
        lightning_client: Optional[LightningAIClient] = None,
        preferred_model: LightningModel = LightningModel.GEMINI_2_5_FLASH
    ):
        self.client = lightning_client or LightningAIClient()
        self.model = preferred_model
    
    async def analyze_repository(
        self,
        repo_content: Dict[str, str],
        target_context: Optional[str] = None,
        user_instructions: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze a repository and suggest integration points.
        
        Args:
            repo_content: Dict of {filepath: content}
            target_context: Context about target project
            user_instructions: User's integration instructions
        
        Returns:
            Analysis with affected files, dependencies, etc.
        """
        
        # Build prompt for code analysis
        prompt = self._build_analysis_prompt(
            repo_content,
            target_context,
            user_instructions
        )

        logger.debug(f"Sending prompt to LLM (first 500 chars):\n{prompt[:500]}")
        
        response = await self.client.generate(
            prompt=prompt,
            model=self.model.value,
            max_tokens=2000,
            temperature=0.1
        )

        logger.debug(f"Raw LLM response:\n{response.text}")
        # Parse structured output
        analysis = self._parse_analysis(response.text)

        analysis['raw_response'] = response.text
        
        return analysis
    
    def _select_relevant_files(
        self,
        repo_content: Dict[str, str],
        limit: int = 5
    ) -> Dict[str, str]:
        """Select most relevant files for analysis"""
        
        priority_patterns = [
            'main.py', 'app.py', 'core', 'api',
            '__init__.py', 'model', 'agent'
        ]
        
        scored_files = []
        for filepath, content in repo_content.items():
            score = 0
            
            # Score based on filename patterns
            for pattern in priority_patterns:
                if pattern in filepath.lower():
                    score += 10
            
            # Score based on file size (prefer medium-sized files)
            size = len(content)
            if 500 < size < 5000:
                score += 5
            
            # Penalize test files
            if 'test' in filepath.lower():
                score -= 5
            
            scored_files.append((score, filepath, content))
        
        # Sort by score and take top files
        scored_files.sort(reverse=True, key=lambda x: x[0])
        
        return {
            filepath: content
            for _, filepath, content in scored_files[:limit]
        }
    
    def _parse_analysis(self, response_text: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured format.
        Handles various response formats robustly.
        
        Args:
            response_text: Raw text from LLM
            
        Returns:
            Dict with structured analysis
        """
        
        # Default structure if parsing fails
        default_result = {
            "main_modules": [],
            "dependencies": [],
            "affected_files": [],
            "risks": ["Failed to parse LLM response - please try again"],
            "implementation_steps": []
        }
        
        if not response_text or not response_text.strip():
            logger.error("Empty response from LLM")
            return default_result
        
        import json
        import re
        
        # Try 1: Direct JSON parse
        try:
            result = json.loads(response_text.strip())
            logger.info("✅ Successfully parsed JSON directly")
            return self._validate_and_fill_defaults(result)  # ✨ USE IT HERE
        except json.JSONDecodeError as e:
            logger.debug(f"Direct JSON parse failed: {e}")
        
        # Try 2: Extract JSON from markdown code blocks
        json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_block_pattern, response_text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
                logger.info("✅ Successfully extracted JSON from markdown block")
                return self._validate_and_fill_defaults(result)  # ✨ USE IT HERE
            except json.JSONDecodeError as e:
                logger.debug(f"Markdown block JSON parse failed: {e}")
        
        # Try 3: Find JSON object anywhere in text (more robust)
        json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
        matches = list(re.finditer(json_pattern, response_text, re.DOTALL))
        
        # Try from largest to smallest match
        matches.sort(key=lambda m: len(m.group(0)), reverse=True)
        
        for match in matches:
            try:
                result = json.loads(match.group(0))
                # Verify it has expected keys
                if any(key in result for key in ["main_modules", "dependencies", "affected_files"]):
                    logger.info("✅ Successfully extracted JSON from text")
                    return self._validate_and_fill_defaults(result)  # ✨ USE IT HERE
            except json.JSONDecodeError:
                continue
        
        # Try 4: Extract key-value pairs manually (last resort)
        logger.warning("All JSON parsing failed, attempting manual extraction")
        extracted = self._manual_extraction(response_text)
        if extracted and any(v for v in extracted.values() if v):
            logger.info("⚠️ Using manual extraction")
            return self._validate_and_fill_defaults(extracted)  # ✨ USE IT HERE
        
        # Complete failure - log the response for debugging
        logger.error(f"❌ Failed to parse LLM response. First 1000 chars:\n{response_text[:1000]}")
        return default_result  # ✨ This should also be validated

    def _validate_and_fill_defaults(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure the response has all required fields with correct types.
        
        Args:
            data: Parsed JSON data
            
        Returns:
            Validated dict with all required fields
        """
        
        result = {
            "main_modules": data.get("main_modules", []),
            "dependencies": data.get("dependencies", []),
            "affected_files": [],
            "risks": data.get("risks", []),
            "implementation_steps": data.get("implementation_steps", [])
        }
        
        # Ensure all fields are lists
        for key in ["main_modules", "dependencies", "risks", "implementation_steps"]:
            if not isinstance(result[key], list):
                logger.warning(f"Field '{key}' is not a list, converting: {type(result[key])}")
                result[key] = []
        
        # Validate affected_files structure
        raw_files = data.get("affected_files", [])
        if not isinstance(raw_files, list):
            logger.warning(f"affected_files is not a list: {type(raw_files)}")
            raw_files = []
        
        for file_info in raw_files:
            if isinstance(file_info, dict) and "path" in file_info:
                # Ensure changes is a list
                changes = file_info.get("changes", [])
                if not isinstance(changes, list):
                    changes = []
                
                result["affected_files"].append({
                    "path": str(file_info.get("path", "")),
                    "reason": str(file_info.get("reason", "")),
                    "confidence": int(file_info.get("confidence", 50)),
                    "changes": changes
                })
            else:
                logger.warning(f"Invalid file_info structure: {file_info}")
        
        logger.info(
            f"✅ Validated result: "
            f"{len(result['affected_files'])} files, "
            f"{len(result['dependencies'])} deps, "
            f"{len(result['risks'])} risks, "
            f"{len(result['implementation_steps'])} steps"
        )
        
        return result
    
    def _manual_extraction(self, text: str) -> Dict[str, Any]:
        """
        Last resort: manually extract information from free-form text.
        
        Args:
            text: Raw text response
            
        Returns:
            Best-effort extracted data
        """
        
        import re
        
        result = {
            "main_modules": [],
            "dependencies": [],
            "affected_files": [],
            "risks": [],
            "implementation_steps": []
        }
        
        # Extract dependencies (look for pip packages)
        dep_patterns = [
            r'(?:install|pip install|dependency|require|import)\s+([a-zA-Z0-9_-]+(?:>=?[0-9.]+)?)',
            r'`([a-zA-Z0-9_-]+)`.*(?:package|library|module)',
        ]
        
        for pattern in dep_patterns:
            deps = re.findall(pattern, text, re.IGNORECASE)
            result["dependencies"].extend(deps)
        
        result["dependencies"] = list(set(result["dependencies"]))  # Remove duplicates
        
        # Extract file paths
        file_patterns = [
            r'(?:file|path|modify|edit|update|change):\s*`?([a-zA-Z0-9_/.-]+\.py)`?',
            r'`([a-zA-Z0-9_/.-]+\.py)`',
        ]
        
        for pattern in file_patterns:
            files = re.findall(pattern, text, re.IGNORECASE)
            for filepath in set(files):
                if filepath not in [f["path"] for f in result["affected_files"]]:
                    result["affected_files"].append({
                        "path": filepath,
                        "reason": "Extracted from text (manual parsing)",
                        "confidence": 30,
                        "changes": []
                    })
        
        # Extract steps (lines starting with numbers)
        step_pattern = r'^\s*(\d+[\.)]\s+.+)$'
        steps = re.findall(step_pattern, text, re.MULTILINE)
        result["implementation_steps"] = steps[:10]  # Limit to 10 steps
        
        # Extract risks (lines with "risk", "warning", "caution")
        risk_pattern = r'(?:risk|warning|caution|note):\s*(.+?)(?:\n|$)'
        risks = re.findall(risk_pattern, text, re.IGNORECASE)
        result["risks"] = risks[:5]  # Limit to 5 risks
        
        logger.info(
            f"⚠️ Manual extraction found: "
            f"{len(result['dependencies'])} deps, "
            f"{len(result['affected_files'])} files, "
            f"{len(result['implementation_steps'])} steps, "
            f"{len(result['risks'])} risks"
        )
        
        return result

    
    async def generate_code_changes(
        self,
        original_code: str,
        change_instructions: str,
        context: Optional[str] = None
    ) -> str:
        """
        Generate modified code based on instructions.
        
        Args:
            original_code: Current code
            change_instructions: What to change
            context: Additional context
        
        Returns:
            Modified code
        """
        
        prompt = PROMPT_AGENT_ANALYZE(original_code, change_instructions, context)
        
        response = await self.client.generate(
            prompt=prompt,
            model=self.model.value,
            max_tokens=3000,
            temperature=0.1
        )
        
        # Extract code from response
        code = self._extract_code(response.text)
        return code
    
    def _extract_code(self, response: str) -> str:
        """Extract code block from LLM response"""
        
        import re
        
        # Try to find code between triple backticks
        code_match = re.search(r'```(?:python)?\n(.*?)\n```', response, re.DOTALL)
        
        if code_match:
            return code_match.group(1).strip()
        
        # If no code blocks, return as-is
        return response.strip()
    
    async def close(self):
        """Cleanup"""
        await self.client.close()


# ============================================================================
# Testing
# ============================================================================

async def test_litai_connection():
    """Test LitAI SDK connection"""
    
    print("="*60)
    print("🧪 Testing LitAI SDK Connection")
    print("="*60)
    
    try:
        client = LightningAIClient()
        
        print(f"✅ Client initialized")
        print(f"   Model: {client.model_name}")
        print(f"   Quota: {client.get_remaining_quota()}/20")
        
        # Test generation
        print("\n📝 Generating test response...")
        response = await client.generate(
            prompt="Say 'Hello from Lightning AI' and nothing else.",
            max_tokens=50
        )
        
        print(f"✅ Response received:")
        print(f"   {response.text[:100]}")
        print(f"   Quota remaining: {client.get_remaining_quota()}/20")
        
        await client.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_code_analysis():
    """Test code analysis agent"""
    
    print("\n" + "="*60)
    print("🧪 Testing Code Analysis Agent")
    print("="*60)
    
    try:
        agent = CodeAnalysisAgent()
        
        # Simple test code
        test_repo = {
            "main.py": """
def hello():
    print("Hello")
    
if __name__ == "__main__":
    hello()
""",
            "utils.py": """
def helper():
    return "Helper"
"""
        }
        
        print("📊 Analyzing test repository...")
        
        analysis = await agent.analyze_repository(
            repo_content=test_repo,
            user_instructions="Add logging to all functions"
        )
        
        print(f"✅ Analysis complete:")
        print(f"   Affected files: {len(analysis.get('affected_files', []))}")
        print(f"   Dependencies: {analysis.get('dependencies', [])}")
        
        await agent.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    
    print("\n🚀 Lightning AI Service Tests\n")
    
    # Test 1: Connection
    test1 = await test_litai_connection()
    
    # Test 2: Code Analysis (only if test 1 passed)
    test2 = False
    if test1:
        test2 = await test_code_analysis()
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    print(f"{'✅' if test1 else '❌'} LitAI Connection")
    print(f"{'✅' if test2 else '❌'} Code Analysis")
    
    if test1 and test2:
        print("\n✅ All tests passed! Ready to use.")
    else:
        print("\n❌ Some tests failed. Check errors above.")


if __name__ == "__main__":
    asyncio.run(main())