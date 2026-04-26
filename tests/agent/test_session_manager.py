"""
Unit tests for the SessionManager module.
Verifies provider initialization, setup_api delegation, and compaction logic.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mentask.agent.core.session import SessionManager
from mentask.agent.schema import AssistantMessage, Message, Role, UsageMetrics


@pytest.fixture
def mock_config():
    config = MagicMock()
    return config


@pytest.mark.asyncio
async def test_session_manager_init(mock_config):
    """Verifies that SessionManager initializes the correct provider."""
    with patch("mentask.agent.core.session.get_provider") as mock_get:
        manager = SessionManager(mock_config, model_name="gemini-2.0-flash")
        mock_get.assert_called_once_with("gemini-2.0-flash", mock_config)
        assert manager.model_name == "gemini-2.0-flash"


@pytest.mark.asyncio
async def test_session_manager_setup_api_delegation(mock_config):
    """Verifies that setup_api calls the provider's setup method."""
    manager = SessionManager(mock_config, model_name="gemini-2.0-flash")
    manager.provider = AsyncMock()
    manager.provider.setup.return_value = True

    success = await manager.setup_api(interactive=False)
    assert success is True
    manager.provider.setup.assert_called_once()


@pytest.mark.asyncio
async def test_session_manager_switch_model(mock_config):
    """Verifies that switch_model re-initializes the provider."""
    manager = SessionManager(mock_config, model_name="gemini-1.5-flash")
    
    with patch("mentask.agent.core.session.get_provider") as mock_get:
        mock_get.return_value = AsyncMock()
        mock_get.return_value.setup.return_value = True
        
        success = await manager.switch_model("gemini-1.5-pro")
        assert success is True
        assert manager.model_name == "gemini-1.5-pro"
        assert mock_get.call_count == 1 # Once in init, but we are inside the patch... wait.
        # Actually init was called before the patch in this test flow? No, manager = ... was before.
        # So mock_get should have been called once inside switch_model.
        mock_get.assert_called_with("gemini-1.5-pro", mock_config)


@pytest.mark.asyncio
async def test_session_manager_compaction_trigger(mock_config):
    """Verifies that compaction is triggered when threshold is approached."""
    manager = SessionManager(mock_config, model_name="gemini-2.0-flash")
    manager.compaction_threshold = 1000
    manager.provider = MagicMock()
    
    # Mock _compact_history
    manager._compact_history = AsyncMock(return_value=[Message(role=Role.USER, content="summary")])
    
    history = [
        AssistantMessage(content="prev", usage=UsageMetrics(input_tokens=900, output_tokens=10))
    ]
    
    # We need to iterate the stream to trigger the check
    async def mock_gen(*args, **kwargs):
        yield {"type": "text", "content": "done"}
        
    manager.provider.generate_stream.side_effect = mock_gen
    
    events = []
    async for event in manager.generate_stream(history, tools_schema=[]):
        events.append(event)
        
    manager._compact_history.assert_called_once()
    assert history[0].content == "summary"
