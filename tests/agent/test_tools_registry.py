from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types

from askgem.agent.tools_registry import ToolDispatcher


@pytest.fixture
def mock_console():
    with patch("askgem.cli.console.console") as mock_console:
        yield mock_console

@pytest.fixture
def mock_status():
    with patch("askgem.agent.tools_registry.Status") as mock_status:
        # Status is used as a context manager: with Status(...):
        mock_status.return_value.__enter__.return_value = mock_status.return_value
        yield mock_status

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.settings = {
        "google_search_api_key": "test_key",
        "google_cx_id": "test_cx",
        "edit_mode": "manual"
    }
    return config

@pytest.fixture
def dispatcher(mock_config):
    mock_ui = MagicMock()
    return ToolDispatcher(config=mock_config, ui=mock_ui)

class TestToolDispatcher:
    def test_init_creates_tool_map(self, dispatcher):
        assert dispatcher._tool_map is not None
