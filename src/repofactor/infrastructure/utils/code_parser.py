import ast
import re
import logging
from typing import List, Optional

from repofactor.domain.models.integration_models import Solution

logger = logging.getLogger(__name__)


def extract_imports(code: str) -> List[str]:
    """Extract all imports from Python code"""
    tree = ast.parse(code)
    imports = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    
    return imports

def parse_grounded_response(response) -> List[Solution]:
    solutions = []
    try:
        if hasattr(response, 'grounding_metadata'):
            metadata = response.grounding_metadata
            if hasattr(metadata, 'grounding_chunks'):
                for chunk in metadata.grounding_chunks:
                    if hasattr(chunk, 'web'):
                        web_info = chunk.web
                        solution = Solution(
                            source=classify_source(web_info.uri),
                            url=web_info.uri,
                            title=getattr(web_info, 'title', "Untitled"),
                            description=getattr(chunk, 'text', ""),
                            code_snippet=extract_code_from_text(getattr(chunk, 'text', "")),
                            confidence=calculate_confidence(chunk),
                            search_query="grounded search"
                        )
                        solutions.append(solution)

            if hasattr(metadata, 'grounding_supports'):
                for support in metadata.grounding_supports:
                    if hasattr(support, 'source'):
                        source_info = support.source
                        if hasattr(source_info, 'uri'):
                            solution = Solution(
                                source=classify_source(source_info.uri),
                                url=source_info.uri,
                                title=getattr(source_info, 'title', 'Solution'),
                                description=getattr(support, 'text', ""),
                                code_snippet=None,
                                confidence=0.7,
                                search_query="support"
                            )
                            solutions.append(solution)

        if not solutions:
            solutions = parse_solutions_from_text(response.text)
    except Exception as e:
        logger.warning(f"Failed to parse grounding metadata: {e}")
        solutions = parse_solutions_from_text(response.text)
    return solutions

def classify_source(url: str) -> str:
    url_lower = url.lower()
    if 'github.com' in url_lower:
        return 'github'
    elif 'stackoverflow.com' in url_lower:
        return 'stackoverflow'
    elif 'reddit.com' in url_lower:
        return 'reddit'
    elif any(term in url_lower for term in ['docs', 'documentation', 'readthedocs']):
        return 'docs'
    else:
        return 'web'

def extract_code_from_text(text: str) -> Optional[str]:
    """Extract first fenced code block from markdown-like text."""
    code_pattern = r"```(?:[a-zA-Z0-9_+-]+)?\n(.*?)```"
    matches = re.findall(code_pattern, text, re.DOTALL)
    if matches:
        return matches[0].strip()
    return None

def calculate_confidence(chunk) -> float:
    confidence = 0.5
    if hasattr(chunk, 'web') and chunk.web.uri:
        uri = chunk.web.uri.lower()
        if 'github.com' in uri and '/issues/' in uri:
            confidence = 0.9
        elif 'stackoverflow.com' in uri:
            confidence = 0.85
        elif 'reddit.com' in uri:
            confidence = 0.7
    return confidence

def parse_solutions_from_text(text: str) -> List[Solution]:
    # Fallback parsing: collect URLs as generic web solutions.
    solutions: List[Solution] = []
    url_pattern = r"https?://[^\s)]+"
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        solutions.append(
            Solution(
                source=classify_source(url),
                url=url,
                title="Candidate solution",
                description="Automatically extracted from text response.",
                code_snippet=None,
                confidence=0.6,
                search_query="text fallback",
            )
        )
    return solutions

def extract_search_queries(response) -> List[str]:
    """Heuristically extract search queries mentioned in the Gemini response text."""
    queries: List[str] = []
    text = getattr(response, "text", None)
    if callable(text):
        text = text()
    if text is None:
        text = str(response)

    patterns = [
        r"[Qq]uery:\s*(.+)",
        r"[Ss]earch query:\s*(.+)",
        r"#\s*Search:\s*(.+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            q = match.group(1).strip().rstrip("`*_-")
            if q and q not in queries:
                queries.append(q)
    return queries
