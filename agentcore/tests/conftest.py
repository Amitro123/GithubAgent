# tests/conftest.py
"""
Pytest configuration for test suite
"""

import sys
from pathlib import Path

# Add src to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment variables
import os
os.environ.setdefault("LIGHTNING_API_KEY", "test-key-for-mocking")
os.environ.setdefault("REPO_CACHE_DIR", "./test_cache")
