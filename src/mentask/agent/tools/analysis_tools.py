import logging

from pydantic import BaseModel, Field

from ...tools.analysis_logic import detect_project_blueprint, get_git_diff_stat, get_repo_structure
from ..schema import ToolResult
from .base import BaseTool

_logger = logging.getLogger("mentask.agent.analysis_tools")

_MAX_OUTPUT_CHARS = 8000


class AnalysisInput(BaseModel):
    mode: str = Field(
        "stat",
        description="The analysis mode: 'stat' for diff summary, 'map' for repo structure, 'blueprint' for tech stack, 'full' for all.",
    )
    base_ref: str = Field(
        "HEAD", description="The git reference to compare against (e.g. 'main', 'HEAD~1'). Only used in 'stat' mode."
    )


class AnalyzeTool(BaseTool):
    """
    Analyzes the repository to provide a high-level overview of changes and structure.
    Use this to identify which files are relevant before reading large amounts of code.
    """

    name = "analyze_codebase"
    description = (
        "Provides a high-level summary of the repository. "
        "Use 'stat' to see what changed, 'map' to see the file tree, or 'blueprint' to see the tech stack. "
        "This tool helps you save tokens by identifying critical files before reading them."
    )
    input_schema = AnalysisInput

    async def execute(self, mode: str = "stat", base_ref: str = "HEAD") -> ToolResult:  # type: ignore[override]
        output = []

        if mode in ("stat", "full"):
            output.append(f"--- GIT DIFF STAT ({base_ref}) ---")
            output.append(get_git_diff_stat(base_ref))

        if mode in ("map", "full"):
            output.append("\n--- REPOSITORY MAP ---")
            output.append(get_repo_structure(max_files=200))

        if mode in ("blueprint", "full"):
            output.append("\n--- PROJECT BLUEPRINT ---")
            output.append(detect_project_blueprint())

        content = "\n".join(output)
        is_error = "Error:" in content

        if len(content) > _MAX_OUTPUT_CHARS:
            truncated = content[:_MAX_OUTPUT_CHARS]
            omitted = len(content) - _MAX_OUTPUT_CHARS
            content = truncated + f"\n\n[TRUNCATED: {omitted} chars omitted — use 'stat' or 'map' individually to avoid overflow]"
            _logger.info("analyze_codebase output truncated (%d chars -> %d)", len(output), _MAX_OUTPUT_CHARS)

        return ToolResult(tool_call_id="", content=content, is_error=is_error)
