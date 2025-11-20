"""LLM client supporting OpenAI and Anthropic."""

import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)


class LLMClient:
    """Universal LLM client supporting multiple providers."""

    def __init__(self, provider: str = "openai", model: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize LLM client.

        Args:
            provider: LLM provider ("openai" or "anthropic")
            model: Model name (optional, uses provider defaults)
            api_key: API key (optional, reads from environment)
        """
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate LLM client."""
        if self.provider == "openai":
            self._initialize_openai()
        elif self.provider == "anthropic":
            self._initialize_anthropic()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _initialize_openai(self):
        """Initialize OpenAI client."""
        try:
            import openai
            self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key not provided")
            
            self._client = openai.OpenAI(api_key=self.api_key)
            self.model = self.model or "gpt-4-turbo-preview"
            logger.info(f"Initialized OpenAI client with model {self.model}")
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")

    def _initialize_anthropic(self):
        """Initialize Anthropic client."""
        try:
            import anthropic
            self.api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("Anthropic API key not provided")
            
            self._client = anthropic.Anthropic(api_key=self.api_key)
            self.model = self.model or "claude-3-opus-20240229"
            logger.info(f"Initialized Anthropic client with model {self.model}")
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate text using the configured LLM.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)

        Returns:
            Generated text

        Raises:
            Exception: If generation fails
        """
        if self.provider == "openai":
            return self._generate_openai(prompt, max_tokens, temperature)
        elif self.provider == "anthropic":
            return self._generate_anthropic(prompt, max_tokens, temperature)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _generate_openai(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Generate text using OpenAI.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    def _generate_anthropic(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Generate text using Anthropic.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise
