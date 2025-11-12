from repofactor.utils.toon_encoder import encode_analysis_context_toon


PROMPT_DEFINITION_AGENT_ANALYZE = """You are an expert code integration assistant. Analyze this repository and provide integration recommendations."""


def PROMPT_AGENT_ANALYZE(original_code: str, change_instructions: str, context: str = None) -> str:
    """Generate prompt for code modification with LLM"""
    context_section = f'\nCONTEXT: {context}' if context else ''
    
    return f"""You are an expert Python developer. Modify the following code according to the instructions.

ORIGINAL CODE:
{original_code}

INSTRUCTIONS:
{change_instructions}
{context_section}

Provide the complete modified code. Include:
- Type hints
- Docstrings
- Error handling
- Clean, pythonic style

MODIFIED CODE:"""


def PROMPT_REPO_ANALYSIS(instructions: str, relevant_files: dict, target_context: str = None) -> str:
    """Generate prompt for repository analysis with structured JSON output (standard JSON format)"""
    
    prompt = f"""You are an expert code integration assistant. Analyze this repository and provide integration recommendations.

USER INSTRUCTIONS:
{instructions}

SOURCE REPOSITORY FILES:
"""
    
    for filepath, content in relevant_files.items():
        # Truncate large files
        truncated = content[:400] if len(content) > 400 else content
        prompt += f"\n--- {filepath} ---\n{truncated}\n"
    
    if target_context:
        prompt += f"\nTARGET PROJECT CONTEXT:\n{target_context}\n"
    
    prompt += """
CRITICAL INSTRUCTIONS:

You MUST respond with ONLY a valid JSON object

NO explanations before or after the JSON

NO markdown code blocks (no ```json)

NO additional text

Your ENTIRE response must be parseable as JSON

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

NOW ANALYZE THE REPOSITORY AND RESPOND WITH VALID JSON ONLY:"""
    
    return prompt


def PROMPT_REPO_ANALYSIS_TOON(
    instructions: str,
    relevant_files: dict,
    target_context: str = None
) -> str:
    """
    Generate ULTRA-COMPACT prompt using TOON format.
    Optimized for Lightning AI's token limits.
    """
    
    # ✅ Encode to TOON with AGGRESSIVE truncation
    toon_context = encode_analysis_context_toon(
        files=relevant_files,
        instructions=instructions,
        target_context=None,
        max_file_length=400
    )
    
    # ✅ SHORTER prompt template
    prompt = f"""Analyze this code repository.

CONTEXT:
{toon_context}

Respond with ONLY valid JSON (no markdown, no explanations):
{{
  "dependencies": ["package"],
  "affected_files": [{{"path": "file.py", "reason": "why", "confidence": 80, "changes": ["what"]}}],
  "risks": ["risk"],
  "steps": ["step 1"]
}}

JSON:"""
    
    return prompt
