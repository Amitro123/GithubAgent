# services/lightning_ai_service.py
"""
Integration with Lightning AI for running LLM inference
https://lightning.ai/models
"""

import os
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from repofactor.domain.prompts.prompt_agent_analyze import PROMPT_AGENT_ANALYZE, PROMPT_REPO_ANALYSIS

class LightningModel(Enum):
    """Available models on Lightning AI"""
    # Code-focused models
    CODE_LLAMA_34B = "codellama/CodeLlama-34b-Instruct-hf"
    DEEPSEEK_CODER_33B = "deepseek-ai/deepseek-coder-33b-instruct"
    STARCODER2_15B = "bigcode/starcoder2-15b"
    
    # General LLMs
    LLAMA_3_70B = "meta-llama/Meta-Llama-3-70B-Instruct"
    MIXTRAL_8X7B = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    QWEN_72B = "Qwen/Qwen2-72B-Instruct"
    
    # Specialized
    PHIND_CODE_LLAMA = "Phind/Phind-CodeLlama-34B-v2"

@dataclass
class LightningRequest:
    """Request to Lightning AI Studio"""
    prompt: str
    model: str
    max_tokens: int = 2000
    temperature: float = 0.1
    top_p: float = 0.95
    stream: bool = False
    
@dataclass
class LightningResponse:
    """Response from Lightning AI"""
    text: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    metadata: Optional[Dict] = None


class LightningAIClient:
    """
    Client for Lightning AI inference.
    Handles authentication, rate limiting, and retries.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        studio_url: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("LIGHTNING_API_KEY")
        self.studio_url = studio_url or os.getenv("LIGHTNING_STUDIO_URL")
        
        if not self.api_key:
            raise ValueError("LIGHTNING_API_KEY not found in environment")
        
        self.client = httpx.AsyncClient(
            timeout=300.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        
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
        model: LightningModel = LightningModel.CODE_LLAMA_34B,
        max_tokens: int = 2000,
        temperature: float = 0.1,
        stream: bool = False
    ) -> LightningResponse:
        """
        Generate completion using Lightning AI.
        
        Args:
            prompt: Input prompt
            model: Model to use (from LightningModel enum)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream response
        
        Returns:
            LightningResponse with generated text
        """
        
        if self.calls_made >= self.monthly_quota:
            raise RuntimeError(
                f"Monthly quota exceeded ({self.monthly_quota} calls). "
                "Consider upgrading your Lightning AI plan."
            )
        
        # Build request payload
        payload = {
            "model": model.value,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }
        
        try:
            response = await self.client.post(
                f"{self.studio_url}/api/v1/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            self.calls_made += 1
            
            return LightningResponse(
                text=result["choices"][0]["text"],
                model=model.value,
                usage=result.get("usage", {}),
                finish_reason=result["choices"][0].get("finish_reason", "stop"),
                metadata=result.get("metadata")
            )
            
        except httpx.HTTPError as e:
            raise RuntimeError(f"Lightning AI request failed: {str(e)}")
    
    async def generate_streaming(
        self,
        prompt: str,
        model: LightningModel = LightningModel.CODE_LLAMA_34B,
        max_tokens: int = 2000,
        temperature: float = 0.1
    ):
        """
        Stream response from Lightning AI.
        Yields chunks as they arrive.
        """
        
        payload = {
            "model": model.value,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }
        
        async with self.client.stream(
            "POST",
            f"{self.studio_url}/api/v1/generate",
            json=payload
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]  # Remove "data: " prefix
                    if chunk.strip() == "[DONE]":
                        break
                    
                    import json
                    data = json.loads(chunk)
                    if "choices" in data:
                        text = data["choices"][0].get("text", "")
                        yield text
        
        self.calls_made += 1
    
    def get_remaining_quota(self) -> int:
        """Get remaining API calls for the month"""
        return self.monthly_quota - self.calls_made
    
    async def close(self):
        """Cleanup"""
        await self.client.aclose()


class CodeAnalysisAgent:
    """
    Agent specialized for code analysis using Lightning AI models.
    Optimized for repo integration tasks.
    """
    
    def __init__(
        self,
        lightning_client: Optional[LightningAIClient] = None,
        preferred_model: LightningModel = LightningModel.CODE_LLAMA_34B
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
        
        response = await self.client.generate(
            prompt=prompt,
            model=self.model,
            max_tokens=2000,
            temperature=0.1
        )
        
        # Parse structured output
        analysis = self._parse_analysis(response.text)
        
        return analysis
    
    def _build_analysis_prompt(
        self,
        repo_content: Dict[str, str],
        target_context: Optional[str],
        instructions: str
    ) -> str:
        """Build optimized prompt for code analysis"""
        
        # Limit content to most relevant files
        relevant_files = self._select_relevant_files(repo_content, limit=5)
        
        # Use centralized prompt function
        return PROMPT_REPO_ANALYSIS(instructions, relevant_files, target_context)
    
    def _select_relevant_files(
        self,
        repo_content: Dict[str, str],
        limit: int = 5
    ) -> Dict[str, str]:
        """Select most relevant files for analysis"""
        
        # Priority: main files, core modules, APIs
        # TODO: Add more patterns based on project type and move to string constants
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
        """Parse LLM response into structured format"""
        
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Fallback: basic parsing
        return {
            "main_modules": [],
            "dependencies": [],
            "affected_files": [],
            "risks": [],
            "implementation_steps": [],
            "raw_response": response_text
        }
    
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
            model=self.model,
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


# Integration with Reflex UI
async def analyze_repo_with_lightning(
    repo_url: str,
    target_file: Optional[str],
    instructions: str,
    local_project_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main function to call from Reflex State.
    Uses Lightning AI for analysis.
    """
    
    from services.repo_integrator_service import RepoIntegratorAgent
    
    # Step 1: Clone and extract repo content
    # (Using existing service)
    integrator = RepoIntegratorAgent()
    
    try:
        repo_info = await integrator._analyze_source_repo(repo_url)
        
        # Step 2: Use Lightning AI for intelligent analysis
        lightning_agent = CodeAnalysisAgent()
        
        # Get file contents (simplified - in production, load actual files)
        repo_content = {
            "main.py": "# Sample content",
            "core/module.py": "# Sample content"
        }
        
        target_context = None
        if local_project_path and target_file:
            target_context = f"Target file: {target_file}\nProject: {local_project_path}"
        
        analysis = await lightning_agent.analyze_repository(
            repo_content=repo_content,
            target_context=target_context,
            user_instructions=instructions
        )
        
        # Step 3: Format for UI
        return {
            "main_file": target_file or "src/main.py",
            "affected_files": analysis.get("affected_files", []),
            "dependencies": analysis.get("dependencies", []),
            "estimated_changes": " ".join(analysis.get("implementation_steps", [])),
            "risks": analysis.get("risks", [])
        }
    
    finally:
        await integrator.close()
        if 'lightning_agent' in locals():
            await lightning_agent.close()


# Example: Direct usage
async def main():
    """Example usage"""
    
    client = LightningAIClient()
    
    try:
        # Simple generation
        response = await client.generate(
            prompt="Explain how to integrate FastAPI with async SQLAlchemy",
            model=LightningModel.CODE_LLAMA_34B,
            max_tokens=500
        )
        
        print(f"Generated text: {response.text}")
        print(f"Remaining quota: {client.get_remaining_quota()}")
        
        # Streaming example
        print("\nStreaming response:")
        async for chunk in client.generate_streaming(
            prompt="Write a Python function to parse git commits",
            model=LightningModel.CODE_LLAMA_34B
        ):
            print(chunk, end="", flush=True)
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())