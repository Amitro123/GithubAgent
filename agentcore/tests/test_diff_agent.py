import pytest
from repofactor.application.agent_service.diff_agent import DiffAgent

@pytest.fixture
def diff_agent():
    return DiffAgent()

def test_generate_diff_basic(diff_agent):
    base_files = {
        "file1.py": "print('Hello')\nprint('World')",
        "file2.py": "def foo():\n    return 1"
    }
    modified_files = {
        "file1.py": "print('Hello')\nprint('World!')",
        "file2.py": "def foo():\n    return 2"
    }
    result = diff_agent.generate_diff(base_files, modified_files)
    
    assert result.files_changed == 2
    file1_diff = next((f for f in result.file_diffs if f.path == "file1.py"), None)
    assert file1_diff is not None
    assert "World!" in file1_diff.diff_text
    assert "files changed" in result.summary

def test_generate_diff_added_removed(diff_agent):
    base_files = {"main.py": "print(1)"}
    modified_files = {"main.py": "print(1)", "new.py": "print('new file')"}
    result = diff_agent.generate_diff(base_files, modified_files)
    assert result.files_changed == 1 or result.files_changed == 2
    assert result.lines_added >= 1
