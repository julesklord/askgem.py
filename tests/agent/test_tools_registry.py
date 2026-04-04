import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from google.genai import types

from askgem.agent.tools_registry import ToolDispatcher

@pytest.fixture
def mock_console():
    with patch("askgem.agent.tools_registry.console") as mock_console:
        yield mock_console

@pytest.fixture
def mock_status():
    with patch("askgem.agent.tools_registry.Status") as mock_status:
        # Status is used as a context manager: with Status(...):
        mock_status.return_value.__enter__.return_value = mock_status.return_value
        yield mock_status

@pytest.fixture
def dispatcher():
    return ToolDispatcher(edit_mode="auto")

class TestToolDispatcher:
    def test_init_creates_tool_map(self, dispatcher):
        assert isinstance(dispatcher._tool_map, dict)
        assert "read_file" in dispatcher._tool_map
        assert "edit_file" in dispatcher._tool_map
        assert "web_search" in dispatcher._tool_map
        assert dispatcher.modified_files_count == 0

    def test_get_tools_list_returns_list_of_callables(self, dispatcher):
        tools = dispatcher.get_tools_list()
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert all(callable(t) for t in tools)

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, dispatcher, mock_console, mock_status):
        func_call = types.FunctionCall(name="unknown_tool", args={})
        result_part = await dispatcher.execute(func_call)

        assert isinstance(result_part, types.Part)
        assert result_part.function_response.name == "unknown_tool"
        assert "not registered" in str(result_part.function_response.response["result"])

        # Verify status usage
        mock_status.assert_called_once()
        assert "unknown_tool" in str(mock_status.call_args)

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.read_file")
    async def test_execute_standard_tool_success(self, mock_read_file, dispatcher, mock_console, mock_status):
        mock_read_file.return_value = "file content"
        dispatcher._tool_map["read_file"] = mock_read_file

        func_call = types.FunctionCall(name="read_file", args={"path": "test.txt"})

        result_part = await dispatcher.execute(func_call)

        # kwargs assertion
        mock_read_file.assert_called_once_with(path="test.txt")
        assert result_part.function_response.response["result"] == "file content"

        # Verify status usage
        mock_status.assert_called_once()
        assert "read_file" in str(mock_status.call_args)

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.read_file")
    async def test_execute_standard_tool_exception(self, mock_read_file, dispatcher, mock_console, mock_status):
        mock_read_file.side_effect = Exception("Test error")
        dispatcher._tool_map["read_file"] = mock_read_file

        func_call = types.FunctionCall(name="read_file", args={"path": "test.txt"})

        result_part = await dispatcher.execute(func_call)

        assert "Error executing read_file" in str(result_part.function_response.response["result"])
        assert "Test error" in str(result_part.function_response.response["result"])
        mock_status.assert_called_once()

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.edit_file")
    async def test_execute_edit_file_auto_mode(self, mock_edit_file, dispatcher, mock_console, mock_status):
        mock_edit_file.return_value = "Success: edited file"
        dispatcher._tool_map["edit_file"] = mock_edit_file

        func_call = types.FunctionCall(
            name="edit_file",
            args={"path": "test.txt", "find_text": "old", "replace_text": "new"}
        )

        result_part = await dispatcher.execute(func_call)

        # For internal interactive tools in ToolsRegistry, they unpack directly via args.get(...) so they are called transitionally.
        # The implementation in askgem/agent/tools_registry.py explicitly calls: edit_file(path, find_text, replace_text)
        mock_edit_file.assert_called_once_with("test.txt", "old", "new")
        assert dispatcher.modified_files_count == 1
        assert result_part.function_response.response["result"] == "Success: edited file"
        mock_status.assert_called_once()

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.edit_file")
    @patch("askgem.agent.tools_registry.Confirm.ask")
    async def test_execute_edit_file_manual_mode_confirmed(self, mock_confirm, mock_edit_file, mock_console, mock_status):
        dispatcher = ToolDispatcher(edit_mode="manual")
        dispatcher._tool_map["edit_file"] = mock_edit_file
        mock_confirm.return_value = True
        mock_edit_file.return_value = "Success: edited file"

        func_call = types.FunctionCall(
            name="edit_file",
            args={"path": "test.txt", "find_text": "old", "replace_text": "new"}
        )

        result_part = await dispatcher.execute(func_call)

        mock_confirm.assert_called_once()
        mock_edit_file.assert_called_once_with("test.txt", "old", "new")
        assert dispatcher.modified_files_count == 1
        assert result_part.function_response.response["result"] == "Success: edited file"

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.edit_file")
    @patch("askgem.agent.tools_registry.Confirm.ask")
    async def test_execute_edit_file_manual_mode_denied(self, mock_confirm, mock_edit_file, mock_console, mock_status):
        dispatcher = ToolDispatcher(edit_mode="manual")
        dispatcher._tool_map["edit_file"] = mock_edit_file
        mock_confirm.return_value = False

        func_call = types.FunctionCall(
            name="edit_file",
            args={"path": "test.txt", "find_text": "old", "replace_text": "new"}
        )

        result_part = await dispatcher.execute(func_call)

        mock_confirm.assert_called_once()
        mock_edit_file.assert_not_called()
        assert dispatcher.modified_files_count == 0
        assert "System Notice" in str(result_part.function_response.response["result"])
        assert "denied permission" in str(result_part.function_response.response["result"])

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.delete_file")
    @patch("askgem.agent.tools_registry.Confirm.ask")
    async def test_execute_delete_file_manual_mode_denied(self, mock_confirm, mock_delete_file, mock_console, mock_status):
        dispatcher = ToolDispatcher(edit_mode="manual")
        dispatcher._tool_map["delete_file"] = mock_delete_file
        mock_confirm.return_value = False

        func_call = types.FunctionCall(
            name="delete_file",
            args={"path": "test.txt"}
        )

        result_part = await dispatcher.execute(func_call)

        mock_confirm.assert_called_once()
        mock_delete_file.assert_not_called()

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.move_file")
    @patch("askgem.agent.tools_registry.Confirm.ask")
    async def test_execute_move_file_manual_mode_denied(self, mock_confirm, mock_move_file, mock_console, mock_status):
        dispatcher = ToolDispatcher(edit_mode="manual")
        dispatcher._tool_map["move_file"] = mock_move_file
        mock_confirm.return_value = False

        func_call = types.FunctionCall(
            name="move_file",
            args={"source": "a.txt", "destination": "b.txt"}
        )

        result_part = await dispatcher.execute(func_call)

        mock_confirm.assert_called_once()
        mock_move_file.assert_not_called()

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.execute_bash", new_callable=AsyncMock)
    @patch("askgem.agent.tools_registry.Confirm.ask")
    async def test_execute_bash_manual_mode_denied(self, mock_confirm, mock_execute_bash, mock_console, mock_status):
        dispatcher = ToolDispatcher(edit_mode="manual")
        dispatcher._tool_map["execute_bash"] = mock_execute_bash
        mock_confirm.return_value = False

        func_call = types.FunctionCall(
            name="execute_bash",
            args={"command": "echo test"}
        )

        result_part = await dispatcher.execute(func_call)

        mock_confirm.assert_called_once()
        mock_execute_bash.assert_not_called()

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.execute_bash", new_callable=AsyncMock)
    @patch("askgem.agent.tools_registry.Confirm.ask")
    async def test_execute_bash_auto_mode(self, mock_confirm, mock_execute_bash, mock_console, mock_status):
        dispatcher = ToolDispatcher(edit_mode="auto")
        dispatcher._tool_map["execute_bash"] = mock_execute_bash
        mock_execute_bash.return_value = "test output"
        mock_confirm.return_value = True

        func_call = types.FunctionCall(
            name="execute_bash",
            args={"command": "echo test"}
        )

        result_part = await dispatcher.execute(func_call)

        # execution in askgem is done via kwargs extraction for command
        mock_execute_bash.assert_called_once_with("echo test")
        assert result_part.function_response.response["result"] == "test output"

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.read_file")
    async def test_truncates_large_results(self, mock_read_file, dispatcher, mock_console, mock_status):
        mock_read_file.return_value = "A" * 15000
        dispatcher._tool_map["read_file"] = mock_read_file

        func_call = types.FunctionCall(name="read_file", args={"path": "large.txt"})

        result_part = await dispatcher.execute(func_call)

        result_str = str(result_part.function_response.response["result"])
        assert len(result_str) < 15000
        assert len(result_str) > 10000
        # The truncation in askgem/agent/tools_registry.py exactly says:
        # [RESULTADO TRUNCADO POR SEGURIDAD]
        assert "TRUNCADO" in result_str

    @pytest.mark.asyncio
    @patch("askgem.agent.tools_registry.read_file")
    async def test_logger_called(self, mock_read_file, mock_console, mock_status):
        mock_logger = MagicMock()
        dispatcher = ToolDispatcher(edit_mode="auto", logger=mock_logger)
        mock_read_file.return_value = "file content"
        dispatcher._tool_map["read_file"] = mock_read_file

        func_call = types.FunctionCall(name="read_file", args={"path": "test.txt"})

        await dispatcher.execute(func_call)

        # Tool Call and Tool Result log calls
        assert mock_logger.call_count == 2

    @pytest.mark.asyncio
    async def test_fallback_type_error(self, dispatcher, mock_console, mock_status):
        # Tools in dispatcher block:
        # try:
        #   return await asyncio.to_thread(tool_func, **args)
        # except TypeError:
        #   return await asyncio.to_thread(tool_func, *args.values())

        # Define a mock tool that simulates needing positional arguments instead of keyword args
        # But we actually want to test the fallback branch properly:
        mock_func = MagicMock()
        mock_func.side_effect = [TypeError("wrong args"), "success"]

        # Wrap it in a normal function so we can pass it as a callable
        def bad_tool(*args, **kwargs):
            return mock_func(*args, **kwargs)

        dispatcher._tool_map["bad_tool"] = bad_tool

        func_call = types.FunctionCall(name="bad_tool", args={"wrong_arg": "val"})
        result_part = await dispatcher.execute(func_call)

        assert result_part.function_response.response["result"] == "success"
        # Check that it was called twice - once with kwargs, once with positional args
        assert mock_func.call_count == 2
