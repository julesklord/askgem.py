from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from src.askgem.agent.schema import ToolResult
from src.askgem.agent.tools.base import BaseTool, ToolRegistry


class MockArgs(BaseModel):
    param1: str


class MockTool(BaseTool):
    name = "mock_tool"
    description = "A test tool"
    input_schema = MockArgs

    async def execute(self, param1: str) -> ToolResult:
        return ToolResult(tool_call_id="", content=f"Processed {param1}")


class SimpleTool(BaseTool):
    name = "simple"
    description = "No schema"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(tool_call_id="", content="Simple success")


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        assert registry.get_tool("mock_tool") == tool
        assert registry.get_tool("missing") is None

    def test_get_all_schemas(self):
        registry = ToolRegistry()
        registry.register(MockTool())

        schemas = registry.get_all_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "mock_tool"
        assert "parameters" in schemas[0]
        assert "param1" in schemas[0]["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        registry = ToolRegistry()
        registry.register(MockTool())

        result = await registry.call_tool("mock_tool", "call_123", {"param1": "test_value"})

        assert result.tool_call_id == "call_123"
        assert result.content == "Processed test_value"
        assert result.is_error is False

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self):
        registry = ToolRegistry()
        result = await registry.call_tool("missing", "call_123", {})

        assert result.is_error is True
        assert "not found" in result.content

    @pytest.mark.asyncio
    async def test_call_tool_validation_error(self):
        registry = ToolRegistry()
        registry.register(MockTool())

        # Missing required param1
        result = await registry.call_tool("mock_tool", "call_123", {})

        assert result.is_error is True
        assert "Error executing" in result.content

    @pytest.mark.asyncio
    async def test_call_tool_execution_exception(self):
        registry = ToolRegistry()
        tool = MockTool()
        # Mocking execute to raise an error
        tool.execute = MagicMock(side_effect=Exception("Runtime crash"))
        registry.register(tool)

        result = await registry.call_tool("mock_tool", "call_123", {"param1": "val"})

        assert result.is_error is True
        assert "Runtime crash" in result.content

    @pytest.mark.asyncio
    async def test_call_tool_without_schema(self):
        registry = ToolRegistry()
        registry.register(SimpleTool())

        result = await registry.call_tool("simple", "call_123", {"extra": "ignored"})
        assert result.content == "Simple success"
        assert result.is_error is False
