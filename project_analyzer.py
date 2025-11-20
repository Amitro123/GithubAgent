"""
Project Context Analyzer - Generic Python Repository Analysis

This module analyzes ANY Python repository to understand its structure,
test framework, coding conventions, and patterns. Works with Flask, FastAPI,
Django, CLI tools, and any other Python project structure.

Author: GitHub Automation Agent
"""

import os
import re
import ast
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
import configparser
import json


class TestFramework(Enum):
    """Supported test frameworks"""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    NOSE = "nose"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ProjectLayout(Enum):
    """Common Python project layouts"""
    FLAT = "flat"  # All code in root
    SRC = "src"    # src/ layout
    APP = "app"    # app/ layout
    LIB = "lib"    # lib/ layout
    PACKAGE = "package"  # Single package in root
    MONOREPO = "monorepo"  # Multiple packages


class ImportStyle(Enum):
    """Import pattern styles"""
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    MIXED = "mixed"


@dataclass
class TestConventions:
    """Test-specific conventions discovered"""
    framework: TestFramework
    test_directory: Optional[str] = None
    test_file_pattern: str = "test_*.py"  # or *_test.py
    uses_fixtures: bool = False
    uses_mocks: bool = False
    fixture_patterns: List[str] = field(default_factory=list)
    mock_libraries: Set[str] = field(default_factory=set)
    assertion_style: str = "assert"  # assert, self.assertEqual, etc.


@dataclass
class DependencyInfo:
    """Project dependencies information"""
    requirements_file: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)
    python_version: Optional[str] = None
    has_setup_py: bool = False
    has_pyproject_toml: bool = False
    has_pipfile: bool = False


@dataclass
class CodingConventions:
    """Coding style and conventions"""
    import_style: ImportStyle = ImportStyle.ABSOLUTE
    uses_type_hints: bool = False
    docstring_style: Optional[str] = None  # google, numpy, sphinx
    line_length: int = 88  # Default Black
    uses_dataclasses: bool = False
    uses_async: bool = False
    common_patterns: List[str] = field(default_factory=list)


@dataclass
class ProjectContext:
    """Complete project analysis context"""
    # Basic info
    repo_path: str
    project_name: str
    
    # Structure
    layout: ProjectLayout
    source_directories: List[str]
    
    # Testing
    test_conventions: TestConventions
    
    # Dependencies
    dependencies: DependencyInfo
    
    # Coding style
    coding_conventions: CodingConventions
    
    # Additional metadata
    is_package: bool = False
    has_cli: bool = False
    web_framework: Optional[str] = None  # flask, fastapi, django, etc.
    config_files: List[str] = field(default_factory=list)


