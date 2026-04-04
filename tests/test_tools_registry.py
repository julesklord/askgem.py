"""Tests for askgem.agent.tools_registry."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types

from askgem.agent.tools_registry import ToolDispatcher


# --- Dummy tool functions for testing ---
def dummy_sync_tool(arg1="default"):
    """Dummy sync tool."""
    return f"Sync tool executed with {arg1}"


async def dummy_async_tool(arg1="default"):
    """Dummy async tool."""
    return f"Async tool executed with {arg1}"


@pytest.fixture
def mock_console():
    with patch("askgem.agent.tools_registry.console") as mock:
        yield mock


@pytest.fixture
def mock_status():
    with patch("askgem.agent.tools_registry.Status") as mock:
        mock.return_value.__enter__.return_value = MagicMock()
        yield mock


@pytest.fixture
def dispatcher():
    dispatcher = ToolDispatcher(edit_mode="manual")
    # Replace actual tools with mock tools for isolation
    dispatcher._tools = [dummy_sync_tool, dummy_async_tool]
    dispatcher._tool_map = {
        "dummy_sync_tool": dummy_sync_tool,
        "dummy_async_tool": dummy_async_tool,
        "delete_file": AsyncMock(return_value="File deleted"),
        "move_file": AsyncMock(return_value="File moved"),
        "execute_bash": AsyncMock(return_value="Command executed"),
        "edit_file": MagicMock(return_value="Success: File edited"),  # Note edit_file is run sync
    }
    return dispatcher


class TestToolDispatcher:
    def test_init_and_get_tools_list(self):
        """Test ToolDispatcher initialization and get_tools_list."""
        dispatcher = ToolDispatcher(search_api_key="test_key", search_cx_id="test_cx")
        tools = dispatcher.get_tools_list()

        # Verify it loaded the default tools
        assert len(tools) > 0
        assert any(t.__name__ == "list_directory" for t in tools if hasattr(t, "__name__"))

        # Verify web_search partial binding works
        assert "web_search" in dispatcher._tool_map
        assert dispatcher._tool_map["web_search"].func.__name__ == "web_search"
        assert dispatcher._tool_map["web_search"].keywords == {"api_key": "test_key", "cx_id": "test_cx"}

    @pytest.mark.asyncio
    async def test_execute_routes_and_returns_part(self, dispatcher, mock_console, mock_status):
        """Test the main execute loop routing correctly and formatting the result."""
        fc = types.FunctionCall(name="dummy_sync_tool", args={"arg1": "test_arg"})

        result_part = await dispatcher.execute(fc)

        assert isinstance(result_part, types.Part)
        assert result_part.function_response.name == "dummy_sync_tool"
        assert result_part.function_response.response["result"] == "Sync tool executed with test_arg"

    @pytest.mark.asyncio
    async def test_execute_truncates_large_output(self, dispatcher, mock_console, mock_status):
        """Test that outputs larger than 10000 characters are truncated."""
        large_output = "A" * 15000
        dispatcher._tool_map["large_tool"] = MagicMock(return_value=large_output)

        fc = types.FunctionCall(name="large_tool", args={})
        result_part = await dispatcher.execute(fc)

        result_text = result_part.function_response.response["result"]
        assert len(result_text) < 15000
        assert len(result_text) == 10000 + len("\n\n[RESULTADO TRUNCADO POR SEGURIDAD]")
        assert result_text.endswith("[RESULTADO TRUNCADO POR SEGURIDAD]")

    @pytest.mark.asyncio
    async def test_execute_with_logger(self, mock_console, mock_status):
        """Test that execution logs to the provided logger."""
        logger_mock = MagicMock()
        dispatcher = ToolDispatcher(logger=logger_mock)
        dispatcher._tool_map = {"dummy_tool": MagicMock(return_value="test_result")}

        fc = types.FunctionCall(name="dummy_tool", args={"arg": "val"})
        await dispatcher.execute(fc)

        assert logger_mock.call_count == 2  # Start and end logs
        assert "Tool Call:" in logger_mock.call_args_list[0][0][0]
        assert "Tool Result:" in logger_mock.call_args_list[1][0][0]

    @pytest.mark.asyncio
    async def test_dispatch_unregistered_tool(self, dispatcher):
        """Test dispatching an unknown tool returns an error message."""
        result = await dispatcher._dispatch("unknown_tool", {})
        assert "not found" in result.lower() or "unregistered" in result.lower() or "not registered" in result.lower()

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.Confirm.ask")
    async def test_dispatch_interactive_tool_confirm(self, mock_confirm, dispatcher, mock_console):
        """Test interactive tool requiring confirmation and proceeding."""
        mock_confirm.return_value = True  # User confirmed

        # Test delete_file
        with patch("askgem.agent.tools_registry.delete_file", MagicMock(return_value="Deleted")):
            result = await dispatcher._dispatch("delete_file", {"path": "test.txt"})
            assert result == "Deleted"
            mock_confirm.assert_called_once()

        mock_confirm.reset_mock()

        # Test move_file
        with patch("askgem.agent.tools_registry.move_file", MagicMock(return_value="Moved")):
            result = await dispatcher._dispatch("move_file", {"source": "a.txt", "destination": "b.txt"})
            assert result == "Moved"
            mock_confirm.assert_called_once()

        mock_confirm.reset_mock()

        # Test execute_bash
        with patch("askgem.agent.tools_registry.execute_bash", AsyncMock(return_value="Bash output")):
            result = await dispatcher._dispatch("execute_bash", {"command": "ls"})
            assert result == "Bash output"
            mock_confirm.assert_called_once()

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.Confirm.ask")
    async def test_dispatch_interactive_tool_deny(self, mock_confirm, dispatcher, mock_console):
        """Test interactive tool requiring confirmation but user denies."""
        mock_confirm.return_value = False  # User denied

        result = await dispatcher._dispatch("delete_file", {"path": "test.txt"})
        assert "denied" in result.lower()

    @pytest.mark.asyncio
    async def test_dispatch_interactive_tool_auto_mode(self, mock_console):
        """Test interactive tool when edit_mode is auto (should bypass confirm)."""
        dispatcher = ToolDispatcher(edit_mode="auto")
        dispatcher._tool_map = {"edit_file": MagicMock(return_value="Success: edited")}

        with patch("askgem.agent.tools_registry.edit_file", MagicMock(return_value="Success: edited")):
            result = await dispatcher._dispatch(
                "edit_file", {"path": "test.txt", "find_text": "a", "replace_text": "b"}
            )
            assert result == "Success: edited"
            assert dispatcher.modified_files_count == 1

            # Verify console output for auto edit mode
            mock_console.print.assert_called()

    @pytest.mark.asyncio
    async def test_dispatch_async_tool(self, dispatcher):
        """Test dispatching an async tool."""
        result = await dispatcher._dispatch("dummy_async_tool", {"arg1": "async_val"})
        assert result == "Async tool executed with async_val"

    @pytest.mark.asyncio
    async def test_dispatch_sync_tool(self, dispatcher):
        """Test dispatching a standard sync tool."""
        result = await dispatcher._dispatch("dummy_sync_tool", {"arg1": "sync_val"})
        assert result == "Sync tool executed with sync_val"

    @pytest.mark.asyncio
    async def test_dispatch_tool_exception(self, dispatcher):
        """Test that exceptions in tools are caught and returned as string."""

        def failing_tool():
            raise ValueError("Intentional crash")

        dispatcher._tool_map["failing_tool"] = failing_tool

        result = await dispatcher._dispatch("failing_tool", {})
        assert "Error executing failing_tool" in result
        assert "Intentional crash" in result
