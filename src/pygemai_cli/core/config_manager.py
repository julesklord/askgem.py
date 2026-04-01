import os
from pathlib import Path
from typing import Optional

# Base directory paths definition
def get_config_dir() -> Path:
    """Returns the configuration directory ~/.pygemai."""
    config_dir = Path.home() / ".pygemai"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_config_path(filename: str) -> str:
    """Returns the absolute path of a PyGemAi configuration file inside the config dir."""
    return str(get_config_dir() / filename)

class ConfigManager:
    """
    Manages central configuration for the v2 app,
    particularly the loading and saving of API keys.
    """
    
    UNENCRYPTED_API_KEY_FILE = ".gemini_api_key_unencrypted"
    
    def __init__(self, console):
        self.console = console
        
    def load_api_key(self) -> Optional[str]:
        """
        Attempts to load the API_KEY in the following order:
        1. Environment Variable
        2. Unencrypted config file fallback
        (Encrypted file support moved to later phase)
        """
        
        # 1. Environment variable
        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key:
            return env_key
            
        # 2. Unencrypted local file (v1 base legacy fallback)
        path = get_config_path(self.UNENCRYPTED_API_KEY_FILE)
        if os.path.exists(path):
            try:
                with open(path, "r") as key_file:
                    api_key = key_file.read().strip()
                    if api_key:
                        self.console.print(f"[bold yellow][!] API Key loaded from unencrypted file:[/bold yellow] [dim]{path}[/dim]")
                        return api_key
            except OSError as e:
                self.console.print(f"[bold red][X] Error loading API Key from file:[/bold red] {e}")
                
        return None
        
    def save_api_key(self, api_key: str) -> bool:
        """
        Saves the API_KEY as plain text for v2.0 development purposes.
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
