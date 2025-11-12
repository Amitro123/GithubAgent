import sys
from pathlib import Path
import pytest
import asyncio


# Add src to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / 'src'))

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def pytest_sessionfinish(session, exitstatus):
    """Cleanup after all tests"""
    # Give time for cleanup
    import time
    time.sleep(0.5)

