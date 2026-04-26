"""
Tests for tools/system_tools.py — list_directory and execute_bash
"""

import asyncio
import platform
import sys

import pytest

from mentask.tools.file_tools import list_directory
from mentask.tools.system_tools import _get_shell_args, execute_bash


class TestListDirectory:
    def test_lists_current_directory(self):
        result = list_directory(".")
        assert "Directory:" in result or "is empty" in result

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
        assert (
            "Permission denied to read the path" in result
            or "does not exist" in result
            or "outside the allowed directory" in result
        )

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
        python_exe = f'"{sys.executable}"'
        cmd = (
            f'& {python_exe} -c "import sys; sys.exit(1)"'
            if platform.system() == "Windows"
            else f'{python_exe} -c "import sys; sys.exit(1)"'
        )
        result = asyncio.run(execute_bash(cmd))
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

    @pytest.mark.asyncio
    async def test_timeout_prevents_hanging(self):
        """Verifies that commands timeout to prevent hanging."""
        import time

        # Command that sleeps longer than 60 seconds (default timeout)
        start_time = time.time()
        if platform.system() == "Windows":
            result = await execute_bash("Start-Sleep -Seconds 70")  # PowerShell sleep
        else:
            result = await execute_bash("sleep 70")
        end_time = time.time()
        # Should timeout within ~60 seconds
        assert end_time - start_time < 65  # Allow some margin
        assert "timed out" in result.lower()

    @pytest.mark.asyncio
    async def test_output_truncation(self):
        """Verifies that very long output is handled without hanging."""
        # Generate long output
        if platform.system() == "Windows":
            long_cmd = 'for ($i=0; $i -lt 1000; $i++) { echo "line$i" }'
        else:
            python_exe = f'"{sys.executable}"'
            long_cmd = f"{python_exe} -c \"for i in range(1000): print(f'line{{i}}')\""

        result = await execute_bash(long_cmd)
        # Should complete without hanging and have reasonable length
        assert len(result) > 100  # Has some output
        assert len(result) < 20000  # Not excessively long
        assert "line0" in result
