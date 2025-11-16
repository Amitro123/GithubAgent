# src/repofactor/application/agent_service/diff_agent.py

from typing import List
import difflib

class FileDiff:
    def __init__(self, path: str, diff_text: str, change_summary: List[str]):
        self.path = path
        self.diff_text = diff_text
        self.change_summary = change_summary

class DiffResult:
    def __init__(self, files_changed: int, lines_added: int, lines_removed: int,
                 file_diffs: List[FileDiff], summary: str):
        self.files_changed = files_changed
        self.lines_added = lines_added
        self.lines_removed = lines_removed
        self.file_diffs = file_diffs
        self.summary = summary

class DiffAgent:
    """
    Agent that computes diffs between two sets of files.
    """
    def __init__(self):
        # any setup here
        pass

    def generate_diff(self, base_files: dict, modified_files: dict) -> DiffResult:
        file_diffs = []
        files_changed = 0
        lines_added = 0
        lines_removed = 0

        all_files = set(base_files.keys()) | set(modified_files.keys())
        for path in all_files:
            original = base_files.get(path, "").splitlines()
            modified = modified_files.get(path, "").splitlines()
            if original != modified:
                diff = list(difflib.unified_diff(
                    original, modified,
                    fromfile=f"base/{path}",
                    tofile=f"mod/{path}",
                    lineterm=""
                ))
                added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
                removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
                summary = []
                if not original: summary.append("File Added")
                elif not modified: summary.append("File Removed")
                else: summary.append(f"Lines Changed: {len(diff)}")
                file_diffs.append(FileDiff(path, "\n".join(diff), summary))
                files_changed += 1
                lines_added += added
                lines_removed += removed

        summary = f"{files_changed} files changed, {lines_added} lines added, {lines_removed} lines removed"
        return DiffResult(files_changed, lines_added, lines_removed, file_diffs, summary)

