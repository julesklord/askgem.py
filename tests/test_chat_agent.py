from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from askgem.agent.chat import ChatAgent


@pytest.fixture
def mock_dependencies():
    with patch("askgem.agent.chat.ConfigManager") as mock_config_manager, patch(
        "askgem.agent.chat.HistoryManager"
    ) as mock_history_manager, patch("askgem.agent.chat.MemoryManager") as mock_memory_manager, patch(
        "askgem.agent.chat.MissionManager"
    ) as mock_mission_manager, patch("askgem.agent.chat.console") as mock_console:
        # Setup ConfigManager mock
        mock_config_instance = MagicMock()
        mock_config_instance.settings = MagicMock()
        mock_config_instance.settings.get.side_effect = lambda key, default=None: {
            "model_name": "test-model",
            "edit_mode": "manual",
        }.get(key, default)

        mock_settings_dict = {"model_name": "test-model", "edit_mode": "manual"}
        mock_config_instance.settings.__getitem__.side_effect = mock_settings_dict.__getitem__
        mock_config_instance.settings.__setitem__.side_effect = mock_settings_dict.__setitem__

        mock_config_manager.return_value = mock_config_instance

        yield {
            "config": mock_config_instance,
            "history": mock_history_manager.return_value,
            "memory": mock_memory_manager.return_value,
            "mission": mock_mission_manager.return_value,
            "console": mock_console,
        }


def test_extract_function_calls(mock_dependencies):
    agent = ChatAgent()
    seen_calls = set()

    # Mock chunk with function calls using the SDK's standard properties
    fc1 = MagicMock()
    fc1.name = "my_tool"
    fc1.args = {"arg1": "value"}

    chunk = MagicMock()
    chunk.function_calls = [fc1]

    calls = agent._extract_function_calls(chunk, seen_calls)

    assert len(calls) == 1
    assert calls[0].name == "my_tool"
    assert ("my_tool", str([("arg1", "value")])) in seen_calls

    # Test deduplication
    calls2 = agent._extract_function_calls(chunk, seen_calls)
    assert len(calls2) == 0


@pytest.mark.asyncio
async def test_stream_response_text_only(mock_dependencies):
    agent = ChatAgent()
    agent.client = MagicMock()
    agent.metrics = MagicMock()
    mock_chat_session = MagicMock()

    # Create an async generator for the stream mock
    async def mock_stream():
        chunk = MagicMock()
        chunk.text = "Hello world!"
        chunk.function_calls = []
        chunk.candidates = []
        chunk.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)
        yield chunk

    mock_chat_session.send_message_stream = AsyncMock(return_value=mock_stream())

    # Return fake raw history
    mock_chat_session.get_history = AsyncMock(return_value=["test history"])
    agent.chat_session = mock_chat_session

    agent._ensure_session = AsyncMock()
    agent._summarize_context = AsyncMock()

    # Mock the ToolDispatcher so we can intercept calls
    agent.dispatcher = AsyncMock()

    callback = MagicMock()

    with patch("askgem.agent.chat._logger.warning"):
        await agent._stream_response("test input", callback=callback)

    callback.assert_called_once_with("Hello world!")
    agent.metrics.add_usage.assert_called_once_with(10, 5)
    mock_dependencies["history"].save_session.assert_called_once_with(["test history"])


@pytest.mark.asyncio
async def test_stream_response_with_tool_call(mock_dependencies):
    agent = ChatAgent()
    agent.client = MagicMock()
    agent.metrics = MagicMock()
    mock_chat_session = MagicMock()

    fc1 = MagicMock()
    fc1.name = "test_tool"
    fc1.args = {}

    # First stream yields a function call
    async def mock_stream_1():
        chunk = MagicMock()
        chunk.text = ""
        chunk.function_calls = [fc1]
        chunk.candidates = []
        chunk.usage_metadata = None
        yield chunk

    # Second stream yields text (after tool executes)
    async def mock_stream_2():
        chunk = MagicMock()
        chunk.text = "Tool result processed"
        chunk.function_calls = []
        chunk.candidates = []
        chunk.usage_metadata = None
        yield chunk

    # the recursion will call send_message_stream twice
    mock_chat_session.send_message_stream = AsyncMock(side_effect=[mock_stream_1(), mock_stream_2()])
    mock_chat_session.get_history = AsyncMock(return_value=[])
    agent.chat_session = mock_chat_session

    agent._ensure_session = AsyncMock()
    agent._summarize_context = AsyncMock()

    agent.dispatcher = AsyncMock()
    agent.dispatcher.execute.return_value = "fake result"

    callback = MagicMock()

    with patch("askgem.agent.chat._logger.warning"):
        await agent._stream_response("initial input", callback=callback)

    agent.dispatcher.execute.assert_called_once_with(fc1)
    callback.assert_called_once_with("Tool result processed")
    assert agent.session_tools == 1


@pytest.mark.asyncio
async def test_cmd_model(mock_dependencies):
    agent = ChatAgent()
    agent.client = MagicMock()

    # Mocking model list
    mock_model1 = MagicMock()
    mock_model1.supported_actions = ["generateContent"]
    mock_model1.name = "models/gemini-pro"

    async def mock_models_stream():
        yield mock_model1

    agent.client.aio.models.list = AsyncMock(return_value=mock_models_stream())

    # No args -> lists models
    await agent._cmd_model([])
    mock_dependencies["console"].print.assert_called()

    # Arg -> switches model
    agent.chat_session = MagicMock()
    agent.chat_session.get_history = AsyncMock(return_value=["hist"])
    agent.client.aio.chats.create = AsyncMock()
    agent._build_config = MagicMock(return_value="config")

    await agent._cmd_model(["new-gemini"])
    assert agent.model_name == "new-gemini"
    agent.config.save_settings.assert_called_once()
    agent.client.aio.chats.create.assert_called_once_with(model="new-gemini", config="config", history=["hist"])


