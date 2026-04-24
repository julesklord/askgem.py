import json
import os

import keyring

from .paths import get_config_path


class ConfigManager:
    """Manages central configuration for the application.

    Validates, loads, and saves the central API keys and preference settings.
    """

    UNENCRYPTED_API_KEY_FILE = ".gem_api_key_unencrypted"
    SETTINGS_FILE = "settings.json"
    SERVICE_NAME = "askgem"

    def __init__(self, console):
        """Initializes the ConfigManager and loads default or existing settings.

        Args:
            console: The active rich console instance for logging outputs.
        """
        self.console = console
        self.settings = {
            "model_name": "gemini-2.0-flash",
            "edit_mode": "manual",  # "manual" or "auto"
            "theme": "indigo",  # indigo, emerald, crimson, amber, cyberpunk
            "stream_delay": 0.015,  # 15ms default delay for professional feel
            "temperature": 0.7,
            "max_file_read_size": 30000,
            "bash_timeout": 60,
            "web_search_enabled": True,
            "google_api_key": "",
            "google_search_api_key": "",
            "google_cx_id": "",
        }
        self.load_settings()

    def load_settings(self) -> None:
        """Loads user settings from the JSON file if available.

        Modifies the settings dict in place.
        """
        path = get_config_path(self.SETTINGS_FILE)
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                self.console.print(f"[error][X] Error loading settings.json: {e}[/error]")

        # Load sensitive keys from keyring
        try:
            search_key = keyring.get_password(self.SERVICE_NAME, "GOOGLE_SEARCH_API_KEY")
            if search_key:
                self.settings["google_search_api_key"] = search_key
        except Exception as e:
            self.console.print(f"[error][!] Error accessing keyring for search key: {e}[/error]")
            # Fallback to env var if keyring fails
            env_search_key = os.getenv("GOOGLE_SEARCH_API_KEY")
            if env_search_key:
                self.settings["google_search_api_key"] = env_search_key

    def save_settings(self) -> None:
        """Saves current memory settings into the JSON config file.
        Sensitive keys are stored in the system keyring.
        """
        settings_to_save = self.settings.copy()

        # Handle sensitive keys
        search_key = self.settings.get("google_search_api_key", "")
        if search_key and search_key != "STORED_IN_KEYRING":
            try:
                keyring.set_password(self.SERVICE_NAME, "GOOGLE_SEARCH_API_KEY", search_key)
                settings_to_save["google_search_api_key"] = "STORED_IN_KEYRING"
            except Exception as e:
                self.console.print(f"[error][X] Error saving search key to keyring: {e}[/error]")
                # Ensure the plaintext key is NOT saved to the JSON file on failure
                settings_to_save["google_search_api_key"] = ""

        path = get_config_path(self.SETTINGS_FILE)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(settings_to_save, f, indent=4)
        except Exception as e:
            self.console.print(f"[error][X] Error saving settings: {e}[/error]")

    def load_api_key(self) -> str | None:
        """Attempts to load the API_KEY from available sources.

        Priority:
        1. Environment variable (GOOGLE_API_KEY)
        2. Local settings.json (google_api_key)
        3. System keyring

        Returns:
            Optional[str]: The API key string if found, otherwise None.
        """
        # 1. Environment variable
        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key:
            return env_key

        # 2. Local Settings
        settings_key = self.settings.get("google_api_key")
        if settings_key:
            return settings_key

        # 3. System Keyring
        try:
            keyring_key = keyring.get_password(self.SERVICE_NAME, "GOOGLE_API_KEY")
            if keyring_key:
                return keyring_key
        except Exception as e:
            self.console.print(f"[error][!] Error accessing keyring: {e}[/error]")
            self.console.print(
                "[warning][!] Keyring is unavailable. You can set the 'GOOGLE_API_KEY' environment variable as a fallback.[/warning]"
            )

        # 3. Unencrypted local file (v1 base legacy fallback) - Removed for security
        path = get_config_path(self.UNENCRYPTED_API_KEY_FILE)
        if os.path.exists(path):
            self.console.print(
                f"[error][!] SECURITY WARNING: Legacy unencrypted API key file detected at {path}[/error]"
            )
            self.console.print(
                "[error][!] This file is no longer used. Please delete it immediately and run 'askgem auth' to secure your key in the system keyring.[/error]"
            )

        return None

    def save_api_key(self, api_key: str) -> bool:
        """Saves the API_KEY to the system keyring.

        Args:
            api_key (str): The raw string of the Google API Key.

        Returns:
            bool: True if saving was successful, False otherwise.
        """
        try:
            keyring.set_password(self.SERVICE_NAME, "GOOGLE_API_KEY", api_key.strip())
            self.console.print(
                f"[success][OK] API Key saved securely in system keyring ({self.SERVICE_NAME})[/success]"
            )

            # If legacy file exists, warn the user
            path = get_config_path(self.UNENCRYPTED_API_KEY_FILE)
            if os.path.exists(path):
                self.console.print(
                    f"[error][!] SECURITY WARNING: Legacy unencrypted file still exists at: {path}[/error]"
                )
                self.console.print("[error][!] You MUST delete it manually for better security.[/error]")

            return True
        except Exception as e:
            self.console.print(f"[error][X] Error saving API Key to keyring: {e}[/error]")
            self.console.print(
                "[warning][!] Keyring storage failed. To bypass this, set the 'GOOGLE_API_KEY' environment variable in your shell.[/warning]"
            )
            return False
