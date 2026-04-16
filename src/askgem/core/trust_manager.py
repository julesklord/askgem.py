import json
import os

from .paths import get_global_config_dir


class TrustManager:
    """Manages universal trusted directories for AskGem."""

    TRUST_FILE = "trusted.json"

    def __init__(self):
        self.path = get_global_config_dir() / self.TRUST_FILE
        self.trusted_paths: set[str] = set()
        self.load_trust()

    def load_trust(self) -> None:
        """Loads trusted paths from the global config directory."""
        if self.path.exists():
            try:
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.trusted_paths = set(os.path.abspath(p) for p in data)
            except Exception:
                pass

    def save_trust(self) -> None:
        """Saves the current set of trusted paths to the global config."""
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(list(self.trusted_paths), f, indent=4)
        except Exception:
            pass

    def is_trusted(self, path: str) -> bool:
        """Checks if a given path (or any of its parents) is trusted."""
        abs_path = os.path.abspath(path)

        # Check direct or parent matches
        return any(abs_path == trusted or abs_path.startswith(trusted + os.sep) for trusted in self.trusted_paths)

    def add_trust(self, path: str) -> None:
        """Adds a path to the universal trusted list."""
        abs_path = os.path.abspath(path)
        self.trusted_paths.add(abs_path)
        self.save_trust()

    def remove_trust(self, path: str) -> None:
        """Removes a path from the trust list."""
        abs_path = os.path.abspath(path)
        if abs_path in self.trusted_paths:
            self.trusted_paths.remove(abs_path)
            self.save_trust()
