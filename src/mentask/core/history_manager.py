"""
Session history persistence module.

It manages saving, loading, and listing prior chat contexts to and from disk.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from ..agent.schema import Message, Role
from ..cli.console import console

_logger = logging.getLogger("mentask")


def json_serializable(obj: Any) -> Any:
    """Helper to convert complex objects into JSON-friendly dicts."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    try:
        return dict(obj)
    except Exception:
        return {"__raw__": repr(obj)}


class HistoryManager:
    """Handles persistent storage and retrieval of chat sessions."""

    def __init__(self, ui_console=None):
        from .paths import get_history_dir

        self.console = ui_console or console
        self.history_dir = get_history_dir()
        self.current_session_id = str(uuid.uuid4())[:8]

    def _deserialize_message(self, data: dict) -> Message | None:
        try:
            # Handle cases where metadata might be missing in older history files
            metadata = data.get("metadata")
            if metadata is None:
                metadata = {}

            return Message(
                role=Role(data["role"]),
                content=data["content"],
                metadata=metadata,
            )
        except (KeyError, ValueError) as e:
            _logger.error(f"Could not deserialize a history entry: {e}")
            return None

    def save_session(self, messages: list[Message]) -> None:
        """Saves current message history to a JSON file."""
        file_p = Path(self.history_dir) / f"{self.current_session_id}.json"
        try:
            # Atomic save can be implemented here too if needed
            with open(file_p, "w", encoding="utf-8") as f:
                json.dump(
                    [m.__dict__ for m in messages],
                    f,
                    indent=4,
                    default=json_serializable,
                )
        except OSError as e:
            _logger.error(f"Error saving session history: {e}")

    def load_session(self, session_id: str) -> list[Message] | None:
        """Loads a previously saved session from disk."""
        base_dir = Path(self.history_dir).resolve()
        file_p = (base_dir / f"{session_id}.json").resolve()

        if base_dir not in file_p.parents:
            _logger.error(f"Security: Attempted access outside history dir: {file_p}")
            return None

        if not file_p.exists():
            return None

        try:
            with open(file_p, encoding="utf-8") as f:
                data = json.load(f)
                messages = [self._deserialize_message(m) for m in data]
                return [m for m in messages if m is not None]
        except (json.JSONDecodeError, OSError) as e:
            _logger.error(f"Error loading session '{session_id}': {e}")
            return None

    def list_sessions(self) -> list[str]:
        """Returns all saved session IDs sorted chronologically."""
        try:
            p = Path(self.history_dir)
            files = sorted(p.glob("*.json"), key=lambda f: f.stat().st_mtime)
            return [f.stem for f in files]
        except OSError as e:
            _logger.error(f"Failed to list sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """Removes a specific session file from disk."""
        filepath = Path(self.history_dir) / f"{session_id}.json"
        try:
            if filepath.exists():
                filepath.unlink(missing_ok=True)
                _logger.info(f"Deleted session file: {filepath}")
                return True
            return False
        except OSError as e:
            _logger.error(f"Failed to delete session {session_id}: {e}")
            return False
