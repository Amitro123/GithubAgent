"""Automated code review module using LLM analysis."""

import logging
from typing import Optional, Dict, Any
from .llm_client import LLMClient
from .github_client import GitHubClient

logger = logging.getLogger(__name__)


class CodeReviewer:
    """Automated code review with quality, security, and best practices analysis."""

    def __init__(self, github_client: GitHubClient, llm_client: LLMClient):
        """Initialize code reviewer.

        Args:
            github_client: GitHub API client
            llm_client: LLM client for analysis
        """
        self.github = github_client
        self.llm = llm_client

    def review_commit(self, commit_sha: str, post_as_issue: bool = False) -> bool:
        """Review a commit and post findings.

        Args:
            commit_sha: Commit SHA to review
            post_as_issue: If True, post as issue; otherwise as commit comment

        Returns:
            True if review was posted successfully
        """
        logger.info(f"Starting code review for commit {commit_sha}")

        # Fetch commit diff
        diff = self.github.get_commit_diff(commit_sha)
        if not diff:
            logger.error("Failed to fetch commit diff")
            return False

        # Fetch commit info for context
        commit_info = self.github.get_commit_info(commit_sha)
        if not commit_info:
            logger.error("Failed to fetch commit info")
            return False

        commit_message = commit_info.get("commit", {}).get("message", "")
        author = commit_info.get("commit", {}).get("author", {}).get("name", "Unknown")

        # Generate code review
        review = self._analyze_code_changes(diff, commit_message, author)
        if not review:
            logger.error("Failed to generate code review")
            return False

        # Post review
        if post_as_issue:
            title = f"🤖 Code Review: {commit_sha[:7]}"
            issue_number = self.github.create_issue(
                title=title,
                body=review,
                labels=["automated-review", "code-quality"]
            )
            return issue_number is not None
        else:
            return self.github.post_commit_comment(commit_sha, review)

    def _analyze_code_changes(
        self, diff: str, commit_message: str, author: str
    ) -> Optional[str]:
        """Analyze code changes using LLM.

        Args:
            diff: Git diff content
            commit_message: Commit message
            author: Commit author

        Returns:
            Formatted review text or None if analysis fails
        """
        prompt = self._build_review_prompt(diff, commit_message, author)
        
        try:
            analysis = self.llm.generate(prompt, max_tokens=2000)
            return self._format_review(analysis)
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return None

    def _build_review_prompt(self, diff: str, commit_message: str, author: str) -> str:
        """Build prompt for LLM code review.

        Args:
            diff: Git diff content
            commit_message: Commit message
            author: Commit author

        Returns:
            Formatted prompt string
        """
        # Truncate diff if too long (keep first 8000 chars)
        if len(diff) > 8000:
            diff = diff[:8000] + "\n\n[... diff truncated for analysis ...]\n"

        return f"""You are an expert code reviewer. Analyze the following code changes and provide a comprehensive review.

**Commit Information:**
- Author: {author}
- Message: {commit_message}

**Code Changes (Git Diff):**
```diff
{diff}
```

**Review Instructions:**
Provide a detailed code review covering:

1. **Code Quality**: Assess readability, maintainability, and adherence to best practices
2. **Potential Bugs**: Identify any logic errors, edge cases, or potential runtime issues
3. **Security Concerns**: Flag any security vulnerabilities or unsafe practices
4. **Performance**: Note any performance implications or optimization opportunities
5. **Best Practices**: Suggest improvements aligned with language/framework conventions
6. **Testing**: Comment on test coverage and testing approach if applicable

**Output Format:**
Structure your review as:
- ✅ **Strengths**: What's done well
- ⚠️ **Issues Found**: Critical problems that need fixing
- 💡 **Suggestions**: Recommendations for improvement
- 🔒 **Security**: Security-related observations
- 📝 **Summary**: Overall assessment and priority actions

Be constructive, specific, and actionable. Reference line numbers or code snippets when relevant.
"""

    def _format_review(self, analysis: str) -> str:
        """Format the LLM analysis into a GitHub-friendly review.

        Args:
            analysis: Raw LLM analysis text

        Returns:
            Formatted review with header and footer
        """
        header = """# 🤖 Automated Code Review

*This review was generated automatically by the GitHub Automation Agent.*

---

"""
        footer = """\n\n---

*💡 This is an automated review. Please use your judgment and discuss with your team before making changes.*
"""
        return header + analysis + footer
