"""
Tests for tools/system_tools.py — list_directory and execute_bash
"""
import os
import platform
import pytest

from pygemai_cli.tools.system_tools import list_directory, execute_bash, _get_shell_args


class TestListDirectory:
    def test_lists_current_directory(self):
        result = list_directory(".")
        assert "Directory: ." in result
        assert "Items:" in result

    def test_lists_specific_directory(self, tmp_path):
        (tmp_path / "alpha.txt").write_text("a")
        (tmp_path / "beta.txt").write_text("b")
        (tmp_path / "subdir").mkdir()

        result = list_directory(str(tmp_path))
        assert "alpha.txt" in result
        assert "beta.txt" in result
        assert "subdir" in result
        assert "📁" in result  # subdir icon
        assert "📄" in result  # file icon

    def test_empty_directory(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        result = list_directory(str(empty))
        assert "empty" in result.lower()

    def test_nonexistent_path(self):
        result = list_directory("/path/that/does/not/exist/abc123xyz")
        assert "Error" in result
        assert "does not exist" in result

    def test_returns_sorted_output(self, tmp_path):
        (tmp_path / "z_last.txt").write_text("")
        (tmp_path / "a_first.txt").write_text("")
        result = list_directory(str(tmp_path))
        lines = result.split("\n")
        item_lines = [l for l in lines if l.startswith("- ")]
        assert "a_first" in item_lines[0]
        assert "z_last" in item_lines[1]


class TestGetShellArgs:
    def test_returns_dict(self):
        result = _get_shell_args()
        assert isinstance(result, dict)

    def test_always_has_shell_true(self):
        result = _get_shell_args()
        assert result.get("shell") is True

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_windows_has_executable(self):
        result = _get_shell_args()
        # On Windows, should have an executable key pointing to PowerShell
        # (or at minimum, shell=True for cmd.exe fallback)
        assert "shell" in result


class TestExecuteBash:
    def test_echo_command(self):
        if platform.system() == "Windows":
            result = execute_bash("echo hello")
        else:
            result = execute_bash("echo hello")
        assert "STDOUT:" in result
        assert "hello" in result

    def test_failed_command_returns_stderr(self):
        # A command that should fail on any platform
        result = execute_bash("python -c \"import sys; sys.exit(1)\"")
        # Should not crash — returns normally
        assert isinstance(result, str)

    def test_nonexistent_command(self):
        result = execute_bash("this_command_does_not_exist_xyz123")
        # Should contain error info but not crash
        assert isinstance(result, str)
        assert len(result) > 0

    def test_silent_success_command(self):
        if platform.system() == "Windows":
            result = execute_bash("cmd /c rem noop")
        else:
            result = execute_bash("true")
        # When no output, should get the success message
        assert isinstance(result, str)

    def test_multiline_output(self):
        if platform.system() == "Windows":
            result = execute_bash("echo line1 & echo line2")
        else:
            result = execute_bash("echo line1 && echo line2")
        assert "line1" in result
        assert "line2" in result
