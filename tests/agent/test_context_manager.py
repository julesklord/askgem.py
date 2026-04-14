"""
Unit tests for the ContextManager module.
Verifies system instruction building and context summarization logic.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from askgem.agent.core.context import ContextManager


def test_context_manager_build_system_instruction():
    """Verifies that the system instruction contains expected core directives."""
    manager = ContextManager()
    instruction = manager.build_system_instruction()

    assert "AskGem" in instruction
    # Check for English keywords in the instruction (after translation)
    assert "autonomous" in instruction.lower() or "agent" in instruction.lower()
    assert "memory" in instruction.lower()


@pytest.mark.asyncio
async def test_context_manager_summarization_threshold():
    """Verifies that summarization is only triggered after the threshold."""
    manager = ContextManager()
    mock_session = MagicMock()
    mock_chat = MagicMock()
    mock_session.chat_session = mock_chat

    # 1. Below threshold (default is 100 turns)
    mock_chat.get_history.return_value = [MagicMock()] * 10
    await manager.summarize_if_needed(mock_session, "model", lambda: None)
    # GenAI generate_content should NOT be called for summarization
    mock_session.client.models.generate_content.assert_not_called()


@pytest.mark.asyncio
async def test_context_manager_summarization_trigger():
    """Verifies that summarization logic is executed when history is long."""
    manager = ContextManager()
    mock_session = MagicMock()
    mock_chat = MagicMock()
    mock_session.chat_session = mock_chat

    # Mock client and generate_content
    mock_session.client = MagicMock()
    mock_session.client.models.generate_content = AsyncMock()
    mock_session.client.aio.chats.create = MagicMock()

    # Create a long history (e.g. 110 messages)
    # GenAI items are usually dict-like or objects with role/parts
    mock_msg = MagicMock()
    mock_msg.role = "user"
    mock_msg.parts = [MagicMock()]
    mock_chat.get_history.return_value = [mock_msg] * 110

    # Mock response from summary model
    mock_summary_res = MagicMock()
    mock_summary_res.text = "This is a summary."
    mock_session.client.models.generate_content.return_value = mock_summary_res

    # Mock builder function
    mock_builder = MagicMock(return_value={})

    await manager.summarize_if_needed(mock_session, "model-pro", mock_builder)

    # Verify summarization was attempted
    mock_session.client.models.generate_content.assert_called_once()
    # Verify session was recreated with new history
    mock_session.client.aio.chats.create.assert_called_once()


