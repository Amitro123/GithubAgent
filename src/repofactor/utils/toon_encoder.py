"""
TOON (Token-Oriented Object Notation) Encoder for Python
========================================================

Compact, LLM-friendly data serialization format.
Based on: https://github.com/toon-format/toon

Benefits:
- 30-60% fewer tokens than JSON for tabular data
- LLM-friendly structure (explicit lengths, field headers)
- Human-readable indentation-based format

Usage:
    from repofactor.utils.toon_encoder import encode_toon
    
    data = {"users": [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"}
    ]}
    
    toon_str = encode_toon(data)
    # Output:
    # users[2]{id,name,role}:
    #   1,Alice,admin
    #   2,Bob,user
"""

from typing import Any, Dict, List, Union
import json


def encode_toon(data: Any, indent: int = 2, delimiter: str = ',') -> str:
    """
    Encode Python data to TOON format.
    
    Args:
        data: Python dict, list, or primitive to encode
        indent: Spaces per indentation level (default: 2)
        delimiter: Array delimiter - ',' (default), '\t' (tab), '|' (pipe)
    
    Returns:
        TOON-formatted string
    
    Examples:
        >>> encode_toon({"name": "Alice", "age": 30})
        'name: Alice\\nage: 30'
        
        >>> encode_toon({"items": [{"id": 1, "qty": 5}, {"id": 2, "qty": 3}]})
        'items[2]{id,qty}:\\n  1,5\\n  2,3'
    """
    encoder = ToonEncoder(indent=indent, delimiter=delimiter)
    return encoder.encode(data)


class ToonEncoder:
    """TOON format encoder"""
    
    def __init__(self, indent: int = 2, delimiter: str = ','):
        self.indent = indent
        self.delimiter = delimiter
    
    def encode(self, value: Any, level: int = 0) -> str:
        """Encode a value at given indentation level"""
        
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return self._encode_number(value)
        elif isinstance(value, str):
            return self._quote_string(value)
        elif isinstance(value, dict):
            return self._encode_object(value, level)
        elif isinstance(value, list):
            return self._encode_array(value, level)
        else:
            # Fallback to JSON
            return json.dumps(value)
    
    def _encode_number(self, num: Union[int, float]) -> str:
        """Encode number (no scientific notation)"""
        if isinstance(num, float):
            # Avoid scientific notation
            if num.is_integer():
                return str(int(num))
            return f"{num:.10g}"  # Up to 10 significant digits
        return str(num)
    
    def _encode_object(self, obj: Dict, level: int) -> str:
        """Encode object as key:value pairs"""
        
        if not obj:
            return ""
        
        spaces = " " * (self.indent * level)
        lines = []
        
        for key, value in obj.items():
            quoted_key = self._quote_key(key)
            
            if isinstance(value, dict):
                # Nested object
                lines.append(f"{spaces}{quoted_key}:")
                nested = self._encode_object(value, level + 1)
                if nested:
                    lines.append(nested)
            elif isinstance(value, list):
                # Array
                array_str = self._encode_array_with_key(value, level + 1, key)
                lines.append(array_str)
            else:
                # Primitive
                value_str = self.encode(value, level)
                lines.append(f"{spaces}{quoted_key}: {value_str}")
        
        return "\n".join(lines)
    
    def _encode_array_with_key(self, arr: List, level: int, key: str) -> str:
        """Encode array with key prefix"""
        
        if not arr:
            spaces = " " * (self.indent * (level - 1))
            return f"{spaces}{key}[0]:"
        
        # Check if tabular (uniform objects with primitives)
        if self._is_tabular(arr):
            return self._encode_tabular(arr, level, key)
        
        # Check if all primitives (inline)
        if all(isinstance(v, (str, int, float, bool, type(None))) for v in arr):
            return self._encode_inline(arr, level, key)
        
        # List format
        return self._encode_list(arr, level, key)
    
    def _encode_array(self, arr: List, level: int) -> str:
        """Encode array without key prefix"""
        
        if not arr:
            return "[0]:"
        
        if self._is_tabular(arr):
            return self._encode_tabular(arr, level)
        
        if all(isinstance(v, (str, int, float, bool, type(None))) for v in arr):
            return self._encode_inline(arr, level)
        
        return self._encode_list(arr, level)
    
    def _is_tabular(self, arr: List) -> bool:
        """Check if array is tabular (uniform objects with primitive values)"""
        
        if not arr or not all(isinstance(item, dict) for item in arr):
            return False
        
        # All dicts must have same keys
        first_keys = set(arr[0].keys())
        if not all(set(item.keys()) == first_keys for item in arr):
            return False
        
        # All values must be primitives
        for item in arr:
            if not all(isinstance(v, (str, int, float, bool, type(None))) for v in item.values()):
                return False
        
        return True
    
    def _encode_tabular(self, arr: List[Dict], level: int, key: str = None) -> str:
        """Encode as TOON table: key[N]{field1,field2}: val1,val2"""
        
        spaces = " " * (self.indent * (level - 1))
        
        # Header: [N]{fields}:
        fields = list(arr[0].keys())
        
        # Use delimiter-specific header format
        if self.delimiter == '\t':
            delim_marker = '\t'
            field_str = '\t'.join(fields)
        elif self.delimiter == '|':
            delim_marker = '|'
            field_str = '|'.join(fields)
        else:  # comma
            delim_marker = ''
            field_str = ','.join(fields)
        
        if key:
            header = f"{spaces}{key}[{len(arr)}{delim_marker}]{{{field_str}}}:"
        else:
            header = f"[{len(arr)}{delim_marker}]{{{field_str}}}:"
        
        lines = [header]
        
        # Data rows
        row_spaces = " " * (self.indent * level)
        for item in arr:
            values = [self.encode(item[f], level) for f in fields]
            lines.append(row_spaces + self.delimiter.join(values))
        
        return "\n".join(lines)
    
    def _encode_inline(self, arr: List, level: int, key: str = None) -> str:
        """Encode primitive array inline: key[N]: val1,val2,val3"""
        
        spaces = " " * (self.indent * (level - 1))
        values = [self.encode(v, level) for v in arr]
        
        # Delimiter-aware header
        if self.delimiter == '\t':
            delim_marker = '\t'
        elif self.delimiter == '|':
            delim_marker = '|'
        else:
            delim_marker = ''
        
        if key:
            return f"{spaces}{key}[{len(arr)}{delim_marker}]: {self.delimiter.join(values)}"
        else:
            return f"[{len(arr)}{delim_marker}]: {self.delimiter.join(values)}"
    
    def _encode_list(self, arr: List, level: int, key: str = None) -> str:
        """Encode non-uniform array as list: - item1 / - item2"""
        
        spaces = " " * (self.indent * (level - 1))
        
        # Header
        if key:
            header = f"{spaces}{key}[{len(arr)}]:"
        else:
            header = f"[{len(arr)}]:"
        
        lines = [header]
        
        # List items
        item_spaces = " " * (self.indent * level)
        for item in arr:
            if isinstance(item, (dict, list)):
                item_str = self.encode(item, level)
                lines.append(f"{item_spaces}- {item_str}")
            else:
                lines.append(f"{item_spaces}- {self.encode(item, level)}")
        
        return "\n".join(lines)
    
    def _quote_key(self, key: str) -> str:
        """Quote key if needed (must be valid identifier)"""
        
        if not key:
            return '""'
        
        # Valid identifier: starts with letter/underscore, contains only letters/digits/underscore/dot
        if key[0].isalpha() or key[0] == '_':
            if all(c.isalnum() or c in ('_', '.') for c in key):
                return key
        
        return json.dumps(key)
    
    def _quote_string(self, s: str) -> str:
        """Quote string if needed"""
        
        # Empty or has leading/trailing spaces
        if not s or s != s.strip():
            return json.dumps(s)
        
        # Contains special chars
        special_chars = [':', '"', '\\']
        if self.delimiter in s or any(c in s for c in special_chars):
            return json.dumps(s)
        
        # Looks like boolean/number/null
        if s.lower() in ('true', 'false', 'null'):
            return f'"{s}"'
        
        try:
            float(s)
            return f'"{s}"'
        except ValueError:
            pass
        
        # Looks like structure
        if s.startswith('- ') or s.startswith('[') or s.startswith('{'):
            return json.dumps(s)
        
        return s


