# services/lightning_ai_service.py
"""
Integration with Lightning AI using LitAI SDK
https://lightning.ai/models
"""
import os, sys, re
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
try:
    from tenacity import retry, stop_after_attempt, wait_exponential
except ImportError:
    def retry(*args, **kwargs):
        def decorator(f):
            return f
        return decorator
    def stop_after_attempt(*args, **kwargs):
        pass
    def wait_exponential(*args, **kwargs):
        pass
import logging


# Import LitAI SDK instead of httpx
try:
    from litai import LLM
except ImportError:
    LLM = None

logger = logging.getLogger(__name__)


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