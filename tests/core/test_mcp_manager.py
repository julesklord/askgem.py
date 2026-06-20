"""Unit tests for MCPManager.

These tests verify connection lifecycle management without requiring real
MCP servers.  All external I/O is mocked.
"""

from contextlib import AsyncExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mentask.core.mcp_manager import MCPManager


async def test_connect_all_delegates_to_connect_stdio() -> None:
    """connect_all() should call connect_stdio once per configured server."""
    config = MagicMock()
    config.settings = {"mcp_servers": {"test_server": {"command": "node", "args": ["server.js"]}}}

    manager = MCPManager(config)
    with patch.object(manager, "connect_stdio", new_callable=AsyncMock) as mock_connect:
        await manager.connect_all()
        mock_connect.assert_called_once_with("test_server", "node", ["server.js"])


async def test_connect_all_skips_server_with_no_command() -> None:
    """connect_all() should skip servers missing the 'command' key."""
    config = MagicMock()
    config.settings = {"mcp_servers": {"bad_server": {"args": ["server.js"]}}}

    manager = MCPManager(config)
    with patch.object(manager, "connect_stdio", new_callable=AsyncMock) as mock_connect:
        await manager.connect_all()
        mock_connect.assert_not_called()


async def test_call_tool_returns_error_when_not_found() -> None:
    """call_tool() should return an error string for unknown tools."""
    manager = MCPManager()
    result = await manager.call_tool("unknown_tool", {})
    assert "not found" in result


async def test_shutdown_closes_exit_stack() -> None:
    """shutdown() must call aclose() on each server's AsyncExitStack.

    With the new AsyncExitStack architecture the MCPManager stores
    (stack, session) pairs.  The stack is responsible for tearing down both
    the transport and the session, so we verify that ``stack.aclose()`` is
    called — not ``session.__aexit__`` directly.
    """
    manager = MCPManager()

    mock_stack = AsyncMock(spec=AsyncExitStack)
    mock_session = AsyncMock()

    manager._server_contexts["test_server"] = (mock_stack, mock_session)

    await manager.shutdown()

    # The stack's aclose() must be called exactly once
    mock_stack.aclose.assert_called_once()

    # After shutdown the internal registry should be empty
    assert manager._server_contexts == {}
    assert manager._tools_cache == {}


async def test_shutdown_continues_after_error_in_one_server() -> None:
    """shutdown() should attempt to close all servers even if one raises."""
    manager = MCPManager()

    failing_stack = AsyncMock(spec=AsyncExitStack)
    failing_stack.aclose.side_effect = RuntimeError("connection lost")

    ok_stack = AsyncMock(spec=AsyncExitStack)

    manager._server_contexts["failing"] = (failing_stack, AsyncMock())
    manager._server_contexts["ok"] = (ok_stack, AsyncMock())

    # Should not raise even when one server fails
    await manager.shutdown()

    failing_stack.aclose.assert_called_once()
    ok_stack.aclose.assert_called_once()


async def test_get_all_tools_logs_warning_on_failure(caplog: pytest.LogCaptureFixture) -> None:
    """get_all_tools() should log a warning when a server call fails."""
    import logging

    manager = MCPManager()
    broken_session = AsyncMock()
    broken_session.list_tools.side_effect = RuntimeError("broken pipe")

    broken_stack = AsyncMock(spec=AsyncExitStack)
    manager._server_contexts["broken"] = (broken_stack, broken_session)

    with caplog.at_level(logging.WARNING, logger="mentask"):
        tools = await manager.get_all_tools()

    assert tools == []
    assert any("broken" in record.message for record in caplog.records)
