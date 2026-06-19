from pydantic import BaseModel, Field

from ...core.sandbox import SandboxManager
from .base import BaseTool, ToolResult


class ShellInput(BaseModel):
    command: str = Field(..., description="The shell command to execute on the host system.")


class ShellTool(BaseTool):
    """Executes a shell command using the sandbox manager."""

    name = "execute_command"
    description = (
        "Run shell commands on the host machine. Use this for building, testing, "
        "checking git status, or listing deep directory structures. Supports PowerShell (Windows) and Bash (Unix)."
    )
    input_schema = ShellInput
    requires_confirmation = True

    def __init__(self, config=None):
        self.config = config
        self.sandbox_manager = SandboxManager(config=self.config)

    async def execute(self, command: str) -> ToolResult:
        # SECURITY BLOCK: Automated git commits/pushes via shell are forbidden.
        blocked_commands = ["git commit", "git push"]
        if any(blocked in command for blocked in blocked_commands):
            return ToolResult(
                tool_call_id="",
                content="SECURITY BLOCK: Automated git commits/pushes via shell are forbidden. "
                "Do not try to clean the working directory. Ask the user for assistance.",
                is_error=True,
            )

        timeout = 60
        if self.config:
            timeout = self.config.settings.get("bash_timeout", 60)

        # Delegate execution to active sandbox manager
        exit_code, stdout, stderr = await self.sandbox_manager.execute(command, timeout=timeout)
        result_content = stdout
        if stderr:
            result_content = f"{stdout}\n\nStderr:\n{stderr}".strip()

        is_error = exit_code != 0 or "Error:" in result_content or "Critical error" in result_content
        return ToolResult(tool_call_id="", content=result_content, is_error=is_error)
