# Simple unified diff
import difflib

def generate_diff(original: str, modified: str, filename: str) -> str:
    """Generate unified diff"""
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}"
    )
    return ''.join(diff)