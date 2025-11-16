from dataclasses import dataclass
from typing import List
from repofactor.application.services.repo_integrator_service import ResearchResult


class ResearchRequest:
    failed_file: str
    error_message: str
    attempted_solution: str
    context: str


class ResearchResult:
    solutions_found: List[Solution]
    examples: List[CodeExample]
    recommendations: List[str]
   
class Solution:
    source: str  # "github", "stackoverflow", "reddit"
    url: str
    description: str
    code_snippet: str
    confidence: float


