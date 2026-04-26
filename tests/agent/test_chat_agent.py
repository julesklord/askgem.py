from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mentask.agent.chat import ChatAgent, ChatAgentDependencies


@pytest.fixture
def mock_dependencies():
    with (
        patch("src.mentask.agent.chat.ConfigManager") as mock_config_manager,
        patch("src.mentask.agent.chat.HistoryManager") as mock_history_manager,
        patch("src.mentask.agent.chat.ContextManager") as mock_context_manager,
        patch("src.mentask.agent.chat.KnowledgeManager") as mock_knowledge_manager,
        patch("src.mentask.agent.chat.console") as mock_console,
    ):
        # Setup ConfigManager mock
        mock_config_instance = MagicMock()
        mock_config_instance.settings = MagicMock()
        mock_config_instance.settings.get.side_effect = lambda key, default=None: {
            "model_name": "test-model",
            "edit_mode": "manual",
            "theme": "indigo",
        }.get(key, default)

        mock_config_manager.return_value = mock_config_instance

        # Setup ContextManager mock
        mock_ctx_instance = MagicMock()
        mock_ctx_instance.build_system_instruction.return_value = "Mocked system context"
        mock_context_manager.return_value = mock_ctx_instance

        # Setup KnowledgeManager mock
        mock_id_instance = MagicMock()
        mock_id_instance.read_identity.return_value = "Mocked identity"
        mock_knowledge_manager.return_value = mock_id_instance

        yield {
            "config": mock_config_instance,
            "history": mock_history_manager.return_value,
            "context": mock_ctx_instance,
            "knowledge": mock_id_instance,
            "console": mock_console,
        }


@pytest.mark.asyncio
async def test_agent_initializes_correctly(mock_dependencies):
    """Verifies that ChatAgent initializes without errors."""
    agent = ChatAgent()
    assert agent.model_name == "test-model"
    assert agent.edit_mode == "manual"
    assert len(agent.messages) == 0


@pytest.mark.asyncio
async def test_setup_api(mock_dependencies):
    agent = ChatAgent()

    # Case 1: no API key and non-interactive
    mock_dependencies["config"].load_api_key.return_value = None
    assert await agent.setup_api(interactive=False) is False

    # Case 2: valid API key
    mock_dependencies["config"].load_api_key.return_value = "test_key"
    # SUCCESS: session.setup_api must be an AsyncMock
    agent.session.setup_api = AsyncMock(return_value=True)
    assert await agent.setup_api(interactive=True) is True


@pytest.mark.asyncio
async def test_agent_accepts_injected_dependencies(mock_dependencies):
    injected_session = MagicMock()
    injected_session.metrics = MagicMock()
    injected_tools = MagicMock()

    deps = ChatAgentDependencies(
        config=mock_dependencies["config"],
        history=mock_dependencies["history"],
        identity=mock_dependencies["knowledge"],
        context=mock_dependencies["context"],
        session=injected_session,
        tools=injected_tools,
    )

    agent = ChatAgent(dependencies=deps)

    assert agent.config is mock_dependencies["config"]
    assert agent.history is mock_dependencies["history"]
    assert agent.identity is mock_dependencies["knowledge"]
    assert agent.context is mock_dependencies["context"]
    assert agent.session is injected_session
    assert agent.tools is injected_tools
