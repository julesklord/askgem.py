import ast

from pydantic import BaseModel, Field

from ...core.paths import get_plugins_dir
from ..schema import ToolResult
from .base import BaseTool, ToolRegistry


class ForgePluginInput(BaseModel):
    plugin_name: str = Field(
        ...,
        description="The internal name for the plugin file (e.g., 'uvr_handler', 'csv_parser'). Must be a valid Python filename without the .py extension.",
    )
    code: str = Field(
        ...,
        description="The complete, self-contained Python code for the plugin. It MUST include imports and a class that inherits from BaseTool.",
    )


class ForgePluginTool(BaseTool):
    """
    Meta-tool that allows the agent to create, save, and hot-reload new tools (plugins) dynamically.
    """

    name = "forge_plugin"
    description = (
        "Creates or updates a dynamic agent tool (plugin) by writing its Python code to the user's workspace "
        "and hot-reloading the ToolRegistry. Use this to permanently extend your capabilities. "
        "The provided code MUST define a class inheriting from BaseTool and implement the 'execute' method."
    )
    input_schema = ForgePluginInput
    requires_confirmation = True  # Always ask the user before the agent self-modifies

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def execute(self, plugin_name: str, code: str, **kwargs) -> ToolResult:
        # Validate plugin name
        if not plugin_name.isidentifier():
            return ToolResult(
                tool_call_id="",
                content=f"Error: Invalid plugin name '{plugin_name}'. It must be a valid Python identifier.",
                is_error=True,
            )

        plugins_dir = get_plugins_dir()
        file_path = plugins_dir / f"{plugin_name}.py"

        # 1. Basic Syntax Validation
        try:
            ast.parse(code)
        except SyntaxError as e:
            return ToolResult(
                tool_call_id="",
                content=f"Syntax Error in the provided plugin code:\nLine {e.lineno}: {e.msg}\n{e.text}",
                is_error=True,
            )

        # 2. Write the file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
        except Exception as e:
            return ToolResult(
                tool_call_id="",
                content=f"Error writing plugin file to {file_path}: {e}",
                is_error=True,
            )

        # 3. Hot-Reload the Registry
        try:
            loaded_count = self.registry.refresh_dynamic_plugins()
            return ToolResult(
                tool_call_id="",
                content=(
                    f"Success! Plugin '{plugin_name}.py' forged and saved to {file_path}.\n"
                    f"Hot-reload triggered. Total dynamic plugins currently loaded: {loaded_count}.\n"
                    f"You now have access to the newly created tool in your schema."
                ),
                is_error=False,
            )
        except Exception as e:
            return ToolResult(
                tool_call_id="",
                content=f"Plugin saved, but failed to hot-reload the registry: {e}",
                is_error=True,
            )
