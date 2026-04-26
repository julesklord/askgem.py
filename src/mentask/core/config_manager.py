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
    SERVICE_NAME = "mentask"

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
            "prompt_style": "atomic",  # atomic, simple, minimal, classic
            "nerdfonts_enabled": True,
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

    def load_api_key(self, provider: str = "google") -> str | None:
        """Attempts to load the API_KEY from available sources for a given provider.

        Args:
            provider (str): The provider name (e.g., 'google', 'openai', 'deepseek').

        Priority:
            1. Environment variable ({PROVIDER}_API_KEY)
            2. Local settings.json ({provider}_api_key)
            3. System keyring

        Returns:
            Optional[str]: The API key string if found, otherwise None.
        """
        provider = provider.lower()
        env_var = f"{provider.upper()}_API_KEY"

        # 1. Environment variable
        env_key = os.getenv(env_var)
        if env_key:
            return env_key

        # Fallback for Google specifically
        if provider == "google":
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                return gemini_key

        # 2. Local Settings
        settings_key = self.settings.get(f"{provider}_api_key")
        if settings_key:
            return settings_key

        # 3. System Keyring
        try:
            keyring_key = keyring.get_password(self.SERVICE_NAME, env_var)
            if keyring_key:
                return keyring_key
        except Exception as e:
            self.console.print(f"[error][!] Error accessing keyring for {provider}: {e}[/error]")

        return None

    def save_api_key(self, api_key: str, provider: str = "google") -> bool:
        """Saves the API_KEY to the system keyring.

        Args:
            api_key (str): The raw string of the API Key.
            provider (str): The provider name.

        Returns:
            bool: True if saving was successful, False otherwise.
        """
        provider = provider.lower()
        env_var = f"{provider.upper()}_API_KEY"
        try:
            keyring.set_password(self.SERVICE_NAME, env_var, api_key.strip())
            self.console.print(
                f"[success][OK] {provider.upper()} API Key saved securely in system keyring ({self.SERVICE_NAME})[/success]"
            )
            return True
        except Exception as e:
            self.console.print(f"[error][X] Error saving {provider.upper()} API Key to keyring: {e}[/error]")
            return False
