"""GitHub webhook server for push event handling."""

import logging
import hmac
import hashlib
from typing import Optional
from flask import Flask, request, jsonify
from .config import Config
from .github_client import GitHubClient
from .llm_client import LLMClient
from .code_reviewer import CodeReviewer
from .readme_updater import ReadmeUpdater
from .spec_updater import SpecUpdater
from .orchestrator import AutomationOrchestrator

logger = logging.getLogger(__name__)


class WebhookServer:
    """GitHub webhook server with signature verification."""

    def __init__(self, config: Config):
        """Initialize webhook server.

        Args:
            config: Application configuration
        """
        self.config = config
        self.app = Flask(__name__)
        self._setup_routes()
        self._initialize_components()

    def _initialize_components(self):
        """Initialize GitHub client, LLM client, and automation modules."""
        # Initialize clients
        self.github_client = GitHubClient(
            token=self.config.GITHUB_TOKEN,
            owner=self.config.REPOSITORY_OWNER,
            repo=self.config.REPOSITORY_NAME,
        )

        self.llm_client = LLMClient(
            provider=self.config.LLM_PROVIDER,
            model=self.config.LLM_MODEL,
            api_key=self.config.OPENAI_API_KEY or self.config.ANTHROPIC_API_KEY,
        )

        # Initialize automation modules
        self.code_reviewer = CodeReviewer(self.github_client, self.llm_client)
        self.readme_updater = ReadmeUpdater(self.github_client, self.llm_client)
        self.spec_updater = SpecUpdater(self.github_client, self.llm_client)

        # Initialize orchestrator
        self.orchestrator = AutomationOrchestrator(
            github_client=self.github_client,
            code_reviewer=self.code_reviewer,
            readme_updater=self.readme_updater,
            spec_updater=self.spec_updater,
            config=self.config,
        )

        logger.info("Webhook server components initialized")

    def _setup_routes(self):
        """Setup Flask routes."""
        @self.app.route("/", methods=["GET"])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                "status": "healthy",
                "service": "GitHub Automation Agent",
                "version": "1.0.0"
            }), 200

        @self.app.route("/webhook", methods=["POST"])
        def webhook():
            """GitHub webhook endpoint."""
            # Verify webhook signature
            if not self._verify_signature(request):
                logger.warning("Invalid webhook signature")
                return jsonify({"error": "Invalid signature"}), 403

            # Get event type
            event_type = request.headers.get("X-GitHub-Event")
            if event_type != "push":
                logger.info(f"Ignoring non-push event: {event_type}")
                return jsonify({"message": "Event ignored"}), 200

            # Process push event
            payload = request.json
            return self._handle_push_event(payload)

    def _verify_signature(self, request) -> bool:
        """Verify GitHub webhook signature.

        Args:
            request: Flask request object

        Returns:
            True if signature is valid, False otherwise
        """
        signature_header = request.headers.get("X-Hub-Signature-256")
        if not signature_header:
            logger.warning("No signature header found")
            return False

        # Extract signature
        try:
            sha_name, signature = signature_header.split("=")
            if sha_name != "sha256":
                logger.warning(f"Unexpected signature algorithm: {sha_name}")
                return False
        except ValueError:
            logger.warning("Invalid signature format")
            return False

        # Compute expected signature
        mac = hmac.new(
            self.config.GITHUB_WEBHOOK_SECRET.encode(),
            msg=request.data,
            digestmod=hashlib.sha256,
        )
        expected_signature = mac.hexdigest()

        # Compare signatures (constant-time comparison)
        return hmac.compare_digest(expected_signature, signature)

    def _handle_push_event(self, payload: dict) -> tuple:
        """Handle GitHub push event.

        Args:
            payload: Webhook payload

        Returns:
            Flask response tuple (response_dict, status_code)
        """
        try:
            # Extract commit information
            commits = payload.get("commits", [])
            if not commits:
                logger.info("No commits in push event")
                return jsonify({"message": "No commits to process"}), 200

            ref = payload.get("ref", "")
            branch = ref.split("/")[-1] if "/" in ref else ref

            # Get the latest commit
            head_commit = payload.get("head_commit")
            if not head_commit:
                logger.warning("No head commit in payload")
                return jsonify({"error": "No head commit found"}), 400

            commit_sha = head_commit.get("id")
            commit_message = head_commit.get("message", "")

            logger.info(f"Processing push event: {commit_sha[:7]} on {branch}")
            logger.info(f"Commit message: {commit_message}")

            # Run automation orchestrator
            result = self.orchestrator.process_push(
                commit_sha=commit_sha,
                branch=branch,
                commit_message=commit_message,
            )

            if result["success"]:
                return jsonify({
                    "message": "Automation completed successfully",
                    "details": result
                }), 200
            else:
                return jsonify({
                    "message": "Automation completed with errors",
                    "details": result
                }), 207  # Multi-status

        except Exception as e:
            logger.error(f"Error processing push event: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    def run(self):
        """Run the webhook server."""
        logger.info(f"Starting webhook server on {self.config.HOST}:{self.config.PORT}")
        self.app.run(
            host=self.config.HOST,
            port=self.config.PORT,
            debug=self.config.DEBUG,
        )
