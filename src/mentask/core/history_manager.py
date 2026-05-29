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
        self._migrate_old_history()
        self.current_session_id = str(uuid.uuid4())

    @staticmethod
    def _migrate_old_history():
        """Moves session files from old ``history/`` dir to ``sessions/``."""
        from .paths import get_config_dir

        config = Path(get_config_dir())
        old_dir = config / "history"
        new_dir = config / "sessions"
        if old_dir.is_dir() and new_dir.is_dir() and old_dir != new_dir:
            import shutil

            for f in old_dir.glob("*.json"):
                dest = new_dir / f.name
                if not dest.exists():
                    shutil.move(str(f), str(dest))
                    _logger.debug("Migrated %s → %s", f.name, dest)
            try:
                old_dir.rmdir()
            except OSError:
                _logger.debug("old history/ dir not empty, left in place")

    def _deserialize_message(self, data: dict) -> Message | None:
        try:
            from ..agent.schema import AssistantMessage, ToolCall

            role_str = data.get("role", "")
            metadata = data.get("metadata") or {}
            content = data.get("content", "")
            thought = data.get("thought")

            if role_str == "assistant":
                # Reconstruct tool_calls list
                raw_calls = data.get("tool_calls") or []
                tool_calls = []
                for tc in raw_calls:
                    if isinstance(tc, dict) and "name" in tc:
                        tool_calls.append(
                            ToolCall(
                                id=tc.get("id", ""),
                                name=tc["name"],
                                arguments=tc.get("arguments", {}),
                            )
                        )
                return AssistantMessage(
                    role=Role(role_str),
                    content=content,
                    thought=thought,
                    metadata=metadata,
                    model=data.get("model", ""),
                    tool_calls=tool_calls,
                )

            return Message(
                role=Role(role_str),
                content=content,
                thought=thought,
                metadata=metadata,
            )
        except (KeyError, ValueError) as e:
            _logger.error(f"Could not deserialize a history entry: {e}")
            return None

    async def save_session(self, messages: list[Message]) -> None:
        """Saves current message history to a JSON file asynchronously."""
        import aiofiles
        file_p = Path(self.history_dir) / f"{self.current_session_id}.json"
        try:
            serialized = json.dumps(
                [m.__dict__ for m in messages],
                indent=4,
                default=json_serializable,
            )
            async with aiofiles.open(file_p, "w", encoding="utf-8") as f:
                await f.write(serialized)
        except Exception as e:
            _logger.error(f"Error saving session history: {e}")

    async def load_session(self, session_id: str) -> list[Message] | None:
        """Loads a previously saved session from disk asynchronously."""
        import aiofiles
        base_dir = Path(self.history_dir).resolve()
        file_p = (base_dir / f"{session_id}.json").resolve()

        if base_dir not in file_p.parents:
            _logger.error(f"Security: Attempted access outside history dir: {file_p}")
            return None

        if not file_p.exists():
            return None

        try:
            async with aiofiles.open(file_p, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                messages = [self._deserialize_message(m) for m in data]
                return [m for m in messages if m is not None]
        except Exception as e:
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

    def reset(self) -> None:
        """Generates a new session ID for a fresh start."""
        self.current_session_id = str(uuid.uuid4())

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
