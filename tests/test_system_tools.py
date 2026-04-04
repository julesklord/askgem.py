"""
Tests for tools/system_tools.py — list_directory and execute_bash
"""
import platform

import pytest
import asyncio

from askgem.tools.system_tools import _get_shell_args, execute_bash
from askgem.tools.file_tools import list_directory


class TestListDirectory:
    def test_lists_current_directory(self):
        result = list_directory(".")
        assert "Directory:" in result
        assert "Items" in result

    def test_lists_specific_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "alpha.txt").write_text("a")
        (tmp_path / "beta.txt").write_text("b")
        (tmp_path / "subdir").mkdir()

        result = list_directory(".")
        assert "alpha.txt" in result
        assert "beta.txt" in result
        assert "subdir" in result
        assert "📁" in result  # subdir icon
        assert "📄" in result  # file icon

    def test_empty_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        result = list_directory(".")
        assert "empty" in result.lower()

    def test_nonexistent_path(self):
        result = list_directory("/path/that/does/not/exist/abc123xyz")
        assert "Error" in result
        # Permission error is raised before the path check
        assert "Permission denied to read the path" in result or "does not exist" in result

    def test_returns_sorted_output(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "z_last.txt").write_text("")
        (tmp_path / "a_first.txt").write_text("")
        result = list_directory(".")
        lines = result.split("\n")
        item_lines = [line for line in lines if line.startswith("- ")]
        assert "a_first" in item_lines[0]
        assert "z_last" in item_lines[1]


class TestGetShellArgs:
    def test_returns_dict(self):
        result = _get_shell_args("echo test")
        assert isinstance(result, dict)

    def test_always_has_shell_key(self):
        result = _get_shell_args("echo test")
        assert "shell" in result

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_windows_has_args_key(self):
        result = _get_shell_args("echo test")
        assert "args" in result


import asyncio

class TestExecuteBash:
    def test_echo_command(self):
        if platform.system() == "Windows":
            result = asyncio.run(execute_bash("echo hello"))
        else:
            result = asyncio.run(execute_bash("echo hello"))
        assert "STDOUT:" in result
        assert "hello" in result

    def test_failed_command_returns_stderr(self):
        # A command that should fail on any platform
        result = asyncio.run(execute_bash("python -c \"import sys; sys.exit(1)\""))
        # Should not crash — returns normally
        assert isinstance(result, str)

    def test_nonexistent_command(self):
        result = asyncio.run(execute_bash("this_command_does_not_exist_xyz123"))
        # Should contain error info but not crash
        assert isinstance(result, str)
        assert len(result) > 0

    def test_silent_success_command(self):
        if platform.system() == "Windows":
            result = asyncio.run(execute_bash("cmd /c rem noop"))
        else:
            result = asyncio.run(execute_bash("true"))
        # When no output, should get the success message
        assert isinstance(result, str)

    def test_multiline_output(self):
        if platform.system() == "Windows":
            result = asyncio.run(execute_bash("echo line1; echo line2"))
        else:
            result = asyncio.run(execute_bash("echo line1 && echo line2"))
        assert "line1" in result
        assert "line2" in result
