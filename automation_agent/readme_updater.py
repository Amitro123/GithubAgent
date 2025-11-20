"""Automated README.md update module."""

import logging
import re
from typing import Optional, Dict, List
from .llm_client import LLMClient
from .github_client import GitHubClient

logger = logging.getLogger(__name__)


class ReadmeUpdater:
    """Automated README.md updates based on code changes."""

    def __init__(self, github_client: GitHubClient, llm_client: LLMClient):
        """Initialize README updater.

        Args:
            github_client: GitHub API client
            llm_client: LLM client for analysis
        """
        self.github = github_client
        self.llm = llm_client

    def update_readme(self, commit_sha: str, branch: str = "main") -> Optional[str]:
        """Update README.md based on code changes.

        Args:
            commit_sha: Commit SHA to analyze
            branch: Branch to update README on

        Returns:
            Updated README content, or None if no updates needed
        """
        logger.info(f"Analyzing commit {commit_sha} for README updates")

        # Fetch commit diff and info
        diff = self.github.get_commit_diff(commit_sha)
        if not diff:
            logger.error("Failed to fetch commit diff")
            return None

        commit_info = self.github.get_commit_info(commit_sha)
        if not commit_info:
            logger.error("Failed to fetch commit info")
            return None

        # Fetch current README
        current_readme = self.github.get_file_content("README.md", ref=branch)
        if current_readme is None:
            logger.warning("README.md not found, will create new one")
            current_readme = "# Project\n\nProject description.\n"

        # Analyze changes and determine updates
        changes_summary = self._extract_changes(diff, commit_info)
        updated_readme = self._generate_updated_readme(
            current_readme, changes_summary, diff
        )

        if not updated_readme or updated_readme == current_readme:
            logger.info("No README updates needed")
            return None

        logger.info("README updates generated")
        return updated_readme

    def _extract_changes(self, diff: str, commit_info: Dict) -> Dict[str, List[str]]:
        """Extract key changes from diff.

        Args:
            diff: Git diff content
            commit_info: Commit information

        Returns:
            Dictionary categorizing changes
        """
        changes = {
            "new_files": [],
            "modified_files": [],
            "new_functions": [],
            "new_classes": [],
            "dependencies": [],
            "config_changes": []
        }

        # Extract file changes
        files = commit_info.get("files", [])
        for file in files:
            filename = file.get("filename", "")
            status = file.get("status", "")
            
            if status == "added":
                changes["new_files"].append(filename)
            elif status in ["modified", "renamed"]:
                changes["modified_files"].append(filename)

            # Check for dependency files
            if filename in ["requirements.txt", "package.json", "Pipfile", "pyproject.toml"]:
                changes["dependencies"].append(filename)
            
            # Check for config files
            if filename.endswith((".env", ".config", ".yml", ".yaml", ".json", ".toml")):
                changes["config_changes"].append(filename)

        # Extract function and class definitions from diff
        # Python patterns
        function_pattern = r'^\+\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        class_pattern = r'^\+\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[:\(]'
        
        for line in diff.split('\n'):
            func_match = re.match(function_pattern, line)
            if func_match:
                changes["new_functions"].append(func_match.group(1))
            
            class_match = re.match(class_pattern, line)
            if class_match:
                changes["new_classes"].append(class_match.group(1))

        return changes

    def _generate_updated_readme(
        self, current_readme: str, changes: Dict, diff: str
    ) -> Optional[str]:
        """Generate updated README using LLM.

        Args:
            current_readme: Current README content
            changes: Extracted changes summary
            diff: Git diff content

        Returns:
            Updated README content or None
        """
        prompt = self._build_readme_update_prompt(current_readme, changes, diff)
        
        try:
            updated_readme = self.llm.generate(prompt, max_tokens=3000)
            # Clean up potential markdown artifacts
            updated_readme = self._clean_readme_output(updated_readme)
            return updated_readme
        except Exception as e:
            logger.error(f"Failed to generate README updates: {e}")
            return None

    def _build_readme_update_prompt(
        self, current_readme: str, changes: Dict, diff: str
    ) -> str:
        """Build prompt for README update.

        Args:
            current_readme: Current README content
            changes: Extracted changes
            diff: Git diff (truncated)

        Returns:
            Formatted prompt
        """
        # Truncate diff if too long
        if len(diff) > 6000:
            diff = diff[:6000] + "\n[... truncated ...]\n"

        changes_text = f"""
**Changes Detected:**
- New Files: {', '.join(changes['new_files']) if changes['new_files'] else 'None'}
- Modified Files: {', '.join(changes['modified_files'][:5]) if changes['modified_files'] else 'None'}
- New Functions: {', '.join(changes['new_functions'][:10]) if changes['new_functions'] else 'None'}
- New Classes: {', '.join(changes['new_classes'][:10]) if changes['new_classes'] else 'None'}
- Dependency Changes: {', '.join(changes['dependencies']) if changes['dependencies'] else 'None'}
- Config Changes: {', '.join(changes['config_changes']) if changes['config_changes'] else 'None'}
"""

        return f"""You are a technical documentation expert. Update the README.md file to reflect recent code changes.

**Current README.md:**
```markdown
{current_readme}
```

{changes_text}

**Git Diff (Sample):**
```diff
{diff}
```

**Instructions:**
1. Analyze the changes and determine what sections of the README need updates
2. Update or add sections for:
   - New features or modules (if new files/classes added)
   - API changes (if function signatures changed)
   - Installation/setup (if dependencies changed)
   - Configuration (if config files changed)
3. Maintain the existing README structure and tone
4. Keep descriptions clear, concise, and user-friendly
5. Add code examples for new functions/classes if appropriate
6. Update version numbers or changelog if present

**Important:**
- Only update sections that are affected by the changes
- Preserve all existing content that is still relevant
- Do NOT remove or modify unrelated sections
- Return the COMPLETE updated README (not just the changes)
- Use proper markdown formatting

**Output:**
Provide the complete updated README.md content:
"""

    def _clean_readme_output(self, readme: str) -> str:
        """Clean up LLM output to extract pure README content.

        Args:
            readme: Raw LLM output

        Returns:
            Cleaned README content
        """
        # Remove markdown code block wrappers if present
        readme = re.sub(r'^```markdown\s*\n', '', readme, flags=re.MULTILINE)
        readme = re.sub(r'^```\s*\n', '', readme, flags=re.MULTILINE)
        readme = re.sub(r'\n```\s*$', '', readme, flags=re.MULTILINE)
        
        # Remove any leading/trailing whitespace
        readme = readme.strip()
        
        return readme
