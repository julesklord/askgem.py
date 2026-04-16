from pydantic import BaseModel, Field
from .base import BaseTool, ToolResult
from ...tools.system_tools import execute_bash

class ShellInput(BaseModel):
    command: str = Field(..., description="The shell command to execute on the host system.")

class ShellTool(BaseTool):
    """Executes a shell command using the secure core runner."""
    name = "execute_command"
    description = (
        "Run shell commands on the host machine. Use this for building, testing, "
        "checking git status, or listing deep directory structures. Supports PowerShell (Windows) and Bash (Unix)."
    )
    input_schema = ShellInput
    requires_confirmation = True

    def __init__(self, config=None):
        self.config = config

    async def execute(self, command: str) -> ToolResult:
        timeout = 60
        if self.config:
            timeout = self.config.settings.get("bash_timeout", 60)
            
        # We cap output at 15000 chars for the agent tool to avoid extreme bloating
        result = await execute_bash(command, timeout=timeout, max_output=15000)
        is_error = "Error:" in result or "Critical error" in result
        return ToolResult(tool_call_id="", content=result, is_error=is_error)
