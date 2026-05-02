import json
from unittest.mock import MagicMock, patch

from mentask.core.config_manager import ConfigManager


def test_save_settings_does_not_leak_key_on_keyring_failure(tmp_path):
    """
    Verifies that the plaintext search key is NOT written to the config file
    if keyring.set_password fails.
    """
    mock_console = MagicMock()
    # We must ensure get_config_dir returns tmp_path so ConfigManager can write there.
    with patch("mentask.core.config_manager.get_config_path") as mock_get_path:
        settings_file = tmp_path / "settings.json"
        mock_get_path.return_value = str(settings_file)

        cm = ConfigManager(mock_console)
        # Set a search key that needs to be moved to keyring
        plaintext_key = "SUPER_SECRET_PLAINTEXT_KEY"
        cm.settings["google_search_api_key"] = plaintext_key

        # Mock keyring to fail
        with patch("keyring.set_password", side_effect=Exception("Keyring failure")):
            cm.save_settings()

        # Read the saved settings file
        with open(settings_file) as f:
            saved_settings = json.load(f)

        # AFTER FIX: This should pass (it should not be equal to plaintext)
        assert saved_settings["google_search_api_key"] != plaintext_key
        assert saved_settings["google_search_api_key"] == ""


def test_save_settings_strips_all_provider_keys(tmp_path):
    """
    Verifies that various provider API keys are stripped from settings.json.
    """
    mock_console = MagicMock()
    with patch("mentask.core.config_manager.get_config_path") as mock_get_path:
        settings_file = tmp_path / "settings.json"
        mock_get_path.return_value = str(settings_file)

        cm = ConfigManager(mock_console)
        cm.settings["google_api_key"] = "sk-google-123"
        cm.settings["openai_api_key"] = "sk-openai-456"
        cm.settings["deepseek_api_key"] = "sk-deepseek-789"

        cm.save_settings()

        with open(settings_file) as f:
            saved_settings = json.load(f)

        assert saved_settings.get("google_api_key") in ["", "STORED_IN_KEYRING", None]
        assert saved_settings.get("openai_api_key") in ["", "STORED_IN_KEYRING", None]
        assert saved_settings.get("deepseek_api_key") in ["", "STORED_IN_KEYRING", None]


def test_load_settings_warns_on_local_secrets(tmp_path):
    """
    Verifies that ConfigManager prints a warning if a local .mentask/settings.json contains secrets.
    """
    mock_console = MagicMock()
    # Mock os.getcwd to return tmp_path
    with patch("os.getcwd", return_value=str(tmp_path)):
        local_dir = tmp_path / ".mentask"
        local_dir.mkdir()
        local_settings = local_dir / "settings.json"

        # Create a local settings file with a secret
        with open(local_settings, "w") as f:
            json.dump({"google_api_key": "sk-local-secret"}, f)

        with patch("mentask.core.config_manager.get_config_path", return_value=str(tmp_path / "global_settings.json")):
            ConfigManager(mock_console)

        # Check if console.print was called with a warning
        # Based on implementation: self.console.print(f"[warning][!] Security Warning: ...")
        warning_calls = [call for call in mock_console.print.call_args_list if "Security Warning" in str(call)]
        assert len(warning_calls) > 0
        assert "google_api_key" in str(warning_calls[0])
