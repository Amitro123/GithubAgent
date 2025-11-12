# services/lightning_ai_service.py
"""
Integration with Lightning AI using LitAI SDK
https://lightning.ai/models
"""
import os
import sys
import re
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging

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

# Import LitAI SDK
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
    Client for Lightning AI inference using LitAI SDK.
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
    
    async def _call_llm(
        self, prompt: str, model: str, max_tokens: int, temperature: float
    ) -> LightningResponse:
        """Helper to call the LLM and handle response."""

        loop = asyncio.get_event_loop()
        logger.info("🔄 Calling Lightning AI...")
        logger.info(f"   Prompt: {len(prompt)} chars (~{len(prompt)//4} tokens)")
        logger.info(f"   Model: {model}")

        response_text = await loop.run_in_executor(None, self.llm.chat, prompt)

        logger.info("✅ Response received")
        logger.debug(f"   Type: {type(response_text)}")

        if response_text is None:
            raise RuntimeError("Lightning AI returned None")

        if isinstance(response_text, dict):
            text_content = (
                response_text.get('content') or
                response_text.get('text') or
                str(response_text)
            )
            response_text = text_content

        if not isinstance(response_text, str):
            response_text = str(response_text)

        if not response_text.strip():
            raise RuntimeError("Lightning AI returned empty response")

        logger.info(f"✅ Response validated (length: {len(response_text)})")
        logger.debug(f"   Preview: {response_text[:200]}...")

        return LightningResponse(
            text=response_text,
            model=model,
            usage={"total_tokens": len(response_text.split())},
            finish_reason="stop"
        )

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
        stream: bool = False,
        prompt_fallback: Optional[str] = None
    ) -> LightningResponse:
        """
        Generate completion with fallback for empty responses.
        """
        if self.calls_made >= self.monthly_quota:
            raise RuntimeError(f"Monthly quota exceeded ({self.monthly_quota} calls).")

        use_model = model or self.model_name
        if use_model != self.llm.model:
            logger.info(f"🔄 Switching model to: {use_model}")
            self.llm = LLM(model=use_model)

        try:
            # Initial attempt
            response = await self._call_llm(prompt, use_model, max_tokens, temperature)
            self.calls_made += 1
            logger.info(f"📊 Quota: {self.calls_made}/{self.monthly_quota} calls used")
            return response

        except Exception as e:
            logger.warning(f"Initial LLM call failed: {e}")
            
            if prompt_fallback:
                logger.info("🔄 Retrying with fallback prompt...")

                # Check quota again for fallback
                if self.calls_made >= self.monthly_quota:
                    raise RuntimeError(f"Monthly quota exceeded before fallback.")

                try:
                    # Fallback attempt
                    response = await self._call_llm(prompt_fallback, use_model, max_tokens, temperature)
                    self.calls_made += 1
                    logger.info(f"✅ Fallback call successful!")
                    logger.info(f"📊 Quota: {self.calls_made}/{self.monthly_quota} calls used")
                    return response
                except Exception as fallback_e:
                    logger.error(f"❌ Fallback call also failed: {fallback_e}", exc_info=True)
                    raise fallback_e
            
            logger.error("❌ No fallback available. Raising original error.", exc_info=True)
            raise e

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
