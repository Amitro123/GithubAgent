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
    
    # ✨ IMPROVED: Much stronger JSON enforcement
    prompt += """

CRITICAL INSTRUCTIONS:
- You MUST respond with ONLY a valid JSON object
- NO explanations before or after the JSON
- NO markdown code blocks (no ```json```)
- NO additional text
- Your ENTIRE response must be parseable as JSON

REQUIRED JSON STRUCTURE:
{
  "main_modules": ["core module names from source repo"],
  "dependencies": ["pip package names like 'fastapi', 'pydantic>=2.0'"],
  "affected_files": [
    {
      "path": "relative/path/in/target/project.py",
      "reason": "clear explanation of why this file needs changes",
      "confidence": 85,
      "changes": ["specific change description 1", "specific change 2"]
    }
  ],
  "risks": ["potential issue 1", "potential issue 2"],
  "implementation_steps": ["1. First actionable step", "2. Second step"]
}

EXAMPLE for integrating FastAPI into a project:
{
  "main_modules": ["fastapi.routing", "fastapi.applications", "fastapi.params"],
  "dependencies": ["fastapi>=0.100.0", "pydantic>=2.0", "uvicorn"],
  "affected_files": [
    {
      "path": "src/main.py",
      "reason": "Need to initialize FastAPI application and define routes",
      "confidence": 95,
      "changes": [
        "Import FastAPI from fastapi",
        "Create app = FastAPI() instance",
        "Add @app.get() route decorators",
        "Add uvicorn.run() in main block"
      ]
    },
    {
      "path": "src/models.py",
      "reason": "Define Pydantic models for request/response validation",
      "confidence": 90,
      "changes": [
        "Import BaseModel from pydantic",
        "Create model classes inheriting from BaseModel"
      ]
    }
  ],
  "risks": [
    "Ensure existing code is async-compatible",
    "Check for port conflicts if running server"
  ],
  "implementation_steps": [
    "1. Install dependencies: pip install fastapi uvicorn pydantic",
    "2. Modify src/main.py to create FastAPI app instance",
    "3. Create src/models.py with Pydantic models",
    "4. Test with: uvicorn src.main:app --reload"
  ]
}

NOW ANALYZE THE REPOSITORY AND RESPOND WITH VALID JSON ONLY:"""
    
    return prompt
