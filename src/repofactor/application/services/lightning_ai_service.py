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
            stream: Whether to stream response
        
        Returns:
            LightningResponse with generated text
        
        Raises:
            RuntimeError: If quota exceeded or request fails
        """
        
        # ✅ Validate prompt length (before quota check)
        if len(prompt) > 30000:  # ~7500 tokens
            logger.warning(f"⚠️  Prompt is very long: {len(prompt)} chars")
            logger.warning("   Consider truncating files more aggressively")
        
        # ✅ Check quota
        if self.calls_made >= self.monthly_quota:
            raise RuntimeError(
                f"Monthly quota exceeded ({self.monthly_quota} calls). "
                "Consider upgrading your Lightning AI plan."
            )
        
        # ✅ Determine model to use
        if model:
            if isinstance(model, LightningModel):
                use_model = model.value
            else:
                use_model = model
        else:
            use_model = self.model_name
        
        # ✅ Switch model if different
        if use_model != self.llm.model:
            logger.info(f"🔄 Switching model to: {use_model}")
            self.llm = LLM(model=use_model)
        
        try:
            # ✅ Call Lightning AI
            loop = asyncio.get_event_loop()
            
            logger.info(f"🔄 Calling Lightning AI...")
            logger.info(f"   Prompt: {len(prompt)} chars (~{len(prompt)//4} tokens)")
            logger.info(f"   Model: {use_model}")
            logger.info(f"   Max tokens: {max_tokens}")
            
            response_text = await loop.run_in_executor(
                None,
                self.llm.chat,
                prompt
            )
            
            # ✅ Enhanced debugging
            logger.info(f"✅ Response received")
            logger.debug(f"   Type: {type(response_text)}")
            logger.debug(f"   Repr: {repr(response_text)[:200]}")
            
            # ✅ Handle different response types
            if response_text is None:
                logger.error("❌ Lightning AI returned None!")
                raise RuntimeError("Lightning AI returned None")
            
            # If dict, extract text content
            if isinstance(response_text, dict):
                logger.debug(f"   Response is dict with keys: {response_text.keys()}")
                text_content = (
                    response_text.get('content') or 
                    response_text.get('text') or 
                    response_text.get('response') or 
                    response_text.get('message') or
                    str(response_text)
                )
                response_text = text_content
            
            # Convert to string if needed
            if not isinstance(response_text, str):
                logger.debug(f"   Converting {type(response_text)} to string")
                response_text = str(response_text)
            
            # ✅ Validate final result
            if not response_text or not response_text.strip():
                logger.error("❌ Lightning AI returned empty string!")
                logger.error(f"   Original response type: {type(response_text)}")
                raise RuntimeError("Lightning AI returned empty response")
            
            logger.info(f"✅ Response validated")
            logger.info(f"   Length: {len(response_text)} chars")
            logger.debug(f"   Preview: {response_text[:200]}...")
            
            # ✅ Update quota counter
            self.calls_made += 1
            logger.info(f"📊 Quota: {self.calls_made}/{self.monthly_quota} calls used")
            
            # ✅ Return structured response
            return LightningResponse(
                text=response_text,
                model=use_model,
                usage={"total_tokens": len(response_text.split()) if response_text else 0},
                finish_reason="stop"
            )
            
        except Exception as e:
            logger.error(f"❌ Lightning AI request failed: {e}")
            logger.error(f"   Prompt length: {len(prompt)} chars")
            logger.error(f"   Model: {use_model}")
            logger.error(f"   Exception type: {type(e).__name__}", exc_info=True)
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
