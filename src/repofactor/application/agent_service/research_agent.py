import os
import asyncio
import logging
from typing import Optional, Dict, Tuple

import google.generativeai as genai

from repofactor.domain.models.integration_models import ResearchResult, Solution
from repofactor.infrastructure.utils.code_parser import (
    parse_grounded_response,
    extract_search_queries,
)
from repofactor.domain.prompts.prompt_research_agnet import (
    build_research_prompt,
    generate_recommendations,
)


logger = logging.getLogger(__name__)


class GeminiResearchAgent:
    """Low-level Gemini integration used by the higher-level ResearchAgent.

    The Gemini client is configured lazily so that simply constructing
    services/orchestrators in tests does not require GEMINI_API_KEY to be set.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-exp") -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._model: Optional[genai.GenerativeModel] = None

    def _ensure_client(self) -> None:
        """Configure Gemini client on first use.

        Raises:
            ValueError: if GEMINI_API_KEY is not available when research is invoked.
        """
        if self._model is not None:
            return
        api_key = self._api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=self._model_name,
            tools="google_search_retrieval",
        )
        logger.info("Initialized Gemini Research Agent with %s", self._model_name)

    async def research_implementation_failure(
        self,
        error_message: str,
        failed_code: str,
        context: Dict[str, str],
    ) -> ResearchResult:
        logger.info("Researching solution for error: %s", error_message[:100])
        self._ensure_client()
        prompt = build_research_prompt(error_message, failed_code, context)
        try:
            response = await asyncio.to_thread(
                self._model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    top_p=0.8,
                    max_output_tokens=2048,
                ),
            )
            solutions: list[Solution] = parse_grounded_response(response)
            search_queries = extract_search_queries(response)
            recommendations = generate_recommendations(solutions, error_message, context)

            result = ResearchResult(
                solutions_found=solutions,
                recommendations=recommendations,
                search_queries_used=search_queries,
                total_sources=len(solutions),
            )
            logger.info("Research complete: %d solutions found", len(solutions))
            return result
        except Exception as e:
            logger.error("Research failed: %s", e)
            return ResearchResult(
                solutions_found=[],
                recommendations=[
                    "Could not find specific solutions",
                    f"Try searching manually: {error_message}",
                ],
                search_queries_used=[],
                total_sources=0,
            )


class ResearchAgent:
    """High-level research agent used by the MultiAgentOrchestrator."""

    def __init__(self, gemini_agent: Optional[GeminiResearchAgent] = None) -> None:
        self._gemini = gemini_agent or GeminiResearchAgent()

    async def find_solution(
        self,
        error_message: str,
        failed_code: str,
        context: Dict[str, str],
    ) -> ResearchResult:
        """Run research and return a structured ResearchResult."""
        return await self._gemini.research_implementation_failure(
            error_message=error_message,
            failed_code=failed_code,
            context=context,
        )

    async def best_fix_snippet(
        self,
        error_message: str,
        failed_code: str,
        context: Dict[str, str],
    ) -> Tuple[Optional[str], ResearchResult]:
        """Return the best code snippet (if any) along with the full ResearchResult."""
        result = await self.find_solution(error_message, failed_code, context)
        if not result.solutions_found:
            return None, result
        best = max(result.solutions_found, key=lambda s: s.confidence)
        snippet = best.code_snippet or best.description
        return snippet, result


async def research_and_retry(
    error_message: str,
    failed_code: str,
    context: Dict,
    max_retries: int = 2,
) -> Optional[str]:
    """Convenience helper for standalone usage of the research flow."""
    agent = ResearchAgent()
    result = await agent.find_solution(error_message, failed_code, context)
    if not result.solutions_found:
        logger.warning("No solutions found")
        return None
    best_solution = max(result.solutions_found, key=lambda s: s.confidence)
    logger.info("Best solution from: %s (%.0f%%)", best_solution.source, best_solution.confidence * 100)
    return best_solution.code_snippet or best_solution.description
