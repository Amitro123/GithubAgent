"""Configuration management for GitHub Automation Agent."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # GitHub Configuration
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    REPOSITORY_OWNER: str = os.getenv("REPOSITORY_OWNER", "")
    REPOSITORY_NAME: str = os.getenv("REPOSITORY_NAME", "")

    # LLM Configuration (supports both OpenAI and Anthropic)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "anthropic"
    LLM_MODEL: str = os.getenv(
        "LLM_MODEL",
        "gpt-4-turbo-preview" if LLM_PROVIDER == "openai" else "claude-3-opus-20240229"
    )

    # Webhook Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Automation Behavior
    CREATE_PR: bool = os.getenv("CREATE_PR", "True").lower() == "true"
    POST_REVIEW_AS_ISSUE: bool = os.getenv("POST_REVIEW_AS_ISSUE", "False").lower() == "true"
    AUTO_COMMIT: bool = os.getenv("AUTO_COMMIT", "False").lower() == "true"

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration values.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not cls.GITHUB_TOKEN:
            errors.append("GITHUB_TOKEN is required")
        if not cls.GITHUB_WEBHOOK_SECRET:
            errors.append("GITHUB_WEBHOOK_SECRET is required")
        if not cls.REPOSITORY_OWNER:
            errors.append("REPOSITORY_OWNER is required")
        if not cls.REPOSITORY_NAME:
            errors.append("REPOSITORY_NAME is required")

        if cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when using OpenAI")
        elif cls.LLM_PROVIDER == "anthropic" and not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is required when using Anthropic")
        elif cls.LLM_PROVIDER not in ["openai", "anthropic"]:
            errors.append("LLM_PROVIDER must be 'openai' or 'anthropic'")

        return errors

    @classmethod
    def get_repo_full_name(cls) -> str:
        """Get full repository name in owner/repo format."""
        return f"{cls.REPOSITORY_OWNER}/{cls.REPOSITORY_NAME}"
