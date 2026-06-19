import json
import logging
import subprocess
import sys

from pydantic import BaseModel, Field

from ..schema import ToolResult
from .base import BaseTool

_logger = logging.getLogger("mentask")


class SandboxProcess:
    """A subprocess that executes Python code in a restricted environment."""

    def __init__(self):
        sandbox_script = """
import sys
import io
import json
import traceback
from contextlib import redirect_stdout, redirect_stderr

def audit_hook(event, args):
    FORBIDDEN_EVENTS = {
        "os.system",
        "os.exec",
        "os.posix_spawn",
        "os.spawn",
        "subprocess.Popen",
        "os.rename",
        "os.replace",
        "os.remove",
        "os.unlink",
        "os.rmdir",
        "shutil.rmtree",
        "os.chmod",
        "os.chown",
    }
    if event in FORBIDDEN_EVENTS:
        raise PermissionError(f"Action '{event}' is forbidden in the sandbox.")

    if event == "open" and len(args) >= 2:
        mode = args[1]
        if isinstance(mode, str) and any(c in mode for c in "wa+x"):
            raise PermissionError(f"File write access is forbidden.")

    if event == "socket.connect" or event == "socket.bind":
        raise PermissionError(f"Network access is forbidden.")

sys.addaudithook(audit_hook)

globals_dict = {
    "__name__": "__main__",
    "__doc__": None,
    "__package__": None,
    "__loader__": None,
    "__spec__": None,
}

while True:
    line = sys.stdin.readline()
    if not line:
        break
    try:
        req = json.loads(line)
        code = req.get("code", "")

        output = io.StringIO()
        error = io.StringIO()

        try:
            with redirect_stdout(output), redirect_stderr(error):
                compiled_code = compile(code, "<string>", "exec")
                exec(compiled_code, globals_dict)
            res = {
                "stdout": output.getvalue(),
                "stderr": error.getvalue(),
                "error": None
            }
        except Exception as e:
            res = {
                "stdout": output.getvalue(),
                "stderr": error.getvalue(),
                "error": f"{type(e).__name__}: {str(e)}\\n{traceback.format_exc()}"
            }
        finally:
            output.close()
            error.close()

        sys.stdout.write(json.dumps(res) + "\\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stderr.write(f"Error in sandbox loop: {e}\\n")
"""
        self.proc = subprocess.Popen(
            [sys.executable, "-c", sandbox_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def execute(self, code: str) -> dict:
        if self.proc.poll() is not None:
            # Subprocess died, restart it
            self.__init__()

        try:
            # We must escape newlines when passing JSON via line based IO, but json.dumps does this automatically.
            self.proc.stdin.write(json.dumps({"code": code}) + "\n")
            self.proc.stdin.flush()

            line = self.proc.stdout.readline()
            if not line:
                stderr_out = self.proc.stderr.read()
                return {"error": f"Sandbox process died unexpectedly.\nStderr: {stderr_out}"}

            return json.loads(line)
        except Exception as e:
            return {"error": f"Failed to communicate with sandbox: {str(e)}"}

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait()


class PythonReplInput(BaseModel):
    code: str = Field(..., description="The Python code to execute. Standard output is captured and returned.")


class PythonReplTool(BaseTool):
    """
    A Python REPL tool that allows the agent to execute Python code in a persistent session.
    Useful for testing snippets, performing calculations, or validating logic.
    """

    name = "python_repl"
    description = "Executes Python code and returns the standard output. Use this to test snippets, validate logic, or perform complex calculations. State is persistent across calls."
    input_schema = PythonReplInput

    def __init__(self):
        self.sandbox = SandboxProcess()

    def __del__(self):
        if hasattr(self, "sandbox"):
            self.sandbox.close()

    async def execute(self, code: str) -> ToolResult:  # type: ignore[override]
        result = self.sandbox.execute(code)

        err = result.get("error")
        if err:
            return ToolResult(tool_call_id="", content=f"Execution Error:\n{err}", is_error=True)

        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")

        if stderr:
            return ToolResult(tool_call_id="", content=f"Output:\n{stdout}\n\nErrors/Stderr:\n{stderr}", is_error=True)

        return ToolResult(
            tool_call_id="", content=stdout if stdout else "Code executed successfully (no output).", is_error=False
        )
