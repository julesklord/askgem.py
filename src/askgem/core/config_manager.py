import json
import os
from typing import Optional

from .paths import get_config_path


class ConfigManager:
    """Manages central configuration for the application.

    Validates, loads, and saves the central API keys and preference settings.
    """

    UNENCRYPTED_API_KEY_FILE = ".gemini_api_key_unencrypted"
    SETTINGS_FILE = "settings.json"

    def __init__(self, console):
        """Initializes the ConfigManager and loads default or existing settings.

        Args:
            console: The active rich console instance for logging outputs.
        """
        self.console = console
        self.settings = {
            "model_name": "gemini-2.5-pro",
            "edit_mode": "manual" # "manual" or "auto"
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
                self.console.print(f"[bold red][X] Error loading settings.json: {e}[/bold red]")

    def save_settings(self) -> None:
        """Saves current memory settings into the JSON config file."""
        path = get_config_path(self.SETTINGS_FILE)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            self.console.print(f"[bold red][X] Error saving settings: {e}[/bold red]")

    def load_api_key(self) -> Optional[str]:
        """Attempts to load the API_KEY from available sources.

        First checks the GOOGLE_API_KEY environment variable. If absent,
        it attempts to load the unencrypted local file fallback.

        Returns:
            Optional[str]: The API key string if found, otherwise None.
        """
        # 1. Environment variable
        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key:
            return env_key

        # 2. Unencrypted local file (v1 base legacy fallback)
        path = get_config_path(self.UNENCRYPTED_API_KEY_FILE)
        if os.path.exists(path):
            try:
                with open(path) as key_file:
                    api_key = key_file.read().strip()
                    if api_key:
                        self.console.print(f"[bold yellow][!] API Key loaded from unencrypted file:[/bold yellow] [dim]{path}[/dim]")
                        return api_key
            except OSError as e:
                self.console.print(f"[bold red][X] Error loading API Key from file:[/bold red] {e}")

        return None

    def save_api_key(self, api_key: str) -> bool:
        """Saves the API_KEY as plain text.

        Args:
            api_key (str): The raw string of the Google API Key.

        Returns:
            bool: True if saving was successful, False otherwise.
        """
        path = get_config_path(self.UNENCRYPTED_API_KEY_FILE)
        try:
            with open(path, "w") as key_file:
                key_file.write(api_key.strip())
            self.console.print(f"[bold green][OK] API Key saved in:[/bold green] [dim]{path}[/dim]")
            if os.name != "nt":
                os.chmod(path, 0o600)
            return True
        except OSError as e:
            self.console.print(f"[bold red][X] Error saving API Key:[/bold red] {e}")
            return False
