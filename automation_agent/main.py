#!/usr/bin/env python3
"""Main entry point for GitHub Automation Agent."""

import logging
import sys
from .config import Config
from .webhook_server import WebhookServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main():
    """Main function to start the automation agent."""
    logger.info("Starting GitHub Automation Agent...")

    # Validate configuration
    errors = Config.validate()
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    logger.info("Configuration validated successfully")
    logger.info(f"Repository: {Config.get_repo_full_name()}")
    logger.info(f"LLM Provider: {Config.LLM_PROVIDER} ({Config.LLM_MODEL})")
    logger.info(f"Create PR: {Config.CREATE_PR}")
    logger.info(f"Auto Commit: {Config.AUTO_COMMIT}")
    logger.info(f"Post Review as Issue: {Config.POST_REVIEW_AS_ISSUE}")

    # Initialize and run webhook server
    try:
        server = WebhookServer(Config)
        server.run()
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
