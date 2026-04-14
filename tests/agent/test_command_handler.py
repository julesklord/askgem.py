"""
Unit tests for the CommandHandler module.
Verifies parsing and execution of slash commands.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from askgem.agent.core.commands import CommandHandler


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.model_name = "gemini-1.5-flash"
    agent.edit_mode = "manual"
    agent.metrics.get_summary.return_value = "Stats summary"
    # Important: allow 'interrupted' to be set as a normal attribute
    agent.interrupted = False
    return agent


@pytest.mark.asyncio
async def test_command_handler_help(mock_agent):
    """Verifies that /help command executes without error."""
    handler = CommandHandler(mock_agent)
    res = await handler.execute("/help")
    # /help returns a Rich Table
    from rich.table import Table

    assert isinstance(res, Table)


@pytest.mark.asyncio
async def test_command_handler_stop(mock_agent):
    """Verifies that /stop command sets the interrupted flag on stream processor."""
    handler = CommandHandler(mock_agent)
    # The command handler sets agent.stream_processor.interrupted
    mock_agent.stream_processor = MagicMock()
    mock_agent.stream_processor.interrupted = False
    await handler.execute("/stop")
    assert mock_agent.stream_processor.interrupted is True


@pytest.mark.asyncio
async def test_command_handler_unknown(mock_agent):
    """Verifies that unknown commands return None."""
    handler = CommandHandler(mock_agent)
    res = await handler.execute("/unknown_cmd_123")
    assert res is None


@pytest.mark.asyncio
async def test_command_handler_model_switch(mock_agent):
    """Verifies that /model <name> updates the model name and resets session."""
    handler = CommandHandler(mock_agent)
    mock_agent.session.reset_session = AsyncMock()
    # Mock generation config builder
    mock_agent._build_config = MagicMock(return_value={})
    await handler.execute("/model gemini-1.5-pro")
    assert mock_agent.model_name == "gemini-1.5-pro"
    mock_agent.session.reset_session.assert_called_once()
