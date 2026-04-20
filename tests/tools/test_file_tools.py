"""
Tests for tools/file_tools.py — read_file and edit_file
"""

import os
from unittest.mock import patch

import pytest

from askgem.core.security import ensure_safe_path
from askgem.tools.file_tools import edit_file, read_file


@pytest.fixture(autouse=True)
def mock_ensure_safe_path():
    with patch("askgem.tools.file_tools.ensure_safe_path", side_effect=lambda x: x):
        yield


class TestReadFile:
    def test_reads_full_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3\n")
        result = read_file(str(f))
        assert "line1" in result
        assert "line3" in result

    def test_line_range(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("alpha\nbeta\ngamma\n")
        result = read_file(str(f), start_line=2, end_line=2)
        assert "beta" in result
        assert "alpha" not in result

    def test_missing_file_returns_error_string(self, tmp_path):
        result = read_file(str(tmp_path / "ghost.txt"))
        assert "Error" in result
        assert "does not exist" in result

    def test_directory_path_returns_error_string(self, tmp_path):
        result = read_file(str(tmp_path))
        assert "Error" in result

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        result = read_file(str(f))
        assert "empty" in result.lower()

    def test_invalid_range_returns_error(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("only one line\n")
        result = read_file(str(f), start_line=99, end_line=100)
        assert "Error" in result


class TestEditFile:
    def test_creates_new_file(self, tmp_path):
        target = str(tmp_path / "new.txt")
        result = edit_file(target, "", "hello world")
        assert "Success" in result
        with open(target, encoding="utf-8") as f:
            assert f.read() == "hello world"

    def test_replaces_exact_block(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("def foo():\n    return 1\n")
        result = edit_file(str(f), "return 1", "return 42")
        assert "Success" in result
        assert "42" in f.read_text()

    def test_creates_bkp_before_editing(self, tmp_path, monkeypatch):
        # mock get_backups_dir to return a dir inside tmp_path
        monkeypatch.setattr("askgem.tools.file_tools.get_backups_dir", lambda: tmp_path / "backups")
        f = tmp_path / "code.py"
        f.write_text("original content")
        edit_file(str(f), "original content", "new content")

        import glob

        bkp_list = glob.glob(str(tmp_path / "backups" / "**" / "code.py"), recursive=True)
        assert len(bkp_list) > 0
        with open(bkp_list[0], encoding="utf-8") as f:
            assert f.read() == "original content"

    def test_find_text_not_found_returns_error(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("actual content here")
        result = edit_file(str(f), "text that does not exist", "replacement")
        assert "Error" in result

    def test_empty_find_text_on_existing_file_returns_error(self, tmp_path):
        """Guard against the str.replace('', ...) corruption bug."""
        f = tmp_path / "code.py"
        f.write_text("some content")
        result = edit_file(str(f), "", "replacement")
        assert "Error" in result
        # File must be untouched
        assert f.read_text() == "some content"

    def test_creates_subdirectories_for_new_file(self, tmp_path):
        target = str(tmp_path / "sub" / "dir" / "new.txt")
        result = edit_file(target, "", "content")
        assert "Success" in result
        assert os.path.exists(target)


class TestFileSecurity:
    """Tests for path traversal and security vulnerabilities."""

    def test_path_traversal_prevention(self, tmp_path):
        """Verifies that ensure_safe_path prevents path traversal."""
        with pytest.raises(PermissionError, match="Access denied"):
            ensure_safe_path(str(tmp_path / ".." / ".." / "etc" / "passwd"))

    def test_absolute_path_outside_cwd(self, tmp_path):
        """Verifies that absolute paths outside CWD are blocked."""
        outside_path = str(tmp_path.parent / "outside.txt")
        with pytest.raises(PermissionError, match="Access denied"):
            ensure_safe_path(outside_path)

    def test_safe_paths_allowed(self, tmp_path, monkeypatch):
        """Verifies that safe paths are allowed."""
        monkeypatch.chdir(tmp_path)
        safe_path = "subdir/file.txt"
        result = ensure_safe_path(safe_path)
        expected = str(tmp_path / safe_path)
        assert result == expected

    def test_relative_paths_resolved(self, tmp_path):
        """Verifies that relative paths are resolved correctly."""
        rel_path = "subdir/file.txt"
        os.chdir(str(tmp_path))
        result = ensure_safe_path(rel_path)
        expected = str(tmp_path / rel_path)
        assert result == expected
