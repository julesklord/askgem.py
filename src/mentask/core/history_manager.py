"""
Session history persistence module.

It manages saving, loading, and listing prior chat contexts to and from disk.
"""

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any

from ..agent.schema import Message, Role
from ..cli.console import console

_TIMESTAMP_PATTERN = re.compile(r"^\d{8}_\d{6}$")


def _is_timestamp_folder(name: str) -> bool:
    return bool(_TIMESTAMP_PATTERN.match(name))

_logger = logging.getLogger("mentask.core.history")


def json_serializable(obj: Any) -> Any:
    """Helper to convert complex objects into JSON-friendly dicts."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    try:
        return dict(obj)
    except Exception as e:
        _logger.debug("Cannot convert object to dict: %s", e, exc_info=True)
        return {"__raw__": repr(obj)}


class HistoryManager:
    """Handles persistent storage and retrieval of chat sessions."""

    def __init__(self, ui_console=None):
        from .paths import get_history_dir

        self.console = ui_console or console
        self.history_dir = get_history_dir()
        self._migrate_old_history()
        self.current_session_id = str(uuid.uuid4())

        # Silent startup cleanup of residual/old files
        try:
            self.cleanup_old_sessions()
            self.cleanup_old_backups()
        except Exception as e:
            _logger.debug("Failed to perform startup cleanup: %s", e)

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

    def cleanup_old_sessions(self, max_age_days: int = 30, max_count: int = 100) -> None:
        """Cleans up session history files based on age and count limits."""
        import time

        try:
            p = Path(self.history_dir)
            if not p.is_dir():
                return

            files = list(p.glob("*.json"))
            if not files:
                return

            now = time.time()
            cutoff = now - (max_age_days * 86400)

            # Sort files by modification time (oldest first)
            files.sort(key=lambda f: f.stat().st_mtime)

            # Delete files older than max_age_days
            remaining_files = []
            for f in files:
                # Do not delete the current session if it somehow already exists
                if f.stem == self.current_session_id:
                    remaining_files.append(f)
                    continue

                mtime = f.stat().st_mtime
                if mtime < cutoff:
                    try:
                        f.unlink(missing_ok=True)
                        _logger.debug("Deleted stale session file: %s (older than %d days)", f.name, max_age_days)
                    except OSError as e:
                        _logger.warning("Could not delete stale session file %s: %s", f.name, e)
                else:
                    remaining_files.append(f)

            # Delete oldest files if total count exceeds max_count
            if len(remaining_files) > max_count:
                to_delete_count = len(remaining_files) - max_count
                for i in range(to_delete_count):
                    f = remaining_files[i]
                    if f.stem == self.current_session_id:
                        continue
                    try:
                        f.unlink(missing_ok=True)
                        _logger.debug("Deleted oldest session file: %s (exceeded count limit of %d)", f.name, max_count)
                    except OSError as e:
                        _logger.warning("Could not delete oldest session file %s: %s", f.name, e)
        except Exception as e:
            _logger.error("Error during session cleanup: %s", e)

    def cleanup_old_backups(self, max_age_days: int = 7) -> None:
        """Cleans up temporary file backups older than max_age_days."""
        import shutil
        import time

        from .paths import get_backups_dir

        try:
            backup_dir = get_backups_dir()
            if not backup_dir.is_dir():
                return

            now = time.time()
            cutoff = now - (max_age_days * 86400)

            for ts_folder in backup_dir.iterdir():
                if ts_folder.is_dir() and _is_timestamp_folder(ts_folder.name):
                    try:
                        # Check modification time of the folder
                        mtime = ts_folder.stat().st_mtime
                        if mtime < cutoff:
                            shutil.rmtree(ts_folder)
                            _logger.debug("Deleted stale backup folder: %s (older than %d days)", ts_folder.name, max_age_days)
                    except Exception as e:
                        _logger.warning("Could not delete stale backup folder %s: %s", ts_folder.name, e)
        except Exception as e:
            _logger.error("Error during backup cleanup: %s", e)

