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

    # List of keys that should never be stored in plaintext in settings.json
    SENSITIVE_KEYS = [
        "google_api_key",
        "openai_api_key",
        "deepseek_api_key",
        "anthropic_api_key",
        "google_search_api_key",
    ]

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
        Supports hierarchical loading: Global -> Local (.mentask/settings.json).
        """
        # 1. Global settings
        path = get_config_path(self.SETTINGS_FILE)
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                self.console.print(f"[error][X] Error loading global settings.json: {e}[/error]")

        # 2. Local settings (Project Override)
        local_path = os.path.join(os.getcwd(), ".mentask", self.SETTINGS_FILE)
        if os.path.exists(local_path):
            try:
                with open(local_path, encoding="utf-8") as f:
                    local_data = json.load(f)

                    # Security check: Project-local settings should NOT contain API keys
                    found_secrets = [k for k in self.SENSITIVE_KEYS if k in local_data and local_data[k]]
                    if found_secrets:
                        self.console.print(
                            f"[warning][!] Security Warning: Local .mentask/settings.json contains sensitive keys: {', '.join(found_secrets)}. These should be moved to the system keyring or environment variables.[/warning]"
                        )

                    self.settings.update(local_data)
            except Exception as e:
                self.console.print(f"[error][!] Error loading local .mentask/settings.json: {e}[/error]")

        # Load sensitive keys from keyring
        for key in self.SENSITIVE_KEYS:
            try:
                env_var = key.upper()
                stored_val = keyring.get_password(self.SERVICE_NAME, env_var)
                if stored_val:
                    self.settings[key] = stored_val
            except Exception as e:
                self.console.print(f"[error][!] Error accessing keyring for {key}: {e}[/error]")
                # Fallback to env var if keyring fails
                env_val = os.getenv(key.upper())
                if env_val:
                    self.settings[key] = env_val

    def save_settings(self) -> None:
        """Saves current memory settings into the JSON config file.
        Sensitive keys are stored in the system keyring.
        """
        settings_to_save = self.settings.copy()

        # Handle all sensitive keys
        for key in self.SENSITIVE_KEYS:
            val = self.settings.get(key, "")
            if val and val != "STORED_IN_KEYRING":
                try:
                    env_var = key.upper()
                    keyring.set_password(self.SERVICE_NAME, env_var, val)
                    settings_to_save[key] = "STORED_IN_KEYRING"
                except Exception as e:
                    self.console.print(f"[error][X] Error saving {key} to keyring: {e}[/error]")
                    # Ensure the plaintext key is NOT saved to the JSON file on failure
                    settings_to_save[key] = ""

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
        if settings_key and settings_key != "STORED_IN_KEYRING":
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
