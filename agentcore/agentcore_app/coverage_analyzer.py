"""
Universal Coverage Analyzer Module

This module provides comprehensive test coverage analysis for ANY Python project structure.
It integrates with coverage.py to measure coverage, identify gaps, and generate reports.

Key Features:
- Works with any project structure (flat, src/, app/, etc.)
- Identifies uncovered code from git diffs
- Generates standardized reports (JSON, HTML, terminal)
- Calculates coverage deltas (before/after push)
- Supports configurable thresholds per repository
- Handles monorepos and single-project structures
"""

import ast
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import coverage
    from coverage import Coverage
    from coverage.results import Analysis
except ImportError:
    raise ImportError(
        "coverage.py is required. Install with: pip install coverage"
    )


class CoverageFormat(Enum):
    """Supported coverage report formats"""
    JSON = "json"
    HTML = "html"
    TERMINAL = "terminal"
    XML = "xml"


@dataclass
class FunctionCoverage:
    """Coverage data for a single function/method"""
    name: str
    start_line: int
    end_line: int
    covered_lines: int
    total_lines: int
    coverage_percent: float
    missing_lines: List[int] = field(default_factory=list)
    is_covered: bool = False


@dataclass
class FileCoverage:
    """Coverage data for a single file"""
    file_path: str
    total_lines: int
    covered_lines: int
    missing_lines: List[int]
    coverage_percent: float
    functions: List[FunctionCoverage] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)


@dataclass
class CoverageReport:
    """Complete coverage analysis report"""
    total_coverage: float
    files: Dict[str, FileCoverage]
    uncovered_functions: List[Tuple[str, str]]  # (file_path, function_name)
    uncovered_classes: List[Tuple[str, str]]    # (file_path, class_name)
    meets_threshold: bool
    threshold: float
    summary: Dict[str, any]


@dataclass
class CoverageDelta:
    """Coverage changes between two runs"""
    before_coverage: float
    after_coverage: float
    delta: float
    new_covered_lines: int
    new_uncovered_lines: int
    improved_files: List[str]
    regressed_files: List[str]


