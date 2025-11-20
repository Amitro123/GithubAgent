"""Automated spec.md project documentation module."""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from .llm_client import LLMClient
from .github_client import GitHubClient

logger = logging.getLogger(__name__)


class SpecUpdater:
    """Automated spec.md project progress documentation."""

    def __init__(self, github_client: GitHubClient, llm_client: LLMClient):
        """Initialize spec updater.

        Args:
            github_client: GitHub API client
            llm_client: LLM client for analysis
        """
        self.github = github_client
        self.llm = llm_client

    def update_spec(self, commit_sha: str, branch: str = "main") -> Optional[str]:
        """Update spec.md with project progress documentation.

        Args:
            commit_sha: Commit SHA to document
            branch: Branch to update spec on

        Returns:
            Updated spec content, or None if update fails
        """
        logger.info(f"Generating spec.md update for commit {commit_sha}")

        # Fetch commit info and diff
        commit_info = self.github.get_commit_info(commit_sha)
        if not commit_info:
            logger.error("Failed to fetch commit info")
            return None

        diff = self.github.get_commit_diff(commit_sha)
        if not diff:
            logger.error("Failed to fetch commit diff")
            return None

        # Fetch recent commit history for context
        recent_commits = self.github.get_recent_commits(limit=5)

        # Fetch current spec.md
        current_spec = self.github.get_file_content("spec.md", ref=branch)
        if current_spec is None:
            logger.info("spec.md not found, creating new one")
            current_spec = self._create_initial_spec()

        # Generate spec update
        spec_entry = self._generate_spec_entry(
            commit_info, diff, recent_commits, current_spec
        )

        if not spec_entry:
            logger.error("Failed to generate spec entry")
            return None

        # Append to spec
        updated_spec = self._append_to_spec(current_spec, spec_entry)
        logger.info("spec.md update generated")
        return updated_spec

    def _create_initial_spec(self) -> str:
        """Create initial spec.md structure.

        Returns:
            Initial spec.md content
        """
        return f"""# Project Specification & Progress

*Last Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*

## Overview

This document tracks the project's development progress, architectural decisions, and milestones.

## Development Log

<!-- Automated entries will be appended below -->

"""

    def _generate_spec_entry(
        self,
        commit_info: Dict[str, Any],
        diff: str,
        recent_commits: List[Dict[str, Any]],
        current_spec: str
    ) -> Optional[str]:
        """Generate a spec.md entry for the commit.

        Args:
            commit_info: Commit information
            diff: Git diff content
            recent_commits: Recent commit history
            current_spec: Current spec.md content

        Returns:
            Formatted spec entry or None
        """
        prompt = self._build_spec_prompt(
            commit_info, diff, recent_commits, current_spec
        )
        
        try:
            entry = self.llm.generate(prompt, max_tokens=1500)
            return self._format_spec_entry(entry, commit_info)
        except Exception as e:
            logger.error(f"Failed to generate spec entry: {e}")
            return None

    def _build_spec_prompt(
        self,
        commit_info: Dict,
        diff: str,
        recent_commits: List[Dict],
        current_spec: str
    ) -> str:
        """Build prompt for spec generation.

        Args:
            commit_info: Current commit info
            diff: Git diff
            recent_commits: Recent commits
            current_spec: Current spec content

        Returns:
            Formatted prompt
        """
        # Truncate diff if too long
        if len(diff) > 6000:
            diff = diff[:6000] + "\n[... truncated ...]\n"

        commit_message = commit_info.get("commit", {}).get("message", "")
        commit_sha = commit_info.get("sha", "")[:7]
        author = commit_info.get("commit", {}).get("author", {}).get("name", "Unknown")
        date = commit_info.get("commit", {}).get("author", {}).get("date", "")

        # Format recent commits for context
        recent_commits_text = "\n".join([
            f"- {c.get('sha', '')[:7]}: {c.get('commit', {}).get('message', '').split(chr(10))[0]}"
            for c in recent_commits[:5]
        ])

        return f"""You are a technical project manager documenting project progress. Generate a comprehensive progress entry for the project specification document.

**Current Commit:**
- SHA: {commit_sha}
- Author: {author}
- Date: {date}
- Message: {commit_message}

**Recent Commit History:**
{recent_commits_text}

**Code Changes:**
```diff
{diff}
```

**Current Spec.md Context (last 1000 chars):**
```
{current_spec[-1000:]}
```

**Instructions:**
Generate a structured progress entry that includes:

1. **Summary of Changes**: High-level overview of what was accomplished
2. **Features Added/Modified**: New functionality or changes to existing features
3. **Technical Details**: Important implementation details, algorithms, or patterns used
4. **Architecture Decisions**: Any architectural choices or design patterns introduced
5. **Dependencies & Configuration**: Changes to dependencies, configs, or setup requirements
6. **Milestones Reached**: Significant milestones or completion of major features
7. **Next Steps**: Suggested next actions or remaining tasks based on the current state

**Output Format:**
Provide a well-structured markdown entry that will be appended to the spec document. Use:
- Clear headings (### for subsections)
- Bullet points for lists
- Code snippets where relevant
- Concise but informative language
- Professional tone

Do NOT include the date header or commit SHA (will be added automatically).
"""

    def _format_spec_entry(self, entry: str, commit_info: Dict) -> str:
        """Format the spec entry with header.

        Args:
            entry: Raw entry content
            commit_info: Commit information

        Returns:
            Formatted entry with header
        """
        commit_sha = commit_info.get("sha", "")[:7]
        commit_message = commit_info.get("commit", {}).get("message", "").split("\n")[0]
        date = datetime.utcnow().strftime("%Y-%m-%d")
        author = commit_info.get("commit", {}).get("author", {}).get("name", "Unknown")

        header = f"""\n---\n\n## [{date}] Update - Commit {commit_sha}

**Commit**: `{commit_sha}` - {commit_message}  
**Author**: {author}  
**Timestamp**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  

"""
        return header + entry.strip() + "\n"

    def _append_to_spec(self, current_spec: str, entry: str) -> str:
        """Append new entry to spec.md.

        Args:
            current_spec: Current spec content
            entry: New entry to append

        Returns:
            Updated spec content
        """
        # Update the "Last Updated" timestamp
        updated_timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        current_spec = current_spec.replace(
            '*Last Updated:',
            f'*Last Updated: {updated_timestamp}*\n\n*Previous Update:'
        )

        # Append the new entry
        return current_spec + "\n" + entry
