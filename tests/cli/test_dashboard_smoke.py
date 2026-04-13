"""
Smoke tests for the AskGem TUI Dashboard.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.askgem.cli.dashboard import AskGemDashboard, MascotWidget


@pytest.fixture
def mock_agent():
    """Mock agent with required attributes."""
    agent = MagicMock()
    agent.model_name = "gemini-1.5-flash"
    agent.edit_mode = "manual"
    agent.metrics.get_summary.return_value = "Tokens: 1,500\nCost: $0.05"
    return agent


def test_mascot_widget_states():
    """Verifies that the mascot widget can change states."""
    widget = MascotWidget()
    # Mock the update method (part of Textual Static)
    widget.update = MagicMock()

    widget.set_state("thinking")
    assert widget.state == "thinking"

    widget.set_state("working")
    assert widget.state == "working"

    widget.set_state("error")
    assert widget.state == "error"

    # Invalid state should be ignored
    widget.set_state("invalid_state_123")
    assert widget.state == "error"


def test_dashboard_initialization(mock_agent):
    """Verifies that the dashboard app can be instantiated."""
    app = AskGemDashboard(agent=mock_agent)
    assert app.agent == mock_agent

    # Mock internal components expected by on_mount
    app.sidebar = MagicMock()
    app.chat_log = MagicMock()
    app._update_metrics = MagicMock()

    # Mock set_interval and init_api to avoid event loop issues
    with patch.object(app, 'set_interval'), patch.object(app, 'init_api'):
        # Trigger the real on_mount logic manually since we're not running the full app
        app.on_mount()
    assert mock_agent.set_status_logger.called
    assert app.title == "AskGem v2.3.1"
