import logging

from pydantic import BaseModel, Field

from ...tools.worktree_tools import enter_worktree, exit_worktree
from .base import BaseTool, ToolResult

_logger = logging.getLogger("mentask.agent.tools.worktree")


class WorktreeInput(BaseModel):
    branch_name: str = Field(..., description="The name of the branch to create/use for the worktree")
    base_dir: str = Field(".mentask/worktrees", description="Base directory to store worktrees")


class EnterWorktreeTool(BaseTool):
    """Creates an isolated git worktree for focused mission execution."""

    name = "enter_worktree"
    description = (
        "Creates a git worktree for isolated code modifications. "
        "CRITICAL RULE: DO NOT use this tool for read-only tasks like 'review', 'read', or 'analyze'. "
        "Only use this if you are explicitly asked to write new code, create a feature, or fix a bug."
    )
    input_schema = WorktreeInput
    requires_confirmation = True

    async def execute(self, **kwargs) -> ToolResult:
        branch_name = kwargs.get("branch_name", "")
        base_dir = kwargs.get("base_dir", ".mentask/worktrees")
        try:
            msg = enter_worktree(branch_name, base_dir)
            return ToolResult(tool_call_id="", content=msg, is_error=False)
        except Exception as e:
            # Preserve the specific fail-fast error so the LLM gets the guardrail message
            is_dirty_error = "ERROR: The working directory is dirty" in str(e)
            content = str(e) if is_dirty_error else f"Error entering worktree: {str(e)}"
            return ToolResult(tool_call_id="", content=content, is_error=True)


class ExitWorktreeTool(BaseTool):
    """Removes a worktree and returns to the main repository root."""

    name = "exit_worktree"
    description = "Exits the current worktree, removes it from git, and returns to the main repository root."

    async def execute(self, **kwargs) -> ToolResult:
        try:
            msg = exit_worktree()
            return ToolResult(tool_call_id="", content=msg, is_error=False)
        except Exception as e:
            return ToolResult(tool_call_id="", content=f"Error exiting worktree: {str(e)}", is_error=True)
