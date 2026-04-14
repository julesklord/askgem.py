"""
Unit tests for the SessionManager module.
Verifies API setup, session creation, and retry logic.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from askgem.agent.core.session import SessionManager
from askgem.agent.core.simulation import SimulationManager


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.load_api_key.return_value = "fake-key"
    return config


@pytest.mark.asyncio
async def test_session_manager_setup_api_success(mock_config):
    """Verifies that setup_api works with a valid key."""
    manager = SessionManager(mock_config, model_name="gemini-1.5-flash")
    with patch("google.genai.Client") as mock_client:
        success = await manager.setup_api(interactive=False)
        assert success is True
        mock_client.assert_called_once()


@pytest.mark.asyncio
async def test_session_manager_setup_api_missing_key(mock_config):
    """Verifies that setup_api fails when no key is found in non-interactive mode."""
    mock_config.load_api_key.return_value = None
    manager = SessionManager(mock_config, model_name="gemini-1.5-flash")
    with patch.dict("os.environ", {}, clear=True):
        success = await manager.setup_api(interactive=False)
        assert success is False


@pytest.mark.asyncio
async def test_session_manager_ensure_session_real(mock_config):
    """Verifies that ensure_session creates a real chat session."""
    manager = SessionManager(mock_config, model_name="gemini-1.5-flash")
    manager.client = MagicMock()
    # Mock aio client path
    manager.client.aio.chats.create = MagicMock()

    await manager.ensure_session(model_config={})
    manager.client.aio.chats.create.assert_called_once()


@pytest.mark.asyncio
async def test_session_manager_simulation_playback_mode(mock_config):
    """Verifies that playback mode skips real API calls."""
    sim = SimulationManager(transcript_path="fake.json", mode="playback")
    manager = SessionManager(mock_config, model_name="gemini-1.5-flash", simulation=sim)

    with patch("google.genai.Client") as mock_client:
        success = await manager.setup_api(interactive=False)
        assert success is True
        mock_client.assert_not_called()

        await manager.ensure_session(model_config={})
        # Should create a SimulationSession, not call real GenAI client
        from askgem.agent.core.simulation import SimulationSession
        assert isinstance(manager.chat_session, SimulationSession)


@pytest.mark.asyncio
async def test_session_manager_retry_logic(mock_config):
    """Verifies that retry logic triggers for specific keywords."""
    manager = SessionManager(mock_config, model_name="gemini-1.5-flash")

    # Error 429 should be retryable
    exc = Exception("429 Resource Exhausted")
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        can_retry = await manager.handle_retryable_error(exc, attempt=1, max_retries=3, base_delay=1.0)
        assert can_retry is True
        mock_sleep.assert_called_once()

    # Max retries reached
    can_retry = await manager.handle_retryable_error(exc, attempt=3, max_retries=3, base_delay=1.0)
    assert can_retry is False


@pytest.mark.asyncio
async def test_session_manager_non_retryable_error(mock_config):
    """Verifies that fatal errors (e.g., Auth) are not retried."""
    manager = SessionManager(mock_config, model_name="gemini-1.5-flash")
    exc = Exception("403 Invalid API Key")
    can_retry = await manager.handle_retryable_error(exc, attempt=1, max_retries=3, base_delay=1.0)
    assert can_retry is False


