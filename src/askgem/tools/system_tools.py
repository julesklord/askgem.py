"""
System operations tools module for the AI agent.

Provides isolated filesystem exploration and bash execution capabilities.
It does NOT handle interactive terminal sessions or streaming stdio.
"""

import asyncio
import platform
import shlex
import shutil


def _get_shell_args(command: str) -> dict:
    """
    Returns the appropriate subprocess keyword arguments for the current OS.

    Windows: Routes through PowerShell (pwsh or powershell.exe) by building
             an explicit argument list [pwsh, '-Command', command] with
             shell=False.
             Falls back to cmd.exe.
    Unix:    Uses /bin/bash explicitly.
    """
    if platform.system() != "Windows":
        return {"args": ["/bin/bash", "-c", command], "shell": False}

    # Prefer pwsh (PowerShell 7+) over legacy powershell.exe
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if pwsh:
        # Build explicit arg list so subprocess never splits the executable path
        return {"args": [pwsh, "-Command", command], "shell": False}

    # Absolute fallback — cmd.exe, which is always present on Windows
    return {"args": ["cmd.exe", "/c", command], "shell": False}


async def _create_process(command: str) -> asyncio.subprocess.Process:
    """Creates a subprocess using platform-specific shell arguments."""
    shell_kwargs = _get_shell_args(command)
    run_args = shell_kwargs.pop("args")
    is_shell = shell_kwargs.get("shell", False)

    if is_shell:
        return await asyncio.create_subprocess_shell(
            run_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    else:
        # run_args is a list for create_subprocess_exec
        return await asyncio.create_subprocess_exec(
            *run_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

async def execute_bash(command: str) -> str:
    """
    Executes a shell command asynchronously, captures its standard output (stdout)
    and errors (stderr), and returns them as text.

    On Windows the command is explicitly routed through PowerShell (if available) so that
    commands like `ls`, `cat`, `grep` behave consistently across platforms.

    WARNING: Use primarily for safe script executions, automated testing,
    git status checks, version checks, or compilations.

    Args:
        command: The exact command to execute in the local user's terminal.

    Returns:
        The output of the executed command or a failure message if the command crashes or isn't found.
    """
    try:
        process = await _create_process(command)

        try:
            # wait_for returns (stdout, stderr) after process finishes
            stdout_data, stderr_data = await asyncio.wait_for(process.communicate(), timeout=60)
        except asyncio.TimeoutError:
            try:
                process.kill()
            except Exception:
                pass
            return f"Error: Command '{command}' timed out after 60 seconds."

        # Decoding
        stdout = stdout_data.decode(errors="replace")
        stderr = stderr_data.decode(errors="replace")

        # Limiting output size and truncation
        max_output = 10000
        if len(stdout) > max_output:
            stdout = stdout[:max_output] + f"\n\n[TRUNCATED: {len(stdout) - max_output} more characters]"
        if len(stderr) > max_output:
            stderr = stderr[:max_output] + f"\n\n[TRUNCATED: {len(stderr) - max_output} more characters]"

        output = ""
        if stdout:
            output += f"STDOUT:\n{stdout}\n"
        if stderr:
            output += f"STDERR:\n{stderr}\n"

        if not output:
            output = "Command executed successfully. (No output printed on screen)"

        return output.strip()
    except Exception as e:
        return f"Critical error attempting to execute command '{command}': {e}"
