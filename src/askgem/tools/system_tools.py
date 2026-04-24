"""
System operations tools module for the AI agent.

Provides isolated filesystem exploration and bash execution capabilities.
It does NOT handle interactive terminal sessions or streaming stdio.
"""

import asyncio
import contextlib
import platform
import shutil

_WINDOWS_SHELL = None


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

    global _WINDOWS_SHELL
    if _WINDOWS_SHELL is None:
        # Prefer pwsh (PowerShell 7+) over legacy powershell.exe
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        # Absolute fallback — cmd.exe, which is always present on Windows
        _WINDOWS_SHELL = [pwsh, "-Command"] if pwsh else ["cmd.exe", "/c"]

    return {"args": _WINDOWS_SHELL + [command], "shell": False}


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


async def _read_stream(stream, callback: callable | None, prefix: str = ""):
    """Reads from a stream line by line and sends it to the callback."""
    if not stream:
        return ""

    lines = []
    while True:
        line = await stream.readline()
        if not line:
            break

        text = line.decode(errors="replace")
        lines.append(text)
        if callback:
            # Send partial output to UI
            callback(text)

    return "".join(lines)


async def execute_bash(
    command: str, timeout: int = 60, max_output: int = 10000, output_callback: callable | None = None
) -> str:
    """
    Executes a shell command asynchronously, captures its standard output (stdout)
    and errors (stderr) in real-time.

    Args:
        command: The exact command to execute.
        timeout: Maximum execution time in seconds.
        max_output: Maximum characters to capture for the final result.
        output_callback: Optional function called for every line of output.
    """
    try:
        process = await _create_process(command)

        try:
            # Start concurrent reading of stdout and stderr
            stdout_task = asyncio.create_task(_read_stream(process.stdout, output_callback))
            stderr_task = asyncio.create_task(_read_stream(process.stderr, output_callback))

            # Wait for process to exit or timeout
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                # Force kill the process and all its children if possible
                with contextlib.suppress(Exception):
                    process.kill()
                await process.wait()
                return f"Error: Command '{command}' timed out after {timeout} seconds."

            # Finalize reading any remaining output
            stdout = await stdout_task
            stderr = await stderr_task

        except Exception as e:
            with contextlib.suppress(Exception):
                process.kill()
            return f"Error during execution: {e}"

        # Limiting output size and truncation for the final return
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
