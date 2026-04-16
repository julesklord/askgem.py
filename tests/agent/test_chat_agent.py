"""
Legacy test suite for ChatAgent.

Many tests here target the OLD architecture (pre-Orchestrator/CommandHandler refactor).
Tests referencing removed methods are marked as skip pending migration.
"""
from unittest.mock import MagicMock, patch

import pytest

from askgem.agent.chat import ChatAgent


@pytest.fixture
def mock_dependencies():
    with patch("askgem.agent.chat.ConfigManager") as mock_config_manager, \
         patch("askgem.agent.chat.HistoryManager") as mock_history_manager, \
         patch("askgem.agent.chat.ContextManager") as mock_context_manager, \
         patch("askgem.agent.chat.IdentityManager") as mock_identity_manager, \
         patch("askgem.agent.chat.console") as mock_console:

        # Setup ConfigManager mock
        mock_config_instance = MagicMock()
        mock_config_instance.settings = MagicMock()
        mock_config_instance.settings.get.side_effect = lambda key, default=None: {
            "model_name": "test-model",
            "edit_mode": "manual",
            "theme": "indigo",
        }.get(key, default)

        mock_settings_dict = {"model_name": "test-model", "edit_mode": "manual", "theme": "indigo"}
        mock_config_instance.settings.__getitem__.side_effect = mock_settings_dict.__getitem__
        mock_config_instance.settings.__setitem__.side_effect = mock_settings_dict.__setitem__
        mock_config_manager.return_value = mock_config_instance

        # Setup ContextManager mock
        mock_ctx_instance = MagicMock()
        mock_ctx_instance.build_system_instruction.return_value = "Mocked system context"
        mock_context_manager.return_value = mock_ctx_instance

        # Setup IdentityManager mock
        mock_id_instance = MagicMock()
        mock_id_instance.read_identity.return_value = "Mocked identity"
        mock_identity_manager.return_value = mock_id_instance

        yield {
            "config": mock_config_instance,
            "history": mock_history_manager.return_value,
            "context": mock_ctx_instance,
            "identity": mock_id_instance,
            "console": mock_console,
        }


# ──────────────────────────────────────────────
# Tests that still work with the new architecture
# ──────────────────────────────────────────────

def test_agent_initializes_correctly(mock_dependencies):
    """Verifies that ChatAgent initializes without errors."""
    agent = ChatAgent()
    assert agent.model_name == "test-model"
    assert agent.edit_mode == "manual"
    assert len(agent.messages) > 0  # System prompt should be set


@pytest.mark.asyncio
async def test_setup_api(mock_dependencies):
    agent = ChatAgent()

    # Case 1: no API key and non-interactive
    mock_dependencies["config"].load_api_key.return_value = None
    assert await agent.setup_api(interactive=False) is False

    # Case 2: valid API key
    mock_dependencies["config"].load_api_key.return_value = "test_key"
    assert await agent.setup_api(interactive=True) is True
    assert agent.client is not None


# ──────────────────────────────────────────────
# SKIPPED: Tests targeting OLD architecture
# These tested methods that were refactored into
# AgentOrchestrator and CommandHandler.
# ──────────────────────────────────────────────

@pytest.mark.skip(reason="Refactored: _extract_function_calls moved to AgentOrchestrator")
def test_extract_function_calls(mock_dependencies):
    pass


@pytest.mark.skip(reason="Refactored: _stream_response replaced by AgentOrchestrator.run_query")
@pytest.mark.asyncio
async def test_stream_response_text_only(mock_dependencies):
    pass


@pytest.mark.skip(reason="Refactored: _stream_response replaced by AgentOrchestrator.run_query")
@pytest.mark.asyncio
async def test_stream_response_with_tool_call(mock_dependencies):
    pass


@pytest.mark.skip(reason="Refactored: _cmd_model moved to CommandHandler")
@pytest.mark.asyncio
async def test_cmd_model(mock_dependencies):
    pass


@pytest.mark.skip(reason="Refactored: _summarize_context moved to SessionManager")
@pytest.mark.asyncio
async def test_summarize_context(mock_dependencies):
    pass


@pytest.mark.skip(reason="Refactored: _process_slash_command moved to CommandHandler")
@pytest.mark.asyncio
async def test_process_slash_command(mock_dependencies):
    pass


@pytest.mark.skip(reason="Refactored: _cmd_mode moved to CommandHandler")
def test_cmd_mode(mock_dependencies):
    pass


@pytest.mark.skip(reason="Refactored: _cmd_clear moved to CommandHandler")
@pytest.mark.asyncio
async def test_cmd_clear(mock_dependencies):
    pass


@pytest.mark.skip(reason="Refactored: dispatcher replaced by AgentOrchestrator")
@pytest.mark.asyncio
async def test_integration_agent_with_tools(mock_dependencies):
    pass

