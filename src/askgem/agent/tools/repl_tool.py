import io
import logging
import sys
from typing import Any, Dict
from contextlib import redirect_stdout, redirect_stderr
from pydantic import BaseModel, Field

from ..schema import ToolResult
from .base import BaseTool

_logger = logging.getLogger("askgem")

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
        # Persistent state across tool calls in the same session
        self.globals = {
            "__name__": "__main__",
            "__doc__": None,
            "__package__": None,
            "__loader__": None,
            "__spec__": None,
        }

    async def execute(self, code: str) -> ToolResult:
        output = io.StringIO()
        error = io.StringIO()

        try:
            with redirect_stdout(output), redirect_stderr(error):
                # We use exec for multi-line support and persistent state
                exec(code, self.globals)
            
            result = output.getvalue()
            err_result = error.getvalue()
            
            if err_result:
                return ToolResult(tool_call_id="", content=f"Output:\n{result}\n\nErrors/Stderr:\n{err_result}", is_error=True)
            
            return ToolResult(tool_call_id="", content=result if result else "Code executed successfully (no output).", is_error=False)
            
        except Exception as e:
            import traceback
            return ToolResult(tool_call_id="", content=f"Execution Error:\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}", is_error=True)
        finally:
            output.close()
            error.close()
