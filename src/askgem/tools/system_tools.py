"""
System operations tools module for the AI agent.

Provides isolated filesystem exploration and bash execution capabilities.
It does NOT handle interactive terminal sessions or streaming stdio.
"""

import asyncio
import os
import platform
import shutil
import subprocess
from typing import Callable, Optional


def list_directory(path: str = ".") -> str:
    """
    Lists all files and folders inside a specific directory on the host system.
    Useful for exploring the current working environment, finding code or other resources.

    Args:
        path: The absolute or relative path of the directory to list. Empty defaults to the current directory.

    Returns:
        A formatted string with the found items or an error message if the path is invalid.
    """
    if not path:
        path = "."

    try:
        elements = sorted(os.listdir(path))
        if not elements:
            return f"The directory '{path}' is empty."

        max_items = 100
        total_items = len(elements)

        listing = [f"Directory: {path}"]
        listing.append(f"Items (showing {min(max_items, total_items)} of {total_items}):")

        for item in elements[:max_items]:
            full_path = os.path.join(path, item)
            item_type = "📁" if os.path.isdir(full_path) else "📄"
            listing.append(f"- {item_type} {item}")

        if total_items > max_items:
            listing.append(f"\n[i] ... and {total_items - max_items} more items hidden. Use a more specific path.")

        return "\n".join(listing)
    except FileNotFoundError:
        return f"Error: The path '{path}' does not exist."
    except NotADirectoryError:
        return f"Error: The path '{path}' is a file, not a directory."
    except PermissionError:
        return f"Error: Permission denied to read the path '{path}'."
    except Exception as e:
        return f"Unexpected error while listing path '{path}': {e}"


def _get_shell_args(command: str) -> dict:
    """
    Returns the appropriate subprocess keyword arguments for the current OS,
    including a potentially rewritten 'args' key for the command itself.

    Windows: Routes through PowerShell (pwsh or powershell.exe) by building
             an explicit argument list [pwsh, '-Command', command] with
             shell=False. This avoids the OS splitting paths with spaces
             (e.g. 'C:\\Program Files\\PowerShell\\7\\pwsh.exe').
             Falls back to cmd.exe via shell=True if PowerShell is absent.
    Unix:    Uses the default /bin/sh behavior via shell=True.
    """
    if platform.system() != "Windows":
        return {"args": command, "shell": True}

    # Prefer pwsh (PowerShell 7+) over legacy powershell.exe
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if pwsh:
        # Build explicit arg list so subprocess never splits the executable path
        return {"args": [pwsh, "-Command", command], "shell": False}

    # Absolute fallback — cmd.exe, which is always present on Windows
    return {"args": command, "shell": True}


async def execute_bash(command: str, log_callback: Optional[Callable[[str], None]] = None) -> str:
    """
    Executes a shell command asynchronously, captures its output,
    and returns it as text. Supports real-time logging via log_callback.
    """
    try:
        shell_kwargs = _get_shell_args(command)
        run_args = shell_kwargs.pop("args")
<<<<<<< Updated upstream
        result = subprocess.run(
            run_args,
            capture_output=True,
            text=True,
            check=False,           # Exit codes handled manually to avoid crashing the agentic loop
            timeout=60,            # Safety cap: prevents a hung command from locking the CLI forever
            **shell_kwargs,
        )

=======
        
        # Proper async subprocess to avoid blocking the TUI event loop
        if isinstance(run_args, list):
            # Windows pwsh/powershell path
            process = await asyncio.create_subprocess_exec(
                *run_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **shell_kwargs
            )
        else:
            # Unix /bin/sh path
            process = await asyncio.create_subprocess_shell(
                run_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **shell_kwargs
            )

        stdout_accum = []
        stderr_accum = []

        async def read_stream(stream, accum, color=None):
            while True:
                line = await stream.readline()
                if not line:
                    break
                line_str = line.decode().rstrip()
                accum.append(line_str + "\n")
                if log_callback:
                    msg = f"[{color}]{line_str}[/]" if color else line_str
                    log_callback(msg)

        # Run both streams concurrently
        await asyncio.gather(
            read_stream(process.stdout, stdout_accum),
            read_stream(process.stderr, stderr_accum, "red")
        )

        await process.wait()

        stdout = "".join(stdout_accum)
        stderr = "".join(stderr_accum)

        max_output = 10000 
        if len(stdout) > max_output:
            stdout = stdout[:max_output] + f"\n\n[TRUNCATED]"
        if len(stderr) > max_output:
            stderr = stderr[:max_output] + f"\n\n[TRUNCATED]"

>>>>>>> Stashed changes
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"

<<<<<<< Updated upstream
        if not output:
            output = "Command executed successfully. (No output printed on screen)"

        return output.strip()
    except subprocess.TimeoutExpired:
        return f"Error: Command '{command}' timed out after 60 seconds and was terminated."
=======
        return output.strip() or "Command executed successfully. (No output)"
>>>>>>> Stashed changes
    except Exception as e:
        return f"Critical error attempting to execute command '{command}': {e}"
