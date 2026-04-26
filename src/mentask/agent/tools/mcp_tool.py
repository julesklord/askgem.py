import logging
from typing import Any

from ..schema import ToolResult
from .base import BaseTool

_logger = logging.getLogger("mentask")


class MCPToolWrapper(BaseTool):
    """
    A dynamic wrapper that represents a tool from an MCP server.
    """

    def __init__(self, mcp_manager, tool_info: Any):
        self.mcp_manager = mcp_manager
        self.name = tool_info.name
        self.description = tool_info.description
        self._input_schema_dict = tool_info.inputSchema

    def get_json_schema(self) -> dict[str, Any]:
        return self._input_schema_dict

    async def execute(self, **kwargs) -> ToolResult:
        try:
            result_str = await self.mcp_manager.call_tool(self.name, kwargs)
            is_error = result_str.startswith("Error:")
            return ToolResult(tool_call_id="", content=result_str, is_error=is_error)
        except Exception as e:
            return ToolResult(tool_call_id="", content=f"MCP Execution Error: {str(e)}", is_error=True)
