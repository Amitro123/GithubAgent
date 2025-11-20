"""Orchestrator for coordinating all automation tasks."""

import logging
from typing import Dict, Any
from .github_client import GitHubClient
from .code_reviewer import CodeReviewer
from .readme_updater import ReadmeUpdater
from .spec_updater import SpecUpdater
from .config import Config

logger = logging.getLogger(__name__)


class AutomationOrchestrator:
    """Orchestrates code review, README updates, and spec documentation."""

    def __init__(
        self,
        github_client: GitHubClient,
        code_reviewer: CodeReviewer,
        readme_updater: ReadmeUpdater,
        spec_updater: SpecUpdater,
        config: Config,
    ):
        """Initialize orchestrator.

        Args:
            github_client: GitHub API client
            code_reviewer: Code review module
            readme_updater: README update module
            spec_updater: Spec update module
            config: Application configuration
        """
        self.github = github_client
        self.code_reviewer = code_reviewer
        self.readme_updater = readme_updater
        self.spec_updater = spec_updater
        self.config = config

    def process_push(self, commit_sha: str, branch: str, commit_message: str) -> Dict[str, Any]:
        """Process a push event and execute all automation tasks.

        Args:
            commit_sha: Commit SHA to process
            branch: Branch name
            commit_message: Commit message

        Returns:
            Dictionary with results of all tasks
        """
        logger.info(f"Starting automation orchestration for commit {commit_sha[:7]}")

        results = {
            "success": True,
            "commit_sha": commit_sha,
            "branch": branch,
            "tasks": {
                "code_review": {"status": "pending"},
                "readme_update": {"status": "pending"},
                "spec_update": {"status": "pending"},
            },
        }

        # Task 1: Code Review
        try:
            logger.info("Task 1: Running code review...")
            review_success = self.code_reviewer.review_commit(
                commit_sha=commit_sha,
                post_as_issue=self.config.POST_REVIEW_AS_ISSUE,
            )
            results["tasks"]["code_review"] = {
                "status": "completed" if review_success else "failed",
                "posted_as_issue": self.config.POST_REVIEW_AS_ISSUE,
            }
            if not review_success:
                results["success"] = False
        except Exception as e:
            logger.error(f"Code review failed: {e}", exc_info=True)
            results["tasks"]["code_review"] = {"status": "error", "error": str(e)}
            results["success"] = False

        # Task 2: README Update
        try:
            logger.info("Task 2: Checking README updates...")
            updated_readme = self.readme_updater.update_readme(
                commit_sha=commit_sha, branch=branch
            )

            if updated_readme:
                # Determine where to commit
                if self.config.CREATE_PR:
                    pr_result = self._create_documentation_pr(
                        branch=branch,
                        readme_content=updated_readme,
                        spec_content=None,  # Will be added later
                        commit_sha=commit_sha,
                    )
                    results["tasks"]["readme_update"] = {
                        "status": "completed",
                        "pr_created": pr_result["success"],
                        "pr_number": pr_result.get("pr_number"),
                    }
                elif self.config.AUTO_COMMIT:
                    commit_success = self.github.update_file(
                        file_path="README.md",
                        content=updated_readme,
                        message=f"docs: Auto-update README.md from {commit_sha[:7]}",
                        branch=branch,
                    )
                    results["tasks"]["readme_update"] = {
                        "status": "completed" if commit_success else "failed",
                        "auto_committed": commit_success,
                    }
                else:
                    results["tasks"]["readme_update"] = {
                        "status": "completed",
                        "note": "Updates generated but not committed (CREATE_PR and AUTO_COMMIT both false)",
                    }
            else:
                results["tasks"]["readme_update"] = {
                    "status": "skipped",
                    "reason": "No updates needed",
                }
        except Exception as e:
            logger.error(f"README update failed: {e}", exc_info=True)
            results["tasks"]["readme_update"] = {"status": "error", "error": str(e)}
            results["success"] = False

        # Task 3: Spec.md Update
        try:
            logger.info("Task 3: Updating spec.md...")
            updated_spec = self.spec_updater.update_spec(
                commit_sha=commit_sha, branch=branch
            )

            if updated_spec:
                if self.config.CREATE_PR:
                    # If README PR was created, add spec to it; otherwise create new PR
                    if results["tasks"]["readme_update"].get("pr_created"):
                        # Update spec in the same PR branch
                        pr_branch = f"automation/docs-update-{commit_sha[:7]}"
                        commit_success = self.github.update_file(
                            file_path="spec.md",
                            content=updated_spec,
                            message=f"docs: Auto-update spec.md from {commit_sha[:7]}",
                            branch=pr_branch,
                        )
                        results["tasks"]["spec_update"] = {
                            "status": "completed" if commit_success else "failed",
                            "added_to_pr": commit_success,
                        }
                    else:
                        pr_result = self._create_documentation_pr(
                            branch=branch,
                            readme_content=None,
                            spec_content=updated_spec,
                            commit_sha=commit_sha,
                        )
                        results["tasks"]["spec_update"] = {
                            "status": "completed",
                            "pr_created": pr_result["success"],
                            "pr_number": pr_result.get("pr_number"),
                        }
                elif self.config.AUTO_COMMIT:
                    commit_success = self.github.update_file(
                        file_path="spec.md",
                        content=updated_spec,
                        message=f"docs: Auto-update spec.md from {commit_sha[:7]}",
                        branch=branch,
                    )
                    results["tasks"]["spec_update"] = {
                        "status": "completed" if commit_success else "failed",
                        "auto_committed": commit_success,
                    }
                else:
                    results["tasks"]["spec_update"] = {
                        "status": "completed",
                        "note": "Updates generated but not committed",
                    }
            else:
                results["tasks"]["spec_update"] = {
                    "status": "failed",
                    "reason": "Failed to generate spec update",
                }
                results["success"] = False
        except Exception as e:
            logger.error(f"Spec update failed: {e}", exc_info=True)
            results["tasks"]["spec_update"] = {"status": "error", "error": str(e)}
            results["success"] = False

        logger.info(f"Automation orchestration completed. Success: {results['success']}")
        return results

    def _create_documentation_pr(
        self,
        branch: str,
        readme_content: str = None,
        spec_content: str = None,
        commit_sha: str = "",
    ) -> Dict[str, Any]:
        """Create a pull request with documentation updates.

        Args:
            branch: Base branch
            readme_content: Updated README content (optional)
            spec_content: Updated spec content (optional)
            commit_sha: Commit SHA that triggered the update

        Returns:
            Dictionary with PR creation result
        """
        pr_branch = f"automation/docs-update-{commit_sha[:7]}"

        try:
            # Create branch
            if not self.github.create_branch(pr_branch, from_branch=branch):
                return {"success": False, "error": "Failed to create branch"}

            # Commit files
            if readme_content:
                if not self.github.update_file(
                    file_path="README.md",
                    content=readme_content,
                    message=f"docs: Auto-update README.md from {commit_sha[:7]}",
                    branch=pr_branch,
                ):
                    return {"success": False, "error": "Failed to update README.md"}

            if spec_content:
                if not self.github.update_file(
                    file_path="spec.md",
                    content=spec_content,
                    message=f"docs: Auto-update spec.md from {commit_sha[:7]}",
                    branch=pr_branch,
                ):
                    return {"success": False, "error": "Failed to update spec.md"}

            # Create PR
            pr_title = f"🤖 Auto-update documentation from {commit_sha[:7]}"
            pr_body = f"""## Automated Documentation Update

This PR contains automated documentation updates generated from commit `{commit_sha[:7]}`.

### Changes Included:
{"- ✅ README.md updated" if readme_content else ""}
{"- ✅ spec.md updated" if spec_content else ""}

### Review Instructions:
1. Review the documentation changes for accuracy
2. Ensure all new features/changes are properly documented
3. Check for any formatting issues
4. Merge if everything looks good

---
*This PR was created automatically by the GitHub Automation Agent.*
"""

            pr_number = self.github.create_pull_request(
                title=pr_title, body=pr_body, head=pr_branch, base=branch
            )

            if pr_number:
                logger.info(f"Created documentation PR #{pr_number}")
                return {"success": True, "pr_number": pr_number, "branch": pr_branch}
            else:
                return {"success": False, "error": "Failed to create PR"}

        except Exception as e:
            logger.error(f"Failed to create documentation PR: {e}")
            return {"success": False, "error": str(e)}
