from pydantic import BaseModel, Field

from ...tools.search_tools import glob_find, grep_search
from ..schema import ToolResult
from .base import BaseTool


class GrepSearchInput(BaseModel):
    pattern: str = Field(..., description="The text or regex pattern to search for.")
    path: str = Field(".", description="The root directory to start searching from.")
    is_regex: bool = Field(False, description="If True, treats pattern as a regular expression.")
    case_sensitive: bool = Field(False, description="If True, performs case-sensitive matching.")


class GrepSearchTool(BaseTool):
    """Recursively searches for a text pattern within files in a directory."""

    name = "grep_search"
    description = (
        "Search for a specific text pattern or regex inside all files in a directory "
        "(recursively). Useful for finding function definitions, variables, or specific "
        "logic across the entire codebase."
    )
    input_schema = GrepSearchInput
    requires_confirmation = False

    async def execute(
        self, pattern: str, path: str = ".", is_regex: bool = False, case_sensitive: bool = False
    ) -> ToolResult:
        result = grep_search(pattern, path, is_regex, case_sensitive)
        return ToolResult(tool_call_id="", content=result)


class GlobFindInput(BaseModel):
    pattern: str = Field(..., description="The glob pattern (e.g., '*.py', '**/tests/*.md').")
    path: str = Field(".", description="The root directory to search.")


class GlobFindTool(BaseTool):
    """Finds files matching a glob pattern recursively."""

    name = "glob_find"
    description = (
        "Find file paths matching a pattern (e.g., all .py files, or files in a specific folder). "
        "Supports recursive patterns like '**/*.md'."
    )
    input_schema = GlobFindInput
    requires_confirmation = False

    async def execute(self, pattern: str, path: str = ".") -> ToolResult:
        result = glob_find(pattern, path)
        return ToolResult(tool_call_id="", content=result)
