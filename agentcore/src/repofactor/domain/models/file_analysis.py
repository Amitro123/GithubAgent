"""File analysis domain model."""

from pydantic import BaseModel


class FileAnalysis(BaseModel):
    """Represents analysis of a single file that needs modification."""
    
    path: str
    reason: str
    confidence: int
    status: str = "pending"