# ============================================================================
# Helper Functions
# ============================================================================

def encode_files_toon(files: Dict[str, str], max_content_length: int = 400) -> str:
    """
    Encode file contents to TOON format with truncation.
    
    Args:
        files: Dict of {filepath: content}
        max_content_length: Max chars per file (default: 400)
    
    Returns:
        TOON-formatted string
    
    Example:
        >>> files = {"main.py": "print('hello')\\n" * 100}
        >>> toon = encode_files_toon(files, max_content_length=50)
    """
    
    files_data = [
        {
            "path": path,
            "content": content[:max_content_length],
            "truncated": len(content) > max_content_length
        }
        for path, content in files.items()
    ]
    
    return encode_toon({"files": files_data})


def encode_analysis_context_toon(
    files: Dict[str, str],
    instructions: str,
    target_context: str = None,
    max_file_length: int = 200
) -> str:
    """
    Encode repository analysis context to TOON format.
    
    Optimized for LLM prompts with minimal tokens.
    
    Args:
        files: Repository files {path: content}
        instructions: User instructions
        target_context: Optional target project context
        max_file_length: Max chars per file (default: 200, very aggressive!)
    
    Returns:
        TOON-formatted prompt section
    """

    
    # Truncate files
    truncated_files = {
        path: content[:max_file_length]
        for path, content in files.items()
    }
    
    # Build TOON structure
    context = {
        "task": instructions[:200], 
        "files": [
            {"path": path, "code": content} 
            for path, content in truncated_files.items()
        ]
    }
    
    # Don't include target_context for now - too much!
    
    return encode_toon(context)
