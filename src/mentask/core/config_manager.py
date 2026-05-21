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
        "mistral_api_key",
        "groq_api_key",
        "together_api_key",
        "perplexity_api_key",
        "google_search_api_key",
        "google_cx_id",
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
            "theme": "neon_cyan",  # Default neon theme
            "available_themes": [
                "indigo",
                "emerald",
                "crimson",
                "amber",
                "cyberpunk",
                "dracula",
                "nord",
                "sakura",
                "neon_cyan",
                "neon_pink",
                "neon_purple",
                "neon_matrix",
            ],
            "context_type": "general",
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
            "readonly_mode": False,
        }
        self.load_settings()

    def get_resolved_theme(self):
        """Resolves a theme.

        Returns:
            ThemeConfig: The resolved theme configuration.
        """
        theme_name = self.settings.get("theme", "neon_cyan")
        if not isinstance(theme_name, str):
            theme_name = "neon_cyan"

        # Lazy import to avoid circular dependencies
        from ..cli.themes import get_theme

        return get_theme(theme_name)

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
                    if isinstance(data, dict):
                        self.settings.update(data)
            except Exception as e:
                self.console.print(f"[error][X] Error loading global settings.json: {e}[/error]")

        # 2. Local settings (Project Override)
        local_path = os.path.join(os.getcwd(), ".mentask", self.SETTINGS_FILE)
        if os.path.exists(local_path):
            try:
                with open(local_path, encoding="utf-8") as f:
                    local_data = json.load(f)

                    if isinstance(local_data, dict):
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
                    if not isinstance(val, str):
                        val = str(val)
                    keyring.set_password(self.SERVICE_NAME, env_var, val)
                    settings_to_save[key] = "STORED_IN_KEYRING"
                except Exception as e:
                    self.console.print(f"[error][X] Error saving {key} to keyring: {e}[/error]")
                    # Ensure the plaintext key is NOT saved to the JSON file on failure
                    settings_to_save[key] = ""
                    self.settings[key] = ""  # Clear from memory to prevent retry/leak

        path = get_config_path(self.SETTINGS_FILE)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(settings_to_save, f, indent=4)
        except Exception as e:
            self.console.print(f"[error][X] Error saving settings: {e}[/error]")

    def detect_provider(self, api_key: str) -> str:
        """Heuristically detects the provider from the API key format.

        Args:
            api_key: The raw API key string.

        Returns:
            str: 'google', 'openai', 'anthropic', 'deepseek', 'groq', etc.
        """
        key = api_key.strip()
        if key.startswith("sk-ant-"):
            return "anthropic"
        if key.startswith("sk-proj-"):
            return "openai"
        if key.startswith("gsk_"):
            return "groq"
        if key.startswith("sk-"):
            # Could be DeepSeek or generic OpenAI
            return "openai"
        if key.startswith("AIzaSy"):
            return "google"
        return "google"  # Default fallback

    def load_api_key(self, provider: str = "google", return_source: bool = False) -> Any:
        """Attempts to load the API_KEY from available sources for a given provider.

        Args:
            provider (str): The provider name.
            return_source (bool): If True, returns a tuple (key, source_name).

        Priority:
            1. Local settings.json ({provider}_api_key) - Project Specific
            2. System keyring (Global) - Explicitly set via /auth
            3. Environment variable ({PROVIDER}_API_KEY) - System default
        """
        provider = provider.lower()
        env_var = f"{provider.upper()}_API_KEY"

        # 1. Local Settings (Project Override)
        settings_key = self.settings.get(f"{provider}_api_key")
        if isinstance(settings_key, str) and settings_key and settings_key != "STORED_IN_KEYRING":
            return (settings_key, "Local Settings") if return_source else settings_key

        # 2. System Keyring (Global - Explicitly set)
        try:
            keyring_key = keyring.get_password(self.SERVICE_NAME, env_var)
            if keyring_key:
                return (keyring_key, "Keyring") if return_source else keyring_key
        except Exception as e:
            self.console.print(f"[error][!] Error accessing keyring for {provider}: {e}[/error]")

        # 3. Environment variable (Fallback)
        env_key = os.getenv(env_var)
        if env_key:
            return (env_key, "Environment Variable") if return_source else env_key

        # Fallback for Google specifically
        if provider == "google":
            for fallback in ["GEMINI_API_KEY", "GEM_API_KEY"]:
                val = os.getenv(fallback)
                if val:
                    return (val, "Environment Variable") if return_source else val

        return (None, None) if return_source else None

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
