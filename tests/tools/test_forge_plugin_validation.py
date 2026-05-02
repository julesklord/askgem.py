from unittest.mock import MagicMock, patch

import pytest

from mentask.agent.tools.base import ToolRegistry
from mentask.agent.tools.plugin_tools import ForgePluginTool


@pytest.mark.asyncio
async def test_forge_plugin_validation_success():
    registry = MagicMock(spec=ToolRegistry)
    tool = ForgePluginTool(registry)

    code = """
from mentask.agent.tools.base import BaseTool
class MyNewTool(BaseTool):
    name = "my_new_tool"
    async def execute(self, **kwargs):
        return "ok"
"""
    with (
        patch("mentask.agent.tools.plugin_tools.get_plugins_dir", return_value=MagicMock()),
        patch("builtins.open", MagicMock()),
    ):
        result = await tool.execute(plugin_name="my_plugin", code=code)

    assert not result.is_error
    assert "Success" in result.content


@pytest.mark.asyncio
async def test_forge_plugin_validation_missing_basetool():
    registry = MagicMock(spec=ToolRegistry)
    tool = ForgePluginTool(registry)

    code = """
class NotATool:
    pass
"""
    result = await tool.execute(plugin_name="my_plugin", code=code)

    assert result.is_error
    assert "MUST define at least one class inheriting from BaseTool" in result.content


@pytest.mark.asyncio
async def test_forge_plugin_validation_syntax_error():
    registry = MagicMock(spec=ToolRegistry)
    tool = ForgePluginTool(registry)

    code = "class Invalid Tool:"  # Space in name
    result = await tool.execute(plugin_name="my_plugin", code=code)

    assert result.is_error
    assert "Syntax Error" in result.content
