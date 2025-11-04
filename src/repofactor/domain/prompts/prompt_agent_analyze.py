PROMPT_DEFINITION_AGENT_ANALYZE = """You are an expert code integration assistant. Analyze this repository and provide integration recommendations."""

def PROMPT_AGENT_ANALYZE(original_code: str, change_instructions: str, context: str = None) -> str:
    """Generate prompt for code modification with LLM"""
    context_section = f'\nCONTEXT: {context}' if context else ''
    
    return f"""You are an expert Python developer. Modify the following code according to the instructions.

ORIGINAL CODE:
```python
{original_code}
```

INSTRUCTIONS:
{change_instructions}
{context_section}

Provide the complete modified code. Include:
- Type hints
- Docstrings
- Error handling
- Clean, pythonic style

MODIFIED CODE:
```python"""

def PROMPT_REPO_ANALYSIS(instructions: str, relevant_files: dict, target_context: str = None) -> str:
    """Generate prompt for repository analysis with structured JSON output"""
    
    prompt = f"""You are an expert code integration assistant. Analyze this repository and provide integration recommendations.

USER INSTRUCTIONS:
{instructions}

SOURCE REPOSITORY FILES:
"""
    
    for filepath, content in relevant_files.items():
        # Truncate large files
        truncated = content[:2000] if len(content) > 2000 else content
        prompt += f"\n--- {filepath} ---\n{truncated}\n"
    
    if target_context:
        prompt += f"\nTARGET PROJECT CONTEXT:\n{target_context}\n"
    
    prompt += """
Provide a structured analysis in JSON format:
{
  "main_modules": ["list of key modules"],
  "dependencies": ["required packages"],
  "affected_files": [
    {
      "path": "file path",
      "reason": "why this file needs changes",
      "confidence": 85,
      "changes": ["specific changes needed"]
    }
  ],
  "risks": ["potential issues"],
  "implementation_steps": ["ordered steps"]
}

Focus on practical, actionable recommendations."""
    
    return prompt

