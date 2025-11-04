"""Analysis result domain model."""

from pydantic import BaseModel
from typing import Optional, List
from .file_analysis import FileAnalysis


class AnalysisResult(BaseModel):
    """Represents the complete analysis result of a repository."""
    
    main_file: str
    affected_files: List[FileAnalysis]
    dependencies: List[str]
    estimated_changes: str
    risks: List[str]
    diff_preview: Optional[str] = None
