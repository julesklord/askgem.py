"""
Unit tests for the advanced search tools.
"""

import os
import pytest
from pathlib import Path
from src.askgem.tools.search_tools import grep_search, glob_find


@pytest.fixture
def temp_workspace(tmp_path):
    """Creates a temporary directory with some nested files for testing."""
    d = tmp_path / "workspace"
    d.mkdir()
    (d / "file1.txt").write_text("Hello World\nThis is a test.")
    (d / "file2.py").write_text("def hello():\n    print('Hello Python')")
    
    sub = d / "subdir"
    sub.mkdir()
    (sub / "nested.md").write_text("# Nested File\nTarget line is here.")
    
    hidden = d / ".git"
    hidden.mkdir()
    (hidden / "config").write_text("Should be ignored")
    
    return d


def test_grep_search_literal(temp_workspace):
    """Verifies basic literal string searching."""
    result = grep_search("Hello", str(temp_workspace))
    assert "file1.txt:1:Hello World" in result
    assert "file2.py:2:print('Hello Python')" in result
    assert ".git" not in result


def test_grep_search_regex(temp_workspace):
    """Verifies regex searching."""
    result = grep_search(r"T[a-z]+get", str(temp_workspace), is_regex=True)
    assert "nested.md:2:Target line is here." in result


def test_grep_search_case_insensitive(temp_workspace):
    """Verifies case-insensitive searching."""
    result = grep_search("hello", str(temp_workspace), case_sensitive=False)
    assert "file1.txt:1:Hello World" in result


def test_grep_search_no_match(temp_workspace):
    """Verifies behavior when no matches are found."""
    result = grep_search("NonExistentString", str(temp_workspace))
    assert "No matches found" in result


def test_glob_find_basic(temp_workspace):
    """Verifies recursive glob finding."""
    result = glob_find("*.py", str(temp_workspace))
    assert "file2.py" in result
    assert "file1.txt" not in result


def test_glob_find_nested(temp_workspace):
    """Verifies nested glob finding."""
    result = glob_find("**/*.md", str(temp_workspace))
    assert "subdir/nested.md" in result


def test_glob_find_no_match(temp_workspace):
    """Verifies behavior when no files match the glob."""
    result = glob_find("*.nonexistent", str(temp_workspace))
    assert "No files found" in result
