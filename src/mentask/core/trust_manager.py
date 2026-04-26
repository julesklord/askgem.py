import json
import os

from .paths import get_global_config_dir


class TrustManager:
    """Manages universal trusted directories for mentask."""

    TRUST_FILE = "trusted.json"

    def __init__(self):
        self.path = get_global_config_dir() / self.TRUST_FILE
        self.trusted_paths: set[str] = set()
        self.session_trusted_paths: set[str] = set()
        # self.load_trust() - now called async by ExecutionManager

    async def load_trust(self) -> None:
        """Loads trusted paths from the global config directory."""
        if self.path.exists():
            try:
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.trusted_paths = set(os.path.abspath(p) for p in data)
            except Exception:
                pass

    async def save_trust(self) -> None:
        """Async-safe trust persistence."""
        import asyncio

        try:
            await asyncio.to_thread(self._write_trust_file)
        except Exception as e:
            import logging

            logging.getLogger("mentask").error(f"Failed to save trust config: {e}")

    def _write_trust_file(self) -> None:
        """Síncrono, corrido en thread pool."""
        with open(self.path, "w", encoding="utf-8") as f:
            import json

            json.dump(list(self.trusted_paths), f, indent=4)

    def is_trusted(self, path: str) -> bool:
        """Checks if a given path (or any of its parents) is trusted (session or permanent)."""
        abs_path = os.path.abspath(path)

        # Check direct or parent matches in both permanent and session sets
        all_trusted = self.trusted_paths.union(self.session_trusted_paths)
        return any(abs_path == trusted or abs_path.startswith(trusted + os.sep) for trusted in all_trusted)

    async def add_trust(self, path: str) -> None:
        """Adds a path to the universal trusted list."""
        abs_path = os.path.abspath(path)
        self.trusted_paths.add(abs_path)
        await self.save_trust()

    def add_session_trust(self, path: str) -> None:
        """Adds a path to the session-only trusted list."""
        abs_path = os.path.abspath(path)
        self.session_trusted_paths.add(abs_path)

    async def remove_trust(self, path: str) -> None:
        """Removes a path from the trust list."""
        abs_path = os.path.abspath(path)
        if abs_path in self.trusted_paths:
            self.trusted_paths.remove(abs_path)
            await self.save_trust()
