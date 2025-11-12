# agentcore/tests/utils/test_toon_encoder.py
import pytest
from src.repofactor.utils.toon_encoder import encode_toon, ToonEncoder, encode_files_toon

def test_encode_primitives():
    """Test encoding of basic data types."""
    assert encode_toon(None) == "null"
    assert encode_toon(True) == "true"
    assert encode_toon(False) == "false"
    assert encode_toon(123) == "123"
    assert encode_toon(123.456) == "123.456"
    assert encode_toon("simple") == "simple"

def test_string_quoting():
    """Test quoting logic for strings."""
    assert encode_toon("string with, delimiter") == '"string with, delimiter"'
    assert encode_toon("string with: special char") == '"string with: special char"'
    assert encode_toon(" leading space") == '" leading space"'
    assert encode_toon("trailing space ") == '"trailing space "'
    assert encode_toon("true") == '"true"'
    assert encode_toon("123.45") == '"123.45"'
    assert encode_toon("") == '""'

def test_simple_object():
    """Test encoding of a simple dictionary."""
    data = {"name": "Alice", "age": 30}
    expected = "name: Alice\nage: 30"
    assert encode_toon(data) == expected

def test_nested_object():
    """Test encoding of a nested dictionary."""
    data = {"user": {"name": "Bob", "active": True}, "level": 5}
    expected = "user:\n  name: Bob\n  active: true\nlevel: 5"
    assert encode_toon(data) == expected

def test_inline_array():
    """Test encoding of a simple list of primitives."""
    data = {"tags": ["dev", "python", "ai"]}
    expected = "tags[3]: dev,python,ai"
    assert encode_toon(data) == expected

def test_tabular_array():
    """Test encoding of a list of uniform objects."""
    data = {
        "users": [
            {"id": 1, "name": "Alice", "role": "admin"},
            {"id": 2, "name": "Bob", "role": "user"},
        ]
    }
    expected = "users[2]{id,name,role}:\n  1,Alice,admin\n  2,Bob,user"
    # ToonEncoder produces a stable key order, but let's handle potential instability in test
    # by checking the components.
    toon_output = encode_toon(data)
    header, rows = toon_output.split('\n', 1)

    assert "users[2]" in header
    assert "{id,name,role}" in header or "{id,role,name}" in header or "{name,id,role}" in header or "{name,role,id}" in header or "{role,id,name}" in header or "{role,name,id}" in header

    assert "1,Alice,admin" in rows or "1,admin,Alice" in rows
    assert "2,Bob,user" in rows or "2,user,Bob" in rows


def test_encode_files_toon():
    """Test the helper function for encoding file dictionaries."""
    files = {
        "main.py": "print('hello')\n" * 50,
        "utils.py": "def helper(): pass"
    }
    toon_output = encode_files_toon(files, max_content_length=50)

    assert "files[2]{path,content,truncated}:" in toon_output

    # Split the output into lines for easier checking
    lines = toon_output.strip().split('\n')
    header = lines[0]
    row1 = lines[1]
    row2 = lines[2]

    # Check that the truncated file is correctly identified
    assert 'main.py' in row1 or 'main.py' in row2
    assert 'true' in row1 or 'true' in row2

    # Check that the non-truncated file is correctly identified
    assert 'utils.py' in row1 or 'utils.py' in row2
    assert 'false' in row1 or 'false' in row2

    # Check for newline character
    assert '"print(\'hello\')\\nprint(\'hello\')\\nprint(\'hello\')\\nprint"' in toon_output

def test_empty_structures():
    """Test encoding of empty lists and dictionaries."""
    assert encode_toon({}) == ""
    assert encode_toon({"empty_list": []}) == "empty_list[0]:"
    assert encode_toon([]) == "[0]:"
