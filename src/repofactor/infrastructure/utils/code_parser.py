# Simple AST-based parser
import ast
from typing import List, Dict

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
