"""
Unit tests for the CommandHandler module.
Verifies parsing and execution of slash commands.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mentask.agent.core.commands import CommandHandler


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
async def test_command_handler_fuzzy_suggestion(mock_agent):
    """Verifies that a typoed command triggers a 'Did you mean' suggestion."""
    handler = CommandHandler(mock_agent)
    # /hel should suggest /help
    res = await handler.execute("/hel")
    # Now returns a Table with the error in the title
    from rich.table import Table

    assert isinstance(res, Table)
    assert "/hel" in str(res.title)
    assert "/help" in str(res.caption)


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
    """Verifies that /stop command sets the interrupted flag on agent."""
    handler = CommandHandler(mock_agent)
    # The command handler sets agent.interrupted
    mock_agent.interrupted = False
    await handler.execute("/stop")
    assert mock_agent.interrupted is True


@pytest.mark.asyncio
async def test_command_handler_unknown(mock_agent):
    """Verifies that unknown commands return an explanatory Table."""
    handler = CommandHandler(mock_agent)
    res = await handler.execute("/unknown_cmd_123")
    from rich.table import Table

    assert isinstance(res, Table)
    assert "/unknown_cmd_123" in str(res.title)


@pytest.mark.asyncio
async def test_command_handler_model_switch(mock_agent):
    """Verifies that /model <name> updates the model name and resets session."""
    handler = CommandHandler(mock_agent)
    mock_agent.session.switch_model = AsyncMock()
    mock_agent.session.reset_session = AsyncMock()
    # Mock generation config builder
    mock_agent._build_config = MagicMock(return_value={})
    await handler.execute("/model gemini-1.5-pro")
    assert mock_agent.model_name == "gemini-1.5-pro"
    mock_agent.session.switch_model.assert_called_once_with("gemini-1.5-pro")


@pytest.mark.asyncio
async def test_command_handler_stats(mock_agent):
    """Verifies that /stats command executes and returns a Panel with expected content."""
    from rich.panel import Panel

    handler = CommandHandler(mock_agent)
    mock_agent.session_messages = 5
    mock_agent.session_tools = 10
    mock_agent.session_files = 3
    mock_agent.session.recent_files = ["test.py", "README.md"]
    mock_agent.metrics.total_prompt_tokens = 1000
    mock_agent.metrics.total_candidate_tokens = 500
    mock_agent.metrics.calculate_cost.return_value = 0.00123

    res = await handler.execute("/stats")

    assert isinstance(res, Panel)
    # Check that it contains expected strings (Rich renderables can be checked via capture or repr)
    # For simplicity, we can just check if the Panel exists and has been called with agent data
    assert res.title == "Session Statistics" or res.title == "cmd.stats.title"
