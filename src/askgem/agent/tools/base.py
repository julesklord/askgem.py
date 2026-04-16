import abc
from typing import Any

from pydantic import BaseModel

from ..schema import ToolResult


class BaseTool(abc.ABC):
    """Base class for all AskGem tools."""

    name: str
    description: str
    input_schema: type[BaseModel] | None = None
    requires_confirmation: bool = False

    def get_json_schema(self) -> dict[str, Any]:
        """Generates the JSON schema for the tool's input."""
        if self.input_schema:
            return self.input_schema.model_json_schema()
        return {"type": "object", "properties": {}}

    @abc.abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Executes the tool logic."""
        pass

class ToolRegistry:
    """Registry to manage and discover tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_all_schemas(self) -> list[dict[str, Any]]:
        """Returns all registered tool schemas for the LLM."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.get_json_schema()
            }
            for t in self._tools.values()
        ]

    async def call_tool(self, name: str, tool_call_id: str, arguments: dict[str, Any]) -> ToolResult:
        """Executes a tool call and returns a ToolResult."""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Error: Tool '{name}' not found.",
                is_error=True
            )

        try:
            # Validate arguments if a schema exists
            validated_args = tool.input_schema(**arguments).model_dump() if tool.input_schema else arguments

            result = await tool.execute(**validated_args)
            # Ensure the result has the correct tool_call_id
            result.tool_call_id = tool_call_id
            return result
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=f"Error executing '{name}': {str(e)}",
                is_error=True
            )
