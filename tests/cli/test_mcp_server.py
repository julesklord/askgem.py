from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mentask.agent.schema import ToolResult
from mentask.cli.mcp_server import main, serve


@pytest.mark.asyncio
async def test_mcp_server_serve():
    mock_agent = MagicMock()
    mock_registry = MagicMock()
    mock_agent.tools = mock_registry

    # Mock schemas list
    mock_registry.get_all_schemas.return_value = [
        {"name": "test_tool", "description": "A test tool", "parameters": {"type": "object"}}
    ]

    # Mock execution result
    mock_result = ToolResult(content="tool output", is_error=False)
    mock_registry.call_tool = AsyncMock(return_value=mock_result)

    # Mock server
    mock_server_instance = MagicMock()
    mock_server_instance.run = AsyncMock()

    # Mock stdio_server context manager
    mock_read = MagicMock()
    mock_write = MagicMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = (mock_read, mock_write)

    with (
        patch("mentask.cli.mcp_server.ChatAgent", return_value=mock_agent),
        patch("mentask.cli.mcp_server.Server", return_value=mock_server_instance),
        patch("mentask.cli.mcp_server.stdio_server", return_value=mock_ctx),
    ):
        await serve()

    # Verify ChatAgent is initialized and plugins loaded
    mock_agent.tools.load_dynamic_plugins.assert_called_once()

    # Retrieve decorator return values where the real handler functions are registered
    mock_list_dec = mock_server_instance.list_tools.return_value
    mock_call_dec = mock_server_instance.call_tool.return_value

    assert mock_list_dec.called
    assert mock_call_dec.called

    # Extract the registered handler functions
    list_tools_handler = mock_list_dec.call_args[0][0]
    call_tool_handler = mock_call_dec.call_args[0][0]

    # Test list tools handler
    res_tools = await list_tools_handler()
    assert len(res_tools) == 1
    assert res_tools[0].name == "test_tool"
    assert res_tools[0].description == "A test tool"

    # Test call tool handler (success case)
    res_call = await call_tool_handler("test_tool", {"arg": 1})
    mock_registry.call_tool.assert_called_once_with("test_tool", "mcp_call", {"arg": 1})
    assert res_call.isError is False
    assert res_call.content[0].text == "tool output"

    # Test call tool handler (error case)
    mock_registry.call_tool.side_effect = Exception("failed execution")
    res_err_call = await call_tool_handler("test_tool", {"arg": 1})
    assert res_err_call.isError is True
    assert "Error executing tool" in res_err_call.content[0].text


def test_mcp_server_main():
    with (
        patch("mentask.cli.mcp_server.serve", new_callable=MagicMock),
        patch("asyncio.run") as mock_asyncio_run,
    ):
        main()

    mock_asyncio_run.assert_called_once()
