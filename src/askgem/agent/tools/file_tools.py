from pydantic import BaseModel, Field
from .base import BaseTool
from ..schema import ToolResult
from ...tools.file_tools import read_file, edit_file, list_directory

class ListDirInput(BaseModel):
    path: str = Field(".", description="The directory path to list contents of.")

class ListDirTool(BaseTool):
    name = "list_dir"
    description = "Lists files and subdirectories in a given directory."
    input_schema = ListDirInput

    async def execute(self, path: str = ".") -> ToolResult:
        result = list_directory(path)
        is_error = result.startswith("Error:")
        return ToolResult(tool_call_id="", content=result, is_error=is_error)

class ReadFileInput(BaseModel):
    path: str = Field(..., description="The path to the file to read.")
    start_line: int | None = Field(None, description="1-indexed line number to start from.")
    end_line: int | None = Field(None, description="1-indexed line number to stop at.")

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Reads the content of a text file. Supports line ranges to prevent context explosion."
    input_schema = ReadFileInput

    def __init__(self, config=None):
        self.config = config

    async def execute(self, path: str, start_line: int | None = None, end_line: int | None = None) -> ToolResult:
        char_limit = 30000
        if self.config:
            char_limit = self.config.settings.get("max_file_read_size", 30000)
            
        result = read_file(path, start_line, end_line, char_limit=char_limit)
        is_error = result.startswith("Error:")
        return ToolResult(tool_call_id="", content=result, is_error=is_error)

class EditFileInput(BaseModel):
    path: str = Field(..., description="The path to the file to edit.")
    find_text: str = Field(..., description="The EXACT literal string block to replace.")
    replace_text: str = Field(..., description="The new content to insert.")

class EditFileTool(BaseTool):
    name = "edit_file"
    description = "Edits a file by replacing an exact block of code. Atomic and safe."
    input_schema = EditFileInput
    requires_confirmation = True

    async def execute(self, path: str, find_text: str, replace_text: str) -> ToolResult:
        result = edit_file(path, find_text, replace_text)
        is_error = result.startswith("Error:")
        return ToolResult(tool_call_id="", content=result, is_error=is_error)

class WriteFileInput(BaseModel):
    path: str = Field(..., description="The path to the file to create.")
    content: str = Field(..., description="The full content to write.")

class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Creates a new file with the specified content. Use edit_file for existing files."
    input_schema = WriteFileInput
    requires_confirmation = True

    async def execute(self, path: str, content: str) -> ToolResult:
        # We reuse edit_file with empty find_text for creation logic
        result = edit_file(path, "", content)
        is_error = result.startswith("Error:")
        return ToolResult(tool_call_id="", content=result, is_error=is_error)
