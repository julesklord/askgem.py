import abc
from typing import Any

from pydantic import BaseModel

from ..schema import ToolResult


class BaseTool(abc.ABC):
    """Base class for all mentask tools."""

    name: str
    description: str
    input_schema: type[BaseModel] | None = None
    requires_confirmation: bool = False

    def get_json_schema(self) -> dict[str, Any]:
        """Generates the JSON schema for the tool's input."""
        if self.input_schema:
            return self.input_schema.model_json_schema()
        if hasattr(self, "parameters"):
            return self.parameters
        return {"type": "object", "properties": {}}

    @abc.abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Executes the tool logic."""
        pass


class ToolRegistry:
    """Registry to manage and discover tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._plugin_loader = None

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def load_dynamic_plugins(self) -> int:
        """Initializes the plugin loader and discovers dynamic user tools."""
        from ...core.plugin_loader import PluginLoader
        
        if self._plugin_loader is None:
            self._plugin_loader = PluginLoader(self)
        
        return self._plugin_loader.discover_and_load()

    def refresh_dynamic_plugins(self) -> int:
        """Forces a refresh of all dynamic plugins for hot-reloading."""
        if self._plugin_loader:
            return self._plugin_loader.refresh()
        return self.load_dynamic_plugins()

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_all_schemas(self) -> list[dict[str, Any]]:
        """Returns all registered tool schemas for the LLM."""
        return [
            {"name": t.name, "description": t.description, "parameters": t.get_json_schema()}
            for t in self._tools.values()
        ]

    async def call_tool(self, name: str, tool_call_id: str, arguments: dict[str, Any]) -> ToolResult:
        """Executes a tool call and returns a ToolResult."""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(tool_call_id=tool_call_id, content=f"Error: Tool '{name}' not found.", is_error=True)

        try:
            # Validate arguments if a schema exists
            validated_args = tool.input_schema(**arguments).model_dump() if tool.input_schema else arguments

            result = await tool.execute(**validated_args)
            # Ensure the result has the correct tool_call_id
            result.tool_call_id = tool_call_id
            return result
        except Exception as e:
            return ToolResult(tool_call_id=tool_call_id, content=f"Error executing '{name}': {str(e)}", is_error=True)