class ProjectAnalyzer:
    """
    Analyzes Python repositories to extract structure, conventions, and patterns.
    Designed to work with ANY Python project structure.
    """
    
    # Common test directory names
    TEST_DIR_NAMES = ['tests', 'test', 'testing', 'test_suite', 'testsuite']
    
    # Common source directory names
    SOURCE_DIR_NAMES = ['src', 'app', 'lib', 'core', 'application']
    
    # Test framework indicators
    FRAMEWORK_IMPORTS = {
        'pytest': ['pytest', 'pytest.fixture', '_pytest'],
        'unittest': ['unittest', 'unittest.TestCase'],
        'nose': ['nose', 'nose.tools']
    }
    
    # Mock library indicators
    MOCK_LIBRARIES = ['unittest.mock', 'mock', 'pytest-mock', 'responses', 'httpretty']
    
    def __init__(self, repo_path: str):
        """
        Initialize analyzer with repository path.
        
        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = Path(repo_path)
        self.project_name = self.repo_path.name
        
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
    
    def analyze(self) -> ProjectContext:
        """
        Perform complete repository analysis.
        
        Returns:
            ProjectContext with all discovered information
        """
        return ProjectContext(
            repo_path=str(self.repo_path),
            project_name=self.project_name,
            layout=self._detect_project_layout(),
            source_directories=self._find_source_directories(),
            test_conventions=self._analyze_test_conventions(),
            dependencies=self._analyze_dependencies(),
            coding_conventions=self._analyze_coding_conventions(),
            is_package=self._is_package(),
            has_cli=self._detect_cli(),
            web_framework=self._detect_web_framework(),
            config_files=self._find_config_files()
        )
    
    def _detect_project_layout(self) -> ProjectLayout:
        """Detect the project's directory layout"""
        # Check for src/ layout
        if (self.repo_path / 'src').exists():
            return ProjectLayout.SRC
        
        # Check for app/ layout
        if (self.repo_path / 'app').exists():
            return ProjectLayout.APP
        
        # Check for lib/ layout
        if (self.repo_path / 'lib').exists():
            return ProjectLayout.LIB
        
        # Check for monorepo (multiple packages)
        python_packages = [
            d for d in self.repo_path.iterdir()
            if d.is_dir() and (d / '__init__.py').exists()
        ]
        if len(python_packages) > 3:
            return ProjectLayout.MONOREPO
        
        # Check for single package
        if len(python_packages) == 1:
            return ProjectLayout.PACKAGE
        
        # Default to flat
        return ProjectLayout.FLAT
    
    def _find_source_directories(self) -> List[str]:
        """Find all directories containing source code"""
        source_dirs = []
        
        # Check common source directory names
        for dir_name in self.SOURCE_DIR_NAMES:
            dir_path = self.repo_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                source_dirs.append(dir_name)
        
        # Find Python packages in root
        for item in self.repo_path.iterdir():
            if item.is_dir() and (item / '__init__.py').exists():
                if item.name not in self.TEST_DIR_NAMES:
                    source_dirs.append(item.name)
        
        return source_dirs if source_dirs else ['.']
    
    def _analyze_test_conventions(self) -> TestConventions:
        """Analyze testing conventions and patterns"""
        test_dir = self._find_test_directory()
        framework = self._detect_test_framework()
        test_pattern = self._detect_test_file_pattern(test_dir)
        
        conventions = TestConventions(
            framework=framework,
            test_directory=test_dir,
            test_file_pattern=test_pattern
        )
        
        # Analyze test files for patterns
        if test_dir:
            test_path = self.repo_path / test_dir
            if test_path.exists():
                self._analyze_test_patterns(test_path, conventions)
        
        return conventions
    
    def _find_test_directory(self) -> Optional[str]:
        """Find the test directory"""
        for test_dir in self.TEST_DIR_NAMES:
            if (self.repo_path / test_dir).exists():
                return test_dir
        return None
    
    def _detect_test_framework(self) -> TestFramework:
        """Detect which test framework is used"""
        frameworks_found = set()
        
        # Check config files
        if (self.repo_path / 'pytest.ini').exists() or \
           (self.repo_path / 'pyproject.toml').exists():
            frameworks_found.add(TestFramework.PYTEST)
        
        if (self.repo_path / 'setup.cfg').exists():
            config = configparser.ConfigParser()
            try:
                config.read(self.repo_path / 'setup.cfg')
                if 'tool:pytest' in config.sections():
                    frameworks_found.add(TestFramework.PYTEST)
            except:
                pass
        
        # Scan test files for imports
        test_files = self._find_python_files(self._find_test_directory())
        for test_file in test_files[:10]:  # Sample first 10 files
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for framework, imports in self.FRAMEWORK_IMPORTS.items():
                    for imp in imports:
                        if imp in content:
                            frameworks_found.add(TestFramework[framework.upper()])
            except:
                continue
        
        if len(frameworks_found) == 0:
            return TestFramework.UNKNOWN
        elif len(frameworks_found) == 1:
            return list(frameworks_found)[0]
        else:
            return TestFramework.MIXED
    
    def _detect_test_file_pattern(self, test_dir: Optional[str]) -> str:
        """Detect test file naming convention"""
        if not test_dir:
            return "test_*.py"
        
        test_path = self.repo_path / test_dir
        if not test_path.exists():
            return "test_*.py"
        
        test_prefix_count = 0
        test_suffix_count = 0
        
        for file in test_path.rglob('*.py'):
            if file.stem.startswith('test_'):
                test_prefix_count += 1
            elif file.stem.endswith('_test'):
                test_suffix_count += 1
        
        return "*_test.py" if test_suffix_count > test_prefix_count else "test_*.py"
    
    def _analyze_test_patterns(self, test_path: Path, conventions: TestConventions):
        """Analyze test files for patterns like fixtures and mocks"""
        test_files = list(test_path.rglob('*.py'))[:20]  # Sample
        
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for fixtures
                if '@pytest.fixture' in content or '@fixture' in content:
                    conventions.uses_fixtures = True
                    # Extract fixture patterns
                    fixture_matches = re.findall(r'@pytest\.fixture.*?\ndef\s+(\w+)', content)
                    conventions.fixture_patterns.extend(fixture_matches)
                
                # Check for mocks
                for mock_lib in self.MOCK_LIBRARIES:
                    if mock_lib in content:
                        conventions.uses_mocks = True
                        conventions.mock_libraries.add(mock_lib)
                
                # Detect assertion style
                if 'self.assertEqual' in content or 'self.assertTrue' in content:
                    conventions.assertion_style = "unittest"
                elif 'assert ' in content:
                    conventions.assertion_style = "assert"
                    
            except:
                continue
    
    def _analyze_dependencies(self) -> DependencyInfo:
        """Analyze project dependencies"""
        dep_info = DependencyInfo()
        
        # Check requirements.txt
        req_file = self.repo_path / 'requirements.txt'
        if req_file.exists():
            dep_info.requirements_file = 'requirements.txt'
            dep_info.dependencies = self._parse_requirements(req_file)
        
        # Check pyproject.toml
        pyproject = self.repo_path / 'pyproject.toml'
        if pyproject.exists():
            dep_info.has_pyproject_toml = True
            deps = self._parse_pyproject_toml(pyproject)
            if deps:
                dep_info.dependencies.extend(deps)
        
        # Check setup.py
        setup_py = self.repo_path / 'setup.py'
        if setup_py.exists():
            dep_info.has_setup_py = True
            deps = self._parse_setup_py(setup_py)
            if deps:
                dep_info.dependencies.extend(deps)
        
        # Check Pipfile
        pipfile = self.repo_path / 'Pipfile'
        if pipfile.exists():
            dep_info.has_pipfile = True
        
        # Detect Python version
        dep_info.python_version = self._detect_python_version()
        
        return dep_info
    
    def _parse_requirements(self, req_file: Path) -> List[str]:
        """Parse requirements.txt file"""
        dependencies = []
        try:
            with open(req_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name (before ==, >=, etc.)
                        pkg = re.split(r'[=<>!]', line)[0].strip()
                        dependencies.append(pkg)
        except:
            pass
        return dependencies
    
    def _parse_pyproject_toml(self, pyproject_file: Path) -> List[str]:
        """Parse pyproject.toml for dependencies"""
        dependencies = []
        try:
            import tomli
            with open(pyproject_file, 'rb') as f:
                data = tomli.load(f)
                
            # Check different possible locations
            deps = data.get('project', {}).get('dependencies', [])
            if deps:
                dependencies.extend([re.split(r'[=<>!]', d)[0].strip() for d in deps])
            
            # Check poetry dependencies
            poetry_deps = data.get('tool', {}).get('poetry', {}).get('dependencies', {})
            if poetry_deps:
                dependencies.extend([k for k in poetry_deps.keys() if k != 'python'])
        except:
            # Fallback to regex parsing if tomli not available
            try:
                with open(pyproject_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    deps = re.findall(r'"([^"]+)"', content)
                    dependencies.extend([d.split('[')[0] for d in deps if '==' in d or '>=' in d])
            except:
                pass
        
        return dependencies
    
    def _parse_setup_py(self, setup_file: Path) -> List[str]:
        """Parse setup.py for dependencies"""
        dependencies = []
        try:
            with open(setup_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for install_requires
            match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if match:
                deps_str = match.group(1)
                deps = re.findall(r'["\']([^"\']+)["\']', deps_str)
                dependencies.extend([re.split(r'[=<>!]', d)[0].strip() for d in deps])
        except:
            pass
        
        return dependencies
    
    def _detect_python_version(self) -> Optional[str]:
        """Detect required Python version"""
        # Check .python-version
        python_version_file = self.repo_path / '.python-version'
        if python_version_file.exists():
            try:
                return python_version_file.read_text().strip()
            except:
                pass
        
        # Check pyproject.toml
        pyproject = self.repo_path / 'pyproject.toml'
        if pyproject.exists():
            try:
                with open(pyproject, 'r', encoding='utf-8') as f:
                    content = f.read()
                    match = re.search(r'python\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        return match.group(1)
            except:
                pass
        
        return None
    
    def _analyze_coding_conventions(self) -> CodingConventions:
        """Analyze coding style and conventions"""
        conventions = CodingConventions()
        
        # Sample Python files
        python_files = self._find_python_files()[:30]
        
        absolute_imports = 0
        relative_imports = 0
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Analyze imports
                if 'from .' in content:
                    relative_imports += 1
                if re.search(r'from\s+\w+', content):
                    absolute_imports += 1
                
                # Check for type hints
                if ': ' in content and '->' in content:
                    conventions.uses_type_hints = True
                
                # Check for dataclasses
                if '@dataclass' in content:
                    conventions.uses_dataclasses = True
                
                # Check for async
                if 'async def' in content or 'await ' in content:
                    conventions.uses_async = True
                
                # Detect docstring style
                if '"""' in content:
                    if 'Args:' in content and 'Returns:' in content:
                        conventions.docstring_style = 'google'
                    elif 'Parameters' in content:
                        conventions.docstring_style = 'numpy'
                    elif ':param' in content:
                        conventions.docstring_style = 'sphinx'
                        
            except:
                continue
        
        # Determine import style
        if relative_imports > absolute_imports * 2:
            conventions.import_style = ImportStyle.RELATIVE
        elif absolute_imports > relative_imports * 2:
            conventions.import_style = ImportStyle.ABSOLUTE
        else:
            conventions.import_style = ImportStyle.MIXED
        
        # Check for Black/Flake8 config
        if (self.repo_path / 'pyproject.toml').exists():
            try:
                with open(self.repo_path / 'pyproject.toml', 'r') as f:
                    content = f.read()
                    match = re.search(r'line-length\s*=\s*(\d+)', content)
                    if match:
                        conventions.line_length = int(match.group(1))
            except:
                pass
        
        return conventions
    
    def _is_package(self) -> bool:
        """Check if this is a Python package"""
        return (self.repo_path / 'setup.py').exists() or \
               (self.repo_path / 'pyproject.toml').exists()
    
    def _detect_cli(self) -> bool:
        """Detect if project has CLI interface"""
        # Check for common CLI patterns
        python_files = self._find_python_files()[:20]
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'click' in content or 'argparse' in content or \
                       'if __name__ == "__main__"' in content:
                        return True
            except:
                continue
        
        return False
    
    def _detect_web_framework(self) -> Optional[str]:
        """Detect web framework if any"""
        python_files = self._find_python_files()[:20]
        
        framework_indicators = {
            'flask': ['from flask import', 'Flask(__name__)'],
            'fastapi': ['from fastapi import', 'FastAPI()'],
            'django': ['from django', 'django.conf'],
            'tornado': ['import tornado', 'tornado.web'],
            'bottle': ['from bottle import', 'Bottle()']
        }
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for framework, indicators in framework_indicators.items():
                    if any(ind in content for ind in indicators):
                        return framework
            except:
                continue
        
        return None
    
    def _find_config_files(self) -> List[str]:
        """Find configuration files"""
        config_patterns = [
            'setup.py', 'setup.cfg', 'pyproject.toml', 'tox.ini',
            'pytest.ini', '.flake8', '.pylintrc', 'mypy.ini',
            'requirements.txt', 'Pipfile', 'poetry.lock'
        ]
        
        found_configs = []
        for pattern in config_patterns:
            if (self.repo_path / pattern).exists():
                found_configs.append(pattern)
        
        return found_configs
    
    def _find_python_files(self, subdir: Optional[str] = None) -> List[Path]:
        """Find all Python files in repository or subdirectory"""
        search_path = self.repo_path / subdir if subdir else self.repo_path
        
        if not search_path.exists():
            return []
        
        python_files = []
        for py_file in search_path.rglob('*.py'):
            # Skip virtual environments and cache
            if any(part in py_file.parts for part in ['venv', '.venv', 'env', '__pycache__', '.git']):
                continue
            python_files.append(py_file)
        
        return python_files


def analyze_repository(repo_path: str) -> ProjectContext:
    """
    Convenience function to analyze a repository.
    
    Args:
        repo_path: Path to repository root
        
    Returns:
        ProjectContext with complete analysis
    """
    analyzer = ProjectAnalyzer(repo_path)
    return analyzer.analyze()


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
    else:
        repo_path = "."
    
    print(f"Analyzing repository: {repo_path}")
    context = analyze_repository(repo_path)
    
    print(f"\nProject: {context.project_name}")
    print(f"Layout: {context.layout.value}")
    print(f"Source directories: {', '.join(context.source_directories)}")
    print(f"\nTest Framework: {context.test_conventions.framework.value}")
    print(f"Test Directory: {context.test_conventions.test_directory}")
    print(f"Test Pattern: {context.test_conventions.test_file_pattern}")
    print(f"\nWeb Framework: {context.web_framework}")
    print(f"Has CLI: {context.has_cli}")
    print(f"Import Style: {context.coding_conventions.import_style.value}")
    print(f"Uses Type Hints: {context.coding_conventions.uses_type_hints}")
    print(f"Uses Async: {context.coding_conventions.uses_async}")