@pytest.mark.asyncio
async def test_setup_api(mock_dependencies):
    agent = ChatAgent()

    # Case 1: no API key and non-interactive
    mock_dependencies["config"].load_api_key.return_value = None
    assert await agent.setup_api(interactive=False) is False

    # Case 2: no API key, interactive but empty input
    with patch("askgem.agent.chat.Prompt.ask", return_value=""):
        assert await agent.setup_api(interactive=True) is False

    # Case 3: valid API key
    mock_dependencies["config"].load_api_key.return_value = "test_key"
    assert await agent.setup_api(interactive=True) is True
    assert agent.client is not None


@pytest.mark.asyncio
async def test_summarize_context(mock_dependencies):
    agent = ChatAgent()
    agent.client = MagicMock()

    # Case 1: Early return if no chat session
    agent.chat_session = None
    await agent._summarize_context()  # Should not raise

    # Case 2: Early return if history < 100
    mock_chat_session = MagicMock()
    mock_chat_session.get_history = AsyncMock(return_value=[1, 2, 3])
    agent.chat_session = mock_chat_session
    await agent._summarize_context()
    agent.client.models.generate_content.assert_not_called()

    # Case 3: Triggers summarization
    mock_chat_session.get_history = AsyncMock(return_value=list(range(105)))
    agent.chat_session = mock_chat_session

    mock_response = MagicMock()
    mock_response.text = "Mocked Summary"
    agent.client.models.generate_content = AsyncMock(return_value=mock_response)

    agent.client.chats.create = MagicMock(return_value="new_session")

    await agent._summarize_context()
    agent.client.models.generate_content.assert_called_once()
    agent.client.chats.create.assert_called_once()
    assert agent.chat_session == "new_session"


@pytest.mark.asyncio
async def test_process_slash_command(mock_dependencies):
    agent = ChatAgent()

    with patch.object(agent, "_cmd_help") as mock_help, patch.object(
        agent, "_cmd_model", new_callable=AsyncMock
    ), patch.object(agent, "_cmd_mode"), patch.object(agent, "_cmd_clear", new_callable=AsyncMock), patch.object(
        agent, "_cmd_history", new_callable=AsyncMock
    ), patch.object(agent, "_cmd_stats"), patch.object(agent, "_cmd_reset", new_callable=AsyncMock):
        await agent._process_slash_command("/help")
        mock_help.assert_called_once()

        await agent._process_slash_command("/stop")
        assert agent.interrupted is True
        agent.interrupted = False

        await agent._process_slash_command("/abort")
        assert agent.interrupted is True


def test_cmd_mode(mock_dependencies):
    agent = ChatAgent()

    # Valid arg
    agent._cmd_mode(["auto"])
    assert agent.edit_mode == "auto"
    mock_dependencies["config"].save_settings.assert_called_once()

    # Invalid arg
    agent.edit_mode = "manual"
    agent._cmd_mode(["invalid"])
    assert agent.edit_mode == "manual"


@pytest.mark.asyncio
async def test_cmd_clear(mock_dependencies):
    agent = ChatAgent()
    agent.client = MagicMock()

    # Mocking client.aio.chats.create
    agent.client.aio.chats.create = MagicMock(return_value="new_cleared_session")

    await agent._cmd_clear()

    agent.client.aio.chats.create.assert_called_once()
    assert agent.chat_session == "new_cleared_session"


@pytest.mark.asyncio
async def test_integration_agent_with_tools(mock_dependencies):
    """Integration test: Agent processes a query that requires tool usage."""
    agent = ChatAgent()
    agent.client = MagicMock()

    # Mock the chat session stream
    async def mock_stream():
        # First chunk: tool call
        chunk1 = MagicMock()
        chunk1.text = ""
        fc = MagicMock()
        fc.name = "read_file"
        fc.args = {"file_path": "test.txt"}
        chunk1.function_calls = [fc]
        chunk1.candidates = []
        chunk1.usage_metadata = None
        yield chunk1

        # Second chunk: response after tool
        chunk2 = MagicMock()
        chunk2.text = "File content processed"
        chunk2.function_calls = []
        chunk2.candidates = []
        chunk2.usage_metadata = None
        yield chunk2

    mock_chat_session = MagicMock()
    mock_chat_session.send_message_stream = AsyncMock(side_effect=[mock_stream()])
    mock_chat_session.get_history = AsyncMock(return_value=[])
    agent.chat_session = mock_chat_session

    agent._ensure_session = AsyncMock()
    agent._summarize_context = AsyncMock()

    # Mock dispatcher to return a result
    agent.dispatcher = AsyncMock()
    agent.dispatcher.execute.return_value = "File content: Hello World"

    callback = MagicMock()

    await agent._stream_response("Read the file test.txt", callback=callback)

    # Verify tool was executed
    agent.dispatcher.execute.assert_called_once()
    call_args = agent.dispatcher.execute.call_args[0][0]
    assert call_args.name == "read_file"
    assert call_args.args["file_path"] == "test.txt"

    # Verify callback was called with final response
    callback.assert_called_with("File content processed")
