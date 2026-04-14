from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from askgem.agent.tools_registry import ToolDispatcher

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
    def test_init(self, dispatcher):
        assert dispatcher is not None