class CoverageAnalyzer:
    """
    Universal coverage analyzer that works with any Python project structure.
    
    This class provides comprehensive test coverage analysis capabilities:
    - Run coverage on any project layout
    - Identify uncovered code from git diffs
    - Generate multiple report formats
    - Calculate coverage deltas
    - Support configurable thresholds
    """
    
    def __init__(
        self,
        project_root: str,
        source_dirs: Optional[List[str]] = None,
        test_dirs: Optional[List[str]] = None,
        coverage_threshold: float = 80.0,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ):
        """
        Initialize the coverage analyzer.
        
        Args:
            project_root: Root directory of the project
            source_dirs: List of source code directories (auto-detected if None)
            test_dirs: List of test directories (auto-detected if None)
            coverage_threshold: Minimum coverage percentage required
            include_patterns: File patterns to include in coverage
            exclude_patterns: File patterns to exclude from coverage
        """
        self.project_root = Path(project_root).resolve()
        self.coverage_threshold = coverage_threshold
        
        # Auto-detect project structure if not provided
        self.source_dirs = self._detect_source_dirs(source_dirs)
        self.test_dirs = self._detect_test_dirs(test_dirs)
        
        # Set up include/exclude patterns
        self.include_patterns = include_patterns or self._default_include_patterns()
        self.exclude_patterns = exclude_patterns or self._default_exclude_patterns()
        
        # Coverage instance
        self.cov: Optional[Coverage] = None
        
    def _detect_source_dirs(self, provided_dirs: Optional[List[str]]) -> List[Path]:
        """
        Auto-detect source code directories in the project.
        
        Common patterns: src/, app/, project_name/, or root-level .py files
        """
        if provided_dirs:
            return [self.project_root / d for d in provided_dirs]
        
        # Common source directory names
        common_names = ['src', 'app', 'lib', 'core']
        detected = []
        
        for name in common_names:
            candidate = self.project_root / name
            if candidate.exists() and candidate.is_dir():
                # Verify it contains Python files
                if list(candidate.rglob('*.py')):
                    detected.append(candidate)
        
        # If no standard directories found, check for package directories
        if not detected:
            for item in self.project_root.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Check if it's a Python package
                    if (item / '__init__.py').exists():
                        detected.append(item)
        
        # Fallback to project root if nothing found
        return detected or [self.project_root]
    
    def _detect_test_dirs(self, provided_dirs: Optional[List[str]]) -> List[Path]:
        """
        Auto-detect test directories in the project.
        
        Common patterns: tests/, test/, *_test/, *_tests/
        """
        if provided_dirs:
            return [self.project_root / d for d in provided_dirs]
        
        # Common test directory names
        common_names = ['tests', 'test', 'testing']
        detected = []
        
        for name in common_names:
            candidate = self.project_root / name
            if candidate.exists() and candidate.is_dir():
                detected.append(candidate)
        
        # Look for directories ending with _test or _tests
        for item in self.project_root.iterdir():
            if item.is_dir() and (item.name.endswith('_test') or item.name.endswith('_tests')):
                detected.append(item)
        
        return detected
    
    def _default_include_patterns(self) -> List[str]:
        """Default file patterns to include in coverage"""
        patterns = []
        for src_dir in self.source_dirs:
            # Include all Python files in source directories
            rel_path = src_dir.relative_to(self.project_root)
            patterns.append(f"{rel_path}/*.py")
            patterns.append(f"{rel_path}/**/*.py")
        return patterns
    
    def _default_exclude_patterns(self) -> List[str]:
        """Default file patterns to exclude from coverage"""
        return [
            "*/tests/*",
            "*/test/*",
            "*_test.py",
            "*/migrations/*",
            "*/venv/*",
            "*/.venv/*",
            "*/env/*",
            "*/node_modules/*",
            "*/__pycache__/*",
            "*/site-packages/*",
            "setup.py",
            "conftest.py"
        ]
    
    def run_coverage(
        self,
        test_command: Optional[str] = None,
        source_paths: Optional[List[str]] = None
    ) -> Coverage:
        """
        Run coverage analysis on the project.
        
        Args:
            test_command: Custom test command (default: auto-detect pytest/unittest)
            source_paths: Specific source paths to measure (default: all source dirs)
            
        Returns:
            Coverage instance with collected data
        """
        # Determine source paths
        if source_paths:
            sources = [str(self.project_root / p) for p in source_paths]
        else:
            sources = [str(d) for d in self.source_dirs]
        
        # Initialize coverage
        self.cov = Coverage(
            source=sources,
            omit=self.exclude_patterns,
            branch=True  # Enable branch coverage
        )
        
        # Start coverage measurement
        self.cov.start()
        
        try:
            # Run tests
            if test_command:
                self._run_custom_command(test_command)
            else:
                self._run_auto_detected_tests()
        finally:
            # Stop coverage measurement
            self.cov.stop()
            self.cov.save()
        
        return self.cov
    
    def _run_custom_command(self, command: str):
        """Run a custom test command"""
        result = subprocess.run(
            command,
            shell=True,
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Warning: Test command failed with code {result.returncode}")
            print(f"STDERR: {result.stderr}")
    
    def _run_auto_detected_tests(self):
        """Auto-detect and run tests using pytest or unittest"""
        # Try pytest first
        try:
            import pytest
            test_args = []
            for test_dir in self.test_dirs:
                if test_dir.exists():
                    test_args.append(str(test_dir))
            
            if test_args:
                pytest.main(test_args + ['-v'])
            else:
                pytest.main(['-v'])
            return
        except ImportError:
            pass
        
        # Fallback to unittest
        try:
            import unittest
            loader = unittest.TestLoader()
            suite = unittest.TestSuite()
            
            for test_dir in self.test_dirs:
                if test_dir.exists():
                    discovered = loader.discover(str(test_dir))
                    suite.addTests(discovered)
            
            runner = unittest.TextTestRunner(verbosity=2)
            runner.run(suite)
        except Exception as e:
            print(f"Warning: Could not run tests automatically: {e}")
    
    def analyze_coverage(self) -> CoverageReport:
        """
        Analyze coverage data and generate a comprehensive report.
        
        Returns:
            CoverageReport with detailed coverage information
        """
        if not self.cov:
            raise RuntimeError("Coverage not run yet. Call run_coverage() first.")
        
        files_coverage = {}
        uncovered_functions = []
        uncovered_classes = []
        
        # Analyze each source file
        for source_file in self.cov.get_data().measured_files():
            # Skip files outside source directories
            file_path = Path(source_file)
            if not any(self._is_under_dir(file_path, src_dir) for src_dir in self.source_dirs):
                continue
            
            # Get coverage analysis for this file
            analysis = self.cov.analysis2(source_file)
            file_cov = self._analyze_file(source_file, analysis)
            
            files_coverage[source_file] = file_cov
            
            # Collect uncovered functions and classes
            for func in file_cov.functions:
                if not func.is_covered:
                    uncovered_functions.append((source_file, func.name))
            
            for cls in file_cov.classes:
                # Check if class has any coverage
                if not self._is_class_covered(source_file, cls, analysis):
                    uncovered_classes.append((source_file, cls))
        
        # Calculate overall coverage
        total_coverage = self.cov.report(file=None, show_missing=False)
        
        # Generate summary
        summary = {
            "total_files": len(files_coverage),
            "total_functions": sum(len(f.functions) for f in files_coverage.values()),
            "uncovered_functions": len(uncovered_functions),
            "uncovered_classes": len(uncovered_classes),
            "total_lines": sum(f.total_lines for f in files_coverage.values()),
            "covered_lines": sum(f.covered_lines for f in files_coverage.values())
        }
        
        return CoverageReport(
            total_coverage=total_coverage,
            files=files_coverage,
            uncovered_functions=uncovered_functions,
            uncovered_classes=uncovered_classes,
            meets_threshold=total_coverage >= self.coverage_threshold,
            threshold=self.coverage_threshold,
            summary=summary
        )
    
    def _analyze_file(self, file_path: str, analysis: Analysis) -> FileCoverage:
        """Analyze coverage for a single file"""
        _, executable_lines, missing_lines, _ = analysis
        
        total_lines = len(executable_lines)
        covered_lines = total_lines - len(missing_lines)
        coverage_percent = (covered_lines / total_lines * 100) if total_lines > 0 else 0
        
        # Parse file to extract functions and classes
        functions, classes = self._extract_code_elements(file_path)
        
        # Determine coverage for each function
        function_coverage = []
        for func_name, start_line, end_line in functions:
            func_lines = set(range(start_line, end_line + 1))
            executable_in_func = func_lines.intersection(executable_lines)
            missing_in_func = func_lines.intersection(missing_lines)
            
            if executable_in_func:
                func_covered = len(executable_in_func) - len(missing_in_func)
                func_total = len(executable_in_func)
                func_percent = (func_covered / func_total * 100) if func_total > 0 else 0
                
                function_coverage.append(FunctionCoverage(
                    name=func_name,
                    start_line=start_line,
                    end_line=end_line,
                    covered_lines=func_covered,
                    total_lines=func_total,
                    coverage_percent=func_percent,
                    missing_lines=sorted(missing_in_func),
                    is_covered=len(missing_in_func) == 0
                ))
        
        return FileCoverage(
            file_path=file_path,
            total_lines=total_lines,
            covered_lines=covered_lines,
            missing_lines=sorted(missing_lines),
            coverage_percent=coverage_percent,
            functions=function_coverage,
            classes=classes
        )
    
    def _extract_code_elements(self, file_path: str) -> Tuple[List[Tuple[str, int, int]], List[str]]:
        """
        Extract functions and classes from a Python file using AST.
        
        Returns:
            Tuple of (functions, classes)
            - functions: List of (name, start_line, end_line)
            - classes: List of class names
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=file_path)
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return [], []
        
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append((
                    node.name,
                    node.lineno,
                    node.end_lineno or node.lineno
                ))
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
                # Also add class methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        functions.append((
                            f"{node.name}.{item.name}",
                            item.lineno,
                            item.end_lineno or item.lineno
                        ))
        
        return functions, classes
    
    def _is_class_covered(self, file_path: str, class_name: str, analysis: Analysis) -> bool:
        """Check if a class has any coverage"""
        _, executable_lines, missing_lines, _ = analysis
        
        # Find class definition in AST
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    class_lines = set(range(node.lineno, node.end_lineno + 1))
                    executable_in_class = class_lines.intersection(executable_lines)
                    missing_in_class = class_lines.intersection(missing_lines)
                    
                    # Class is covered if any of its executable lines are covered
                    return len(missing_in_class) < len(executable_in_class)
        except Exception:
            pass
        
        return False
    
    def _is_under_dir(self, file_path: Path, directory: Path) -> bool:
        """Check if file_path is under directory"""
        try:
            file_path.relative_to(directory)
            return True
        except ValueError:
            return False
    
    def identify_uncovered_from_diff(
        self,
        diff_content: str,
        report: CoverageReport
    ) -> Dict[str, List[str]]:
        """
        Identify uncovered code elements from a git diff.
        
        Args:
            diff_content: Git diff output
            report: Coverage report
            
        Returns:
            Dictionary mapping file paths to lists of uncovered elements
        """
        uncovered_in_diff = {}
        
        # Parse diff to extract changed files and line numbers
        changed_files = self._parse_diff(diff_content)
        
        for file_path, changed_lines in changed_files.items():
            if file_path not in report.files:
                continue
            
            file_cov = report.files[file_path]
            uncovered_elements = []
            
            # Check which functions in the diff are uncovered
            for func in file_cov.functions:
                # Check if function overlaps with changed lines
                func_lines = set(range(func.start_line, func.end_line + 1))
                if func_lines.intersection(changed_lines) and not func.is_covered:
                    uncovered_elements.append(f"Function: {func.name} (lines {func.start_line}-{func.end_line})")
            
            # Check for uncovered lines in the diff
            uncovered_lines = set(file_cov.missing_lines).intersection(changed_lines)
            if uncovered_lines:
                uncovered_elements.append(f"Uncovered lines: {sorted(uncovered_lines)}")
            
            if uncovered_elements:
                uncovered_in_diff[file_path] = uncovered_elements
        
        return uncovered_in_diff
    
    def _parse_diff(self, diff_content: str) -> Dict[str, Set[int]]:
        """
        Parse git diff to extract changed files and line numbers.
        
        Returns:
            Dictionary mapping file paths to sets of changed line numbers
        """
        changed_files = {}
        current_file = None
        current_line = 0
        
        for line in diff_content.split('\n'):
            # New file marker
            if line.startswith('+++'):
                file_path = line[6:].strip()  # Remove '+++ b/'
                if file_path.endswith('.py'):
                    current_file = file_path
                    changed_files[current_file] = set()
            
            # Line number marker
            elif line.startswith('@@') and current_file:
                # Extract line number from @@ -x,y +a,b @@
                parts = line.split('+')[1].split('@@')[0].strip()
                current_line = int(parts.split(',')[0])
            
            # Added or modified line
            elif current_file and (line.startswith('+') and not line.startswith('++')):
                changed_files[current_file].add(current_line)
                current_line += 1
            
            # Context or removed line
            elif current_file and (line.startswith(' ') or line.startswith('-')):
                if not line.startswith('-'):
                    current_line += 1
        
        return changed_files
    
    def calculate_coverage_delta(
        self,
        before_report: CoverageReport,
        after_report: CoverageReport
    ) -> CoverageDelta:
        """
        Calculate coverage changes between two reports.
        
        Args:
            before_report: Coverage report before changes
            after_report: Coverage report after changes
            
        Returns:
            CoverageDelta with comparison data
        """
        delta = after_report.total_coverage - before_report.total_coverage
        
        # Calculate line-level changes
        before_covered = before_report.summary['covered_lines']
        after_covered = after_report.summary['covered_lines']
        new_covered = after_covered - before_covered
        
        before_total = before_report.summary['total_lines']
        after_total = after_report.summary['total_lines']
        new_uncovered = (after_total - after_covered) - (before_total - before_covered)
        
        # Find improved and regressed files
        improved = []
        regressed = []
        
        for file_path in set(before_report.files.keys()).union(after_report.files.keys()):
            before_cov = before_report.files.get(file_path)
            after_cov = after_report.files.get(file_path)
            
            if before_cov and after_cov:
                if after_cov.coverage_percent > before_cov.coverage_percent:
                    improved.append(file_path)
                elif after_cov.coverage_percent < before_cov.coverage_percent:
                    regressed.append(file_path)
        
        return CoverageDelta(
            before_coverage=before_report.total_coverage,
            after_coverage=after_report.total_coverage,
            delta=delta,
            new_covered_lines=new_covered,
            new_uncovered_lines=new_uncovered,
            improved_files=improved,
            regressed_files=regressed
        )
    
    def generate_report(
        self,
        report: CoverageReport,
        format: CoverageFormat,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate a coverage report in the specified format.
        
        Args:
            report: Coverage report to format
            format: Output format (JSON, HTML, TERMINAL, XML)
            output_path: Output file path (required for HTML/XML)
            
        Returns:
            Report content as string (for JSON/TERMINAL) or file path (for HTML/XML)
        """
        if format == CoverageFormat.JSON:
            return self._generate_json_report(report)
        elif format == CoverageFormat.HTML:
            if not output_path:
                output_path = str(self.project_root / 'htmlcov')
            return self._generate_html_report(output_path)
        elif format == CoverageFormat.TERMINAL:
            return self._generate_terminal_report(report)
        elif format == CoverageFormat.XML:
            if not output_path:
                output_path = str(self.project_root / 'coverage.xml')
            return self._generate_xml_report(output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_json_report(self, report: CoverageReport) -> str:
        """Generate JSON format report"""
        data = {
            "total_coverage": report.total_coverage,
            "meets_threshold": report.meets_threshold,
            "threshold": report.threshold,
            "summary": report.summary,
            "files": {
                path: {
                    "coverage_percent": file.coverage_percent,
                    "total_lines": file.total_lines,
                    "covered_lines": file.covered_lines,
                    "missing_lines": file.missing_lines,
                    "functions": [
                        {
                            "name": func.name,
                            "coverage_percent": func.coverage_percent,
                            "is_covered": func.is_covered,
                            "missing_lines": func.missing_lines
                        }
                        for func in file.functions
                    ]
                }
                for path, file in report.files.items()
            },
            "uncovered_functions": [
                {"file": f, "function": func}
                for f, func in report.uncovered_functions
            ],
            "uncovered_classes": [
                {"file": f, "class": cls}
                for f, cls in report.uncovered_classes
            ]
        }
        return json.dumps(data, indent=2)
    
    def _generate_html_report(self, output_dir: str) -> str:
        """Generate HTML format report"""
        if not self.cov:
            raise RuntimeError("Coverage not run yet")
        
        self.cov.html_report(directory=output_dir)
        return output_dir
    
    def _generate_terminal_report(self, report: CoverageReport) -> str:
        """Generate terminal-friendly text report"""
        lines = []
        lines.append("=" * 80)
        lines.append("COVERAGE ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"Total Coverage: {report.total_coverage:.2f}%")
        lines.append(f"Threshold: {report.threshold:.2f}%")
        lines.append(f"Status: {'✓ PASS' if report.meets_threshold else '✗ FAIL'}")
        lines.append("")
        lines.append(f"Summary:")
        lines.append(f"  Total Files: {report.summary['total_files']}")
        lines.append(f"  Total Functions: {report.summary['total_functions']}")
        lines.append(f"  Uncovered Functions: {report.summary['uncovered_functions']}")
        lines.append(f"  Uncovered Classes: {report.summary['uncovered_classes']}")
        lines.append(f"  Total Lines: {report.summary['total_lines']}")
        lines.append(f"  Covered Lines: {report.summary['covered_lines']}")
        lines.append("")
        
        if report.uncovered_functions:
            lines.append("Uncovered Functions:")
            for file_path, func_name in report.uncovered_functions[:10]:
                lines.append(f"  - {func_name} in {file_path}")
            if len(report.uncovered_functions) > 10:
                lines.append(f"  ... and {len(report.uncovered_functions) - 10} more")
            lines.append("")
        
        if report.uncovered_classes:
            lines.append("Uncovered Classes:")
            for file_path, cls_name in report.uncovered_classes[:10]:
                lines.append(f"  - {cls_name} in {file_path}")
            if len(report.uncovered_classes) > 10:
                lines.append(f"  ... and {len(report.uncovered_classes) - 10} more")
            lines.append("")
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    def _generate_xml_report(self, output_path: str) -> str:
        """Generate XML format report (Cobertura format)"""
        if not self.cov:
            raise RuntimeError("Coverage not run yet")
        
        self.cov.xml_report(outfile=output_path)
        return output_path


# Convenience functions for common use cases

def quick_coverage_check(
    project_root: str,
    threshold: float = 80.0,
    test_command: Optional[str] = None
) -> Tuple[bool, CoverageReport]:
    """
    Quick coverage check for a project.
    
    Args:
        project_root: Project root directory
        threshold: Minimum coverage threshold
        test_command: Optional custom test command
        
    Returns:
        Tuple of (passes_threshold, report)
    """
    analyzer = CoverageAnalyzer(
        project_root=project_root,
        coverage_threshold=threshold
    )
    
    analyzer.run_coverage(test_command=test_command)
    report = analyzer.analyze_coverage()
    
    return report.meets_threshold, report


def analyze_diff_coverage(
    project_root: str,
    diff_content: str,
    threshold: float = 80.0
) -> Dict[str, any]:
    """
    Analyze coverage for code changes in a git diff.
    
    Args:
        project_root: Project root directory
        diff_content: Git diff content
        threshold: Coverage threshold
        
    Returns:
        Dictionary with coverage analysis for changed code
    """
    analyzer = CoverageAnalyzer(
        project_root=project_root,
        coverage_threshold=threshold
    )
    
    analyzer.run_coverage()
    report = analyzer.analyze_coverage()
    uncovered_in_diff = analyzer.identify_uncovered_from_diff(diff_content, report)
    
    return {
        "overall_coverage": report.total_coverage,
        "meets_threshold": report.meets_threshold,
        "uncovered_in_changes": uncovered_in_diff,
        "summary": report.summary
    }
