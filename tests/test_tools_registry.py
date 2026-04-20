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
def mock_ui():
    ui = MagicMock()
    ui.confirm_action = AsyncMock(return_value=True)
    ui.log_status = MagicMock()
    return ui


@pytest.fixture
def mock_security():
    with patch("askgem.agent.tools_registry.is_command_safe") as mock_safe:
        mock_safe.return_value = False  # Default to unsafe for interactive tests
        yield mock_safe


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.settings = {"google_search_api_key": "test_key", "google_cx_id": "test_cx", "edit_mode": "manual"}
    return config


@pytest.fixture
def dispatcher(mock_config, mock_ui):
    dispatcher = ToolDispatcher(config=mock_config, ui=mock_ui)
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
    def test_init_and_get_tools_list(self, mock_config, mock_ui):
        """Test ToolDispatcher initialization and get_tools_list."""
        dispatcher = ToolDispatcher(config=mock_config, ui=mock_ui)
        tools = dispatcher.get_tools_list()

        # Verify it loaded the default tools
        assert len(tools) > 0
        assert any(t.__name__ == "list_directory" for t in tools if hasattr(t, "__name__"))

        # Verify web_search partial binding works
        assert "web_search" in dispatcher._tool_map
        assert dispatcher._tool_map["web_search"].func.__name__ == "web_search"
        assert dispatcher._tool_map["web_search"].keywords == {"api_key": "test_key", "cx_id": "test_cx"}

    @pytest.mark.asyncio
    async def test_execute_routes_and_returns_part(self, dispatcher):
        """Test the main execute loop routing correctly and formatting the result."""
        fc = types.FunctionCall(name="dummy_sync_tool", args={"arg1": "test_arg"})

        result_part = await dispatcher.execute(fc)

        assert isinstance(result_part, types.Part)
        assert result_part.function_response.name == "dummy_sync_tool"
        assert result_part.function_response.response["result"] == "Sync tool executed with test_arg"

    @pytest.mark.asyncio
    async def test_execute_truncates_large_output(self, dispatcher):
        """Test that outputs larger than 10000 characters are truncated."""
        large_output = "A" * 15000
        dispatcher._tool_map["large_tool"] = MagicMock(return_value=large_output)

        fc = types.FunctionCall(name="large_tool", args={})
        result_part = await dispatcher.execute(fc)

        result_text = result_part.function_response.response["result"]
        assert len(result_text) < 15000
        assert len(result_text) == 10000 + len(
            "\n\n... [!] Result truncated at 10000 characters to avoid context overflow."
        )
        assert result_text.endswith("... [!] Result truncated at 10000 characters to avoid context overflow.")

    @pytest.mark.asyncio
    async def test_execute_with_logger(self, mock_config, mock_ui):
        """Test that execution logs to the provided logger."""
        logger_mock = MagicMock()
        dispatcher = ToolDispatcher(config=mock_config, ui=mock_ui, logger=logger_mock)
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
        assert (
            "no está registrada" in result.lower()
            or "unregistered" in result.lower()
            or "not registered" in result.lower()
        )

    @pytest.mark.asyncio
    async def test_dispatch_interactive_tool_confirm(self, dispatcher):
        """Test interactive tool requiring confirmation and proceeding."""
        dispatcher.ui.confirm_action.return_value = True  # User confirmed

        # Test delete_file
        with patch("askgem.agent.tools_registry.delete_file", MagicMock(return_value="Deleted")):
            result = await dispatcher._dispatch("delete_file", {"path": "test.txt"})
            assert result == "Deleted"
            dispatcher.ui.confirm_action.assert_called_once()

        dispatcher.ui.confirm_action.reset_mock()

        # Test move_file
        with patch("askgem.agent.tools_registry.move_file", MagicMock(return_value="Moved")):
            result = await dispatcher._dispatch("move_file", {"source": "a.txt", "destination": "b.txt"})
            assert result == "Moved"
            dispatcher.ui.confirm_action.assert_called_once()

        dispatcher.ui.confirm_action.reset_mock()

        # Test execute_bash (with security mock)
        with patch("askgem.agent.tools_registry.execute_bash", AsyncMock(return_value="Bash output")):  # noqa: SIM117
            with patch("askgem.agent.tools_registry.analyze_command_safety") as mock_analyze:
                import askgem.core.security

                mock_analyze.return_value.level = askgem.core.security.SafetyLevel.DANGEROUS
                mock_analyze.return_value.category = "mock"
                mock_analyze.return_value.description = "mock"
                result = await dispatcher._dispatch("execute_bash", {"command": "ls"})
                assert result == "Bash output"
                dispatcher.ui.confirm_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_interactive_tool_deny(self, dispatcher):
        """Test interactive tool requiring confirmation but user denies."""
        dispatcher.ui.confirm_action.return_value = False  # User denied

        result = await dispatcher._dispatch("delete_file", {"path": "test.txt"})
        assert "denegó" in result.lower() or "denied" in result.lower()

    @pytest.mark.asyncio
    async def test_dispatch_interactive_tool_auto_mode(self, mock_ui):
        """Test interactive tool when edit_mode is auto (should bypass confirm)."""
        auto_config = MagicMock()
        auto_config.settings = {"google_search_api_key": "test_key", "google_cx_id": "test_cx", "edit_mode": "auto"}
        dispatcher = ToolDispatcher(config=auto_config, ui=mock_ui)
        dispatcher._tool_map = {"edit_file": MagicMock(return_value="Success: edited")}

        with patch("askgem.agent.tools_registry.edit_file", MagicMock(return_value="Success: edited")):
            result = await dispatcher._dispatch(
                "edit_file", {"path": "test.txt", "find_text": "a", "replace_text": "b"}
            )
            assert result == "Success: edited"
            assert dispatcher.modified_files_count == 1

            # Verify UI was notified but not asked for confirmation
            assert mock_ui.confirm_action.call_count == 0
            mock_ui.log_status.assert_called()

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
