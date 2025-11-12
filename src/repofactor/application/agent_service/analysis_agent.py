# src/repofactor/application/agent_service/analysis_agent.py
"""
Code Analysis Agent - using Lightning AI directly with TOON format
"""

import logging
from typing import Dict, Any, Optional, List
import json
import re

from pydantic import BaseModel, Field

from repofactor.domain.prompts.prompt_agent_analyze import (
    PROMPT_REPO_ANALYSIS_TOON,
    PROMPT_REPO_ANALYSIS,
)
from repofactor.application.services.lightning_ai_service import LightningAIClient

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models (for validation)
# ============================================================================

class AffectedFileSchema(BaseModel):
    """Schema for a single affected file"""
    path: str = Field(description="Relative file path in target project")
    reason: str = Field(description="Why this file needs changes")
    confidence: int = Field(ge=0, le=100, description="Confidence score 0-100")
    changes: List[str] = Field(description="List of specific changes needed")


class RepositoryAnalysisSchema(BaseModel):
    """Complete repository analysis output"""
    main_modules: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    affected_files: List[AffectedFileSchema] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    implementation_steps: List[str] = Field(default_factory=list)


# ============================================================================
# Analysis Agent
# ============================================================================

class CodeAnalysisAgent:
    """
    Agent using Lightning AI directly with TOON format (30-60% fewer tokens).
    Robust JSON parsing with comprehensive error handling.
    """
    
    def __init__(
        self,
        model: str = "google/gemini-2.5-flash-lite-preview-06-17"
    ):
        """Initialize with Lightning AI client."""
        self.client = LightningAIClient(model=model)
        self.model = model
        
        logger.info(f"✅ CodeAnalysisAgent: Lightning AI with TOON format")
        logger.info(f"   Model: {model}")
    
    async def analyze_repository(
        self,
        repo_content: Dict[str, str],
        target_context: Optional[str] = None,
        user_instructions: str = ""
    ) -> Dict[str, Any]:
        """Analyze repository and return structured results."""
        
        # Generate TOON-formatted prompt (compact!)
        prompt_toon = PROMPT_REPO_ANALYSIS_TOON(
            instructions=user_instructions,
            relevant_files=repo_content,
            target_context=target_context
        )

        # Generate standard JSON prompt as a fallback
        prompt_json = PROMPT_REPO_ANALYSIS(
            instructions=user_instructions,
            relevant_files=repo_content,
            target_context=target_context
        )
        
        # Enhanced logging
        logger.info(f"📊 Prompt stats:")
        logger.info(f"   Length: {len(prompt_toon)} chars (~{len(prompt_toon)//4} tokens)")
        logger.info(f"   Files: {len(repo_content)}")
        logger.info(f"   Format: TOON (compact, 30-60% fewer tokens)")
        logger.debug(f"Prompt preview: {prompt_toon[:300]}...")
        
        try:
            # Call Lightning AI with fallback
            logger.info("🔄 Calling Lightning AI...")
            
            response = await self.client.generate(
                prompt=prompt_toon,
                prompt_fallback=prompt_json,
                max_tokens=3000,
                temperature=0.1
            )
            
            # Comprehensive response validation
            logger.info(f"✅ Response received")
            logger.info(f"   Type: {type(response)}")
            logger.info(f"   Text length: {len(response.text) if response.text else 0} chars")
            
            if not response.text or not response.text.strip():
                logger.error("❌ Empty response from Lightning AI!")
                logger.error(f"   TOON prompt length: {len(prompt_toon)} chars")
                logger.error(f"   Fallback JSON prompt length: {len(prompt_json)} chars")
                logger.error(f"   Files: {len(repo_content)}")
                
                # Log first file for debugging
                if repo_content:
                    first_file = next(iter(repo_content.keys()))
                    logger.error(f"   First file: {first_file} ({len(repo_content[first_file])} chars)")
                
                raise ValueError("Empty response from Lightning AI - prompt may be too long")
            
            logger.debug(f"Response preview: {response.text[:500]}...")
            
            # Parse with robust logic
            parsed = self._parse_llm_response(response.text)
            
            # Validate with Pydantic
            validated = RepositoryAnalysisSchema(**parsed)
            
            result = validated.model_dump()
            
            # Add raw response for debugging
            result['raw_llm_response'] = response.text
            
            logger.info(
                f"✅ Analysis complete: {len(result['affected_files'])} files, "
                f"{len(result['dependencies'])} deps, "
                f"{len(result['risks'])} risks"
            )
            
            return result
            
        except ValueError as e:
            # Empty response error
            logger.error(f"Analysis failed: {e}")
            raise RuntimeError(f"Repository analysis failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise RuntimeError(f"Repository analysis failed: {str(e)}")
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Robust JSON parsing with multiple strategies.
        
        Tries:
        1. Direct JSON parse
        2. Extract from markdown code blocks
        3. Find JSON object in text
        """
        
        default = {
            "main_modules": [],
            "dependencies": [],
            "affected_files": [],
            "risks": ["Failed to parse LLM response"],
            "implementation_steps": []
        }
        
        if not response_text or not response_text.strip():
            logger.error("Empty LLM response")
            return default
        
        # Strategy 1: Direct JSON parse
        try:
            result = json.loads(response_text.strip())
            logger.info("✅ Parsed JSON directly")
            return self._fill_defaults(result)
        except json.JSONDecodeError:
            logger.debug("Not direct JSON")
        
        # Strategy 2: Extract from markdown code block
        match = re.search(r'``````', response_text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
                logger.info("✅ Extracted JSON from markdown block")
                return self._fill_defaults(result)
            except json.JSONDecodeError:
                logger.debug("Markdown block not valid JSON")
        
        # Strategy 3: Find any JSON object in text
        matches = list(re.finditer(
            r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}',
            response_text,
            re.DOTALL
        ))
        
        # Sort by length (longest first) - likely to be the main object
        matches.sort(key=lambda m: len(m.group(0)), reverse=True)
        
        for match in matches:
            try:
                result = json.loads(match.group(0))
                # Check if it looks like our expected structure
                if any(k in result for k in ["affected_files", "dependencies", "main_modules"]):
                    logger.info("✅ Extracted JSON from text")
                    return self._fill_defaults(result)
            except json.JSONDecodeError:
                continue
        
        logger.warning("⚠️ Could not parse JSON, returning default structure")
        logger.warning(f"Response preview: {response_text[:200]}")
        return default
    
    def _fill_defaults(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required fields exist with proper types"""
        
        result = {
            "main_modules": data.get("main_modules", []),
            "dependencies": data.get("dependencies", []),
            "affected_files": [],
            "risks": data.get("risks", []),
            "implementation_steps": data.get("implementation_steps", [])
        }
        
        # Validate and normalize affected_files
        raw_files = data.get("affected_files", [])
        if isinstance(raw_files, list):
            for file_info in raw_files:
                if isinstance(file_info, dict) and "path" in file_info:
                    result["affected_files"].append({
                        "path": str(file_info.get("path", "")),
                        "reason": str(file_info.get("reason", "")),
                        "confidence": int(file_info.get("confidence", 50)),
                        "changes": file_info.get("changes", [])
                    })
        
        return result
    
    async def close(self):
        """Cleanup resources"""
        await self.client.close()
