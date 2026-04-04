import json
import os
from typing import Optional

import keyring

from .paths import get_config_path


class ConfigManager:
    """Manages central configuration for the application.

    Validates, loads, and saves the central API keys and preference settings.
    """

    UNENCRYPTED_API_KEY_FILE = ".gemini_api_key_unencrypted"
    SETTINGS_FILE = "settings.json"
    SERVICE_NAME = "askgem"

    def __init__(self, console):
        """Initializes the ConfigManager and loads default or existing settings.

        Args:
            console: The active rich console instance for logging outputs.
        """
        self.console = console
        self.settings = {
            "model_name": "gemini-2.5-flash",
            "edit_mode": "manual",  # "manual" or "auto"
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

        path = get_config_path(self.SETTINGS_FILE)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(settings_to_save, f, indent=4)
        except Exception as e:
            self.console.print(f"[error][X] Error saving settings: {e}[/error]")

    def load_api_key(self) -> Optional[str]:
        """Attempts to load the API_KEY from available sources.

        1. Environment variable (GOOGLE_API_KEY)
        2. System keyring
        3. Unencrypted local file (legacy fallback)

        Returns:
            Optional[str]: The API key string if found, otherwise None.
        """
        # 1. Environment variable
        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key:
            return env_key

        # 2. System Keyring
        try:
            keyring_key = keyring.get_password(self.SERVICE_NAME, "GOOGLE_API_KEY")
            if keyring_key:
                return keyring_key
        except Exception as e:
            self.console.print(f"[error][!] Error accessing keyring: {e}[/error]")
            self.console.print(
                "[warning][!] Keyring is unavailable. You can set the 'GOOGLE_API_KEY' environment variable as a fallback.[/warning]"
            )

        # 3. Unencrypted local file (v1 base legacy fallback)
        path = get_config_path(self.UNENCRYPTED_API_KEY_FILE)
        if os.path.exists(path):
            try:
                with open(path) as key_file:
                    api_key = key_file.read().strip()
                    if api_key:
                        self.console.print(
                            f"[warning][!] API Key loaded from unencrypted file:[/warning] [google.blue]{path}[/google.blue]"
                        )
                        self.console.print(
                            "[warning][!] Consider running 'askgem auth' to secure it in system keyring.[/warning]"
                        )
                        return api_key
            except OSError as e:
                self.console.print(f"[error][X] Error loading API Key from file:[/error] {e}")

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
                self.console.print(f"[warning][!] Legacy unencrypted file still exists at: {path}[/warning]")
                self.console.print("[warning][!] You may want to delete it manually for better security.[/warning]")

            return True
        except Exception as e:
            self.console.print(f"[error][X] Error saving API Key to keyring: {e}[/error]")
            self.console.print(
                "[warning][!] Keyring storage failed. To bypass this, set the 'GOOGLE_API_KEY' environment variable in your shell.[/warning]"
            )
            return False
