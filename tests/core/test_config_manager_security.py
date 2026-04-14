import json
import os
from unittest.mock import MagicMock, patch
import pytest
from askgem.core.config_manager import ConfigManager

def test_save_settings_does_not_leak_key_on_keyring_failure(tmp_path):
    """
    Verifies that the plaintext search key is NOT written to the config file
    if keyring.set_password fails.
    """
    mock_console = MagicMock()
    # We must ensure get_config_dir returns tmp_path so ConfigManager can write there.
    with patch("askgem.core.config_manager.get_config_path") as mock_get_path:
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
        with open(settings_file, "r") as f:
            saved_settings = json.load(f)

        # AFTER FIX: This should pass (it should not be equal to plaintext)
        assert saved_settings["google_search_api_key"] != plaintext_key
        assert saved_settings["google_search_api_key"] == ""
