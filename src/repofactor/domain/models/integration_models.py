# domain/models/integration_models.py
"""
Data models for integration flow
Unified models that work for both simple and multi-agent approaches
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum


class ChangeType(Enum):
    """Type of change to make"""
    MODIFY = "modify"
    CREATE = "create"
    DELETE = "delete"


@dataclass
class AffectedFile:
    """Detailed file information"""
    path: str
    reason: str
    change_type: ChangeType
    confidence: float
    dependencies: List[str] = field(default_factory=list)
    changes_needed: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dict for serialization"""
        data = asdict(self)
        data['change_type'] = self.change_type.value
        return data


@dataclass
class AnalysisResult:
    """Complete analysis result - works for both simple and multi-agent"""
    
    # Basic info
    repo_url: str
    repo_name: str
    
    # Files (enhanced format)
    affected_files: List[AffectedFile]
    
    # Dependencies
    dependencies: List[str]
    dependency_graph: Optional[Dict[str, List[str]]] = None
    imports_to_add: List[str] = field(default_factory=list)
    
    # Risk & Planning
    risks: List[str] = field(default_factory=list)
    estimated_time: str = "10-30 minutes"
    implementation_steps: List[str] = field(default_factory=list)
    
    # Metadata
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    internal_logs: List[str] = field(default_factory=list)
    raw_llm_response: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization"""
        return {
            "repo_url": self.repo_url,
            "repo_name": self.repo_name,
            "affected_files": [f.to_dict() for f in self.affected_files],
            "dependencies": self.dependencies,
            "dependency_graph": self.dependency_graph,
            "imports_to_add": self.imports_to_add,
            "risks": self.risks,
            "estimated_time": self.estimated_time,
            "implementation_steps": self.implementation_steps,
            "confidence_scores": self.confidence_scores
        }
    
    @property
    def file_count(self) -> int:
        """Number of files to modify"""
        return len(self.affected_files)
    
    @property
    def high_confidence_files(self) -> List[AffectedFile]:
        """Files with >80% confidence"""
        return [f for f in self.affected_files if f.confidence > 0.8]
    
    @classmethod
    def from_dict(cls, data: Dict, repo_url: str = "", repo_name: str = "") -> 'AnalysisResult':
        """Create AnalysisResult from dict (for backwards compatibility)"""
        return parse_llm_response_to_analysis(data, repo_url, repo_name)


# ============================================================================
# Helper Functions for Conversion
# ============================================================================

def dict_to_affected_file(data: Dict) -> AffectedFile:
    """
    Convert dict from LLM to AffectedFile
    
    Args:
        data: Dict with keys: path, reason, change_type, confidence, etc.
        
    Returns:
        AffectedFile instance
        
    Example:
        >>> data = {
        ...     "path": "main.py",
        ...     "reason": "Add logging",
        ...     "confidence": 0.9
        ... }
        >>> file = dict_to_affected_file(data)
        >>> print(file.path)
        "main.py"
    """
    # Handle change_type conversion
    change_type_value = data.get("change_type", "modify")
    if isinstance(change_type_value, str):
        try:
            change_type = ChangeType(change_type_value)
        except ValueError:
            change_type = ChangeType.MODIFY
    else:
        change_type = change_type_value
    
    return AffectedFile(
        path=data.get("path", "unknown"),
        reason=data.get("reason", ""),
        change_type=change_type,
        confidence=float(data.get("confidence", 0.5)),
        dependencies=data.get("dependencies", []),
        changes_needed=data.get("changes", data.get("changes_needed", []))
    )


def parse_llm_response_to_analysis(
    llm_response: Dict,
    repo_url: str,
    repo_name: str
) -> AnalysisResult:
    """
    Parse LLM response into AnalysisResult
    
    Handles various formats from different LLM responses
    
    Args:
        llm_response: Raw dict from LLM
        repo_url: Repository URL
        repo_name: Repository name
        
    Returns:
        Properly structured AnalysisResult
        
    Example:
        >>> response = {
        ...     "affected_files": [
        ...         {"path": "main.py", "reason": "test", "confidence": 0.9}
        ...     ],
        ...     "dependencies": ["fastapi"],
        ...     "risks": ["API changes"]
        ... }
        >>> result = parse_llm_response_to_analysis(response, "url", "name")
        >>> print(result.file_count)
        1
    """
    
    # Parse affected files
    affected_files_data = llm_response.get("affected_files", [])
    affected_files = []
    
    for file_data in affected_files_data:
        try:
            affected_file = dict_to_affected_file(file_data)
            affected_files.append(affected_file)
        except Exception as e:
            print(f"Warning: Failed to parse file {file_data.get('path', 'unknown')}: {e}")
            continue
    
    return AnalysisResult(
        repo_url=repo_url,
        repo_name=repo_name,
        affected_files=affected_files,
        dependencies=llm_response.get("dependencies", []),
        dependency_graph=llm_response.get("dependency_graph"),
        imports_to_add=llm_response.get("imports_to_add", []),
        risks=llm_response.get("risks", []),
        estimated_time=llm_response.get("estimated_time", "10-30 minutes"),
        implementation_steps=llm_response.get("implementation_steps", []),
        confidence_scores=llm_response.get("confidence_scores", {}),
        internal_logs=llm_response.get("internal_logs", []),
        raw_llm_response=str(llm_response)
    )


def create_empty_analysis(repo_url: str, repo_name: str, reason: str = "No analysis performed") -> AnalysisResult:
    """
    Create an empty AnalysisResult (for error cases)
    
    Args:
        repo_url: Repository URL
        repo_name: Repository name
        reason: Reason for empty result
        
    Returns:
        Empty AnalysisResult
    """
    return AnalysisResult(
        repo_url=repo_url,
        repo_name=repo_name,
        affected_files=[],
        dependencies=[],
        risks=[reason],
        estimated_time="N/A",
        implementation_steps=[]
    )



@dataclass
class ModifiedFile:
    path: str
    original_content: str
    modified_content: str
    backup_path: Optional[str] = None
    changes_made: List[str] = field(default_factory=list)

@dataclass
class Error:
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None

@dataclass
class ImplementationResult:
    success: bool
    modified_files: List[ModifiedFile] = field(default_factory=list)
    errors: List[Error] = field(default_factory=list)
    execution_logs: List[str] = field(default_factory=list)


# ============================================================================
# Type Aliases for Backwards Compatibility
# ============================================================================

# For code that still uses Dict[str, Any] format
LegacyAffectedFile = Dict[str, Any]
LegacyAnalysisResult = Dict[str, Any]


def to_legacy_format(result: AnalysisResult) -> LegacyAnalysisResult:
    """Convert AnalysisResult to legacy dict format"""
    return result.to_dict()


def from_legacy_format(data: LegacyAnalysisResult) -> AnalysisResult:
    """Convert legacy dict format to AnalysisResult"""
    return parse_llm_response_to_analysis(
        data,
        data.get("repo_url", ""),
        data.get("repo_name", "")
    )