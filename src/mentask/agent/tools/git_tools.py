from pydantic import BaseModel, Field

from ...tools.git_logic import get_staged_diff, git_commit
from ..schema import ToolResult
from .base import BaseTool


class GitCommitInput(BaseModel):
    type: str = Field(
        ...,
        description="The type of change: feat, fix, docs, style, refactor, perf, test, build, ci, chore, or revert.",
    )
    scope: str | None = Field(
        None, description="A noun describing a section of the codebase (e.g., 'parser', 'renderer')."
    )
    subject: str = Field(..., description="A short, imperative summary of the change.")
    body: str | None = Field(None, description="A detailed description of the changes.")
    stage_all: bool = Field(
        True, description="If True, all tracked and untracked changes will be staged before commit."
    )
    paths: list[str] | None = Field(
        None, description="Specific files or directories to stage (ignored if stage_all is True)."
    )


class GitCommitTool(BaseTool):
    """
    Manages git commits with a structured Conventional Commits format.
    Ensures that changes are properly staged and documented.
    """

    name = "commit_changes"
    description = (
        "Creates a git commit following the Conventional Commits standard. "
        "Use this tool to finalize a task and document your changes. "
        "It will automatically stage changes if requested."
    )
    input_schema = GitCommitInput
    requires_confirmation = True

    async def execute(
        self,
        type: str,
        subject: str,
        scope: str | None = None,
        body: str | None = None,
        stage_all: bool = True,
        paths: list[str] | None = None,
    ) -> ToolResult:
        # 1. Format the message
        header = f"{type}"
        if scope:
            header += f"({scope})"
        header += f": {subject}"

        full_message = header
        if body:
            full_message += f"\n\n{body}"

        # 2. Get a preview of what's being committed (for the tool result/history)
        preview = get_staged_diff()

        # 3. Execute commit
        result = git_commit(full_message, stage_all=stage_all, paths=paths)

        is_error = result.startswith("Error:")

        content = result
        if not is_error and preview and preview != "No staged changes.":
            content += f"\n\nSummary of committed changes:\n{preview}"

        return ToolResult(tool_call_id="", content=content, is_error=is_error)
