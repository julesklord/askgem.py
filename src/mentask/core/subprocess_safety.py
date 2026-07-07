"""
Subprocess execution safety validation module for mentask.
Provides checks and wrappers for subprocess calls to prevent command/flag injections.
"""

import asyncio
import logging
import os
import subprocess
import sys
import urllib.parse
from collections.abc import Sequence
from typing import Any

_logger = logging.getLogger("mentask.security")

# Whitelist of allowed executables/binaries
_ALLOWED_COMMANDS = {
    "git",
    "docker",
    "ollama",
    "ruff",
    "taskkill",
    "opencode",
    "aider",
    "python",
    "python3",
    "sh",
    "bash",
    "wsl",
    "wsl.exe",
    sys.executable,
}


def validate_args(args: Sequence[Any]) -> list[str]:
    """Validates the argument list and checks against whitelist of commands.

    Args:
        args: Command and arguments as a sequence of strings (or string-like objects).

    Returns:
        list[str]: The validated string argument list.

    Raises:
        ValueError: If the command is not whitelisted or arguments are deemed unsafe.
    """
    if not args:
        raise ValueError("Empty command arguments")

    str_args = [str(arg) for arg in args]
    executable = str_args[0]
    base_exe = os.path.basename(executable)

    # Check against whitelist
    is_whitelisted = False
    if executable in _ALLOWED_COMMANDS or base_exe in _ALLOWED_COMMANDS:
        is_whitelisted = True
    else:
        # Check resolved paths for python/sys.executable
        try:
            exe_real = os.path.realpath(executable)
            sys_exe_real = os.path.realpath(sys.executable)
            if exe_real == sys_exe_real:
                is_whitelisted = True
        except OSError:  # nosec B110
            pass

    if not is_whitelisted:
        raise ValueError(f"Execution blocked: Executable '{executable}' is not in the security whitelist.")

    # Guard against flag injection in git arguments
    if base_exe == "git" and len(str_args) > 1:
        positional_args = []
        found_separator = False
        for arg in str_args[1:]:
            if arg == "--":
                found_separator = True
                continue
            if not found_separator:
                # Before -- separator: skip flags (start with -), track positional args
                if not arg.startswith("-"):
                    positional_args.append(arg)
            else:
                # After -- separator: all args are positional
                positional_args.append(arg)
        # Reject positional args that start with hyphen (flag injection)
        for arg in positional_args:
            if arg.startswith("-"):
                _logger.warning("Flag injection blocked in git arg: %s", arg)
                raise ValueError(f"Security: Flag injection blocked in git argument: {arg}")

    return str_args


def safe_run(args: Sequence[Any], **kwargs: Any) -> subprocess.CompletedProcess:
    """Wrapper around subprocess.run that validates the command arguments.

    Raises:
        ValueError: If security check fails.
    """
    validated = validate_args(args)
    return subprocess.run(validated, **kwargs)  # nosec B603


def safe_check_output(args: Sequence[Any], **kwargs: Any) -> str:
    """Wrapper around subprocess.check_output that validates the command arguments.

    Raises:
        ValueError: If security check fails.
    """
    validated = validate_args(args)
    # Ensure encoding is set if checking output to return str
    if "encoding" not in kwargs and not kwargs.get("text"):
        kwargs["encoding"] = "utf-8"
    return subprocess.check_output(validated, **kwargs)  # nosec B603


def safe_popen(args: Sequence[Any], **kwargs: Any) -> subprocess.Popen:
    """Wrapper around subprocess.Popen that validates the command arguments.

    Raises:
        ValueError: If security check fails.
    """
    validated = validate_args(args)
    return subprocess.Popen(validated, **kwargs)  # nosec B603


async def safe_create_subprocess_exec(
    program: Any, *args: Any, **kwargs: Any
) -> asyncio.subprocess.Process:
    """Wrapper around asyncio.create_subprocess_exec that validates command arguments.

    Raises:
        ValueError: If security check fails.
    """
    full_args = [program] + list(args)
    validated = validate_args(full_args)
    return await asyncio.create_subprocess_exec(validated[0], *validated[1:], **kwargs)  # nosec B603


def validate_url_scheme(url: str) -> None:
    """Validates that a URL has a safe schema (http or https).

    Raises:
        ValueError: If scheme is not http or https.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsafe URL scheme '{parsed.scheme}'. Only http and https are allowed.")

