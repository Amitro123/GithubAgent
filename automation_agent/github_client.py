"""GitHub API client wrapper for automation operations."""

import logging
from typing import Optional, Dict, Any, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub API client with retry logic and error handling."""

    def __init__(self, token: str, owner: str, repo: str):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token
            owner: Repository owner
            repo: Repository name
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_url = "https://api.github.com"
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        })
        return session

    def get_commit_diff(self, commit_sha: str) -> Optional[str]:
        """Get the diff for a specific commit.

        Args:
            commit_sha: Commit SHA to fetch diff for

        Returns:
            Diff content as string, or None if error
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/commits/{commit_sha}"
        try:
            response = self.session.get(url, headers={"Accept": "application/vnd.github.v3.diff"})
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch commit diff: {e}")
            return None

    def get_commit_info(self, commit_sha: str) -> Optional[Dict[str, Any]]:
        """Get commit information.

        Args:
            commit_sha: Commit SHA

        Returns:
            Commit data dictionary or None
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/commits/{commit_sha}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch commit info: {e}")
            return None

    def post_commit_comment(self, commit_sha: str, body: str) -> bool:
        """Post a comment on a commit.

        Args:
            commit_sha: Commit SHA to comment on
            body: Comment body text

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/commits/{commit_sha}/comments"
        try:
            response = self.session.post(url, json={"body": body})
            response.raise_for_status()
            logger.info(f"Posted comment on commit {commit_sha}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to post commit comment: {e}")
            return False

    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> Optional[int]:
        """Create a GitHub issue.

        Args:
            title: Issue title
            body: Issue body
            labels: Optional list of label names

        Returns:
            Issue number if successful, None otherwise
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues"
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels

        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            issue_number = response.json()["number"]
            logger.info(f"Created issue #{issue_number}")
            return issue_number
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create issue: {e}")
            return None

    def get_file_content(self, file_path: str, ref: str = "main") -> Optional[str]:
        """Get content of a file from the repository.

        Args:
            file_path: Path to file in repository
            ref: Git reference (branch, tag, or commit SHA)

        Returns:
            File content as string, or None if not found
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/contents/{file_path}"
        try:
            response = self.session.get(url, params={"ref": ref})
            if response.status_code == 404:
                return None
            response.raise_for_status()
            import base64
            content = response.json()["content"]
            return base64.b64decode(content).decode("utf-8")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch file content: {e}")
            return None

    def update_file(self, file_path: str, content: str, message: str, branch: str = "main") -> bool:
        """Update or create a file in the repository.

        Args:
            file_path: Path to file in repository
            content: New file content
            message: Commit message
            branch: Branch to commit to

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/contents/{file_path}"
        import base64

        # Get current file SHA if it exists
        sha = None
        try:
            response = self.session.get(url, params={"ref": branch})
            if response.status_code == 200:
                sha = response.json()["sha"]
        except requests.exceptions.RequestException:
            pass

        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        try:
            response = self.session.put(url, json=payload)
            response.raise_for_status()
            logger.info(f"Updated file {file_path} on branch {branch}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update file: {e}")
            return False

    def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        """Create a new branch.

        Args:
            branch_name: Name for the new branch
            from_branch: Source branch to branch from

        Returns:
            True if successful, False otherwise
        """
        # Get SHA of source branch
        ref_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/git/ref/heads/{from_branch}"
        try:
            response = self.session.get(ref_url)
            response.raise_for_status()
            sha = response.json()["object"]["sha"]

            # Create new branch
            create_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/git/refs"
            payload = {"ref": f"refs/heads/{branch_name}", "sha": sha}
            response = self.session.post(create_url, json=payload)
            response.raise_for_status()
            logger.info(f"Created branch {branch_name}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create branch: {e}")
            return False

    def create_pull_request(
        self, title: str, body: str, head: str, base: str = "main"
    ) -> Optional[int]:
        """Create a pull request.

        Args:
            title: PR title
            body: PR body
            head: Branch containing changes
            base: Branch to merge into

        Returns:
            PR number if successful, None otherwise
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/pulls"
        payload = {"title": title, "body": body, "head": head, "base": base}

        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            pr_number = response.json()["number"]
            logger.info(f"Created PR #{pr_number}")
            return pr_number
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create pull request: {e}")
            return None

    def get_recent_commits(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent commits from the repository.

        Args:
            limit: Maximum number of commits to fetch

        Returns:
            List of commit dictionaries
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/commits"
        try:
            response = self.session.get(url, params={"per_page": limit})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch recent commits: {e}")
            return []
