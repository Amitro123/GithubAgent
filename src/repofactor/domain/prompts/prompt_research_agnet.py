from typing import List, Dict

from repofactor.domain.models.integration_models import Solution


def build_research_prompt(error_message: str, failed_code: str, context: Dict) -> str:
    repo = context.get("repo", "unknown")
    task = context.get("user_instructions", "integrate code")
    studio_logs = context.get("studio_logs") or []
    logs_snippet = ""
    if studio_logs:
        truncated = studio_logs[-10:]
        joined = "\n".join(truncated)
        logs_snippet = f"\n## StudioAI / Execution Logs (last {len(truncated)} lines)\n{joined}\n"

    return f"""You are a research agent helping debug a code integration issue.

## Problem Context
- **Repository**: {repo}
- **Task**: {task}
- **Error**: {error_message}

## Failed Code
```python
{failed_code}
```
{logs_snippet}
## Your Mission

1. Analyze the error, failed code, and logs.
2. Search the web (GitHub, StackOverflow, docs, etc.) for similar issues.
3. Propose concrete, minimal fixes and code snippets.

Format your answer with sections:
- Summary
- Root Cause
- Suggested Fixes
- Code Snippets
- Search Queries Used
"""


def generate_recommendations(
    solutions: List[Solution],
    error_message: str,
    context: Dict,
) -> List[str]:
    """Generate short, human-readable recommendations from Solution objects."""
    if not solutions:
        return [
            "No concrete solutions were found automatically.",
            f"Try searching manually for the error: {error_message}",
        ]

    recs: List[str] = []
    for sol in solutions[:5]:
        title = sol.title or sol.source
        recs.append(
            f"Review solution '{title}' from {sol.source} ({sol.url}) and adapt it to the failing code."
        )

    recs.append(
        "Apply the highest-confidence solution and rerun tests to verify the integration is fixed."
    )
    return recs
