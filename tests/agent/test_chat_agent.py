from unittest.mock import MagicMock, patch
import pytest
from askgem.agent.chat import ChatAgent

@pytest.fixture
def mock_dependencies():
    with patch("askgem.agent.chat.ConfigManager") as mock_config_manager, patch(
        "askgem.agent.chat.HistoryManager"
    ) as mock_history_manager, patch("askgem.cli.console.console") as mock_console:
        mock_config_instance = MagicMock()
        mock_config_instance.settings = MagicMock()
        mock_config_instance.settings.get.side_effect = lambda key, default=None: {
            "model_name": "test-model",
            "edit_mode": "manual",
        }.get(key, default)
        mock_config_manager.return_value = mock_config_instance
        yield {
            "config": mock_config_instance,
            "history": mock_history_manager.return_value,
            "console": mock_console,
        }

def test_init_chat_agent(mock_dependencies):
    agent = ChatAgent()
    assert agent.model_name == "test-model"
    assert agent.edit_mode == "manual"
