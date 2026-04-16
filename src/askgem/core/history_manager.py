"""
Session history persistence module.

It manages saving, loading, and listing prior chat contexts to and from disk.
It does NOT manage API integrations or session configurations directly.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any

from ..agent.schema import AssistantMessage, Message, Role, ToolCall, UsageMetrics
from .paths import get_history_dir

# Maximum number of messages to inject back into context.
MAX_CONTEXT_WINDOW = 20

# Maximum aggregate character count for the active history window.
# Approximately 10k-15k tokens to avoid 429 errors on free tier TPM limits.
MAX_HISTORY_CHARS = 40000


def _safe_dict_cast(obj: Any) -> dict:
    """Safely converts protobuf MapComposite / repeated container objects.

    Args:
        obj: The object to safely cast to a dictionary.

    Returns:
        dict: The resulting dictionary structure.
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    # MapComposite and similar protobuf wrappers support .items()
    try:
        return {k: v for k, v in obj.items()}
    except (AttributeError, TypeError):
        pass
    # Last resort: plain cast — may raise on exotic types
    try:
        return dict(obj)
    except Exception:
        return {"__raw__": repr(obj)}


class HistoryManager:
    """Handles persistent storage and retrieval of chat sessions.

    Applies a rolling context window to cap token usage on session reload.
    """

    def __init__(self, console):
        """Initializes the HistoryManager and active session parameters.

        Args:
            console: The interactive rich console element.
        """
        self.console = console
        self.history_dir = get_history_dir()
        # Each run gets a unique timestamped session ID
        self.current_session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f"_{uuid.uuid4().hex[:6]}"

    # ------------------------------------------------------------------ #
    # Serialization helpers (google-genai v0.2.0 Content <-> JSON)        #
    # ------------------------------------------------------------------ #

    def _message_to_dict(self, msg: Message) -> dict[str, Any]:
        """Converts a Message Pydantic model into a JSON-serializable dictionary."""
        return msg.model_dump(mode="json")

    def _dict_to_message(self, data: dict[str, Any]) -> Message | None:
        """Rebuilds a Message object from a stored dictionary."""
        try:
            role = data.get("role")
            if role == Role.ASSISTANT:
                return AssistantMessage.model_validate(data)
            return Message.model_validate(data)
        except Exception as e:
            self.console.print(f"[dim red]Warning: Could not deserialize a history entry: {e}[/dim red]")
            return None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def save_session(self, history: list[Message]) -> None:
        """Serializes the current chat history to disk under the active session ID.

        Safe to call repeatedly — it overwrites the same file each time.

        Args:
            history (List[Message]): Current conversation list (Pydantic).
        """
        if not history:
            return

        filepath = os.path.join(self.history_dir, f"{self.current_session_id}.json")
        try:
            serialized = [self._message_to_dict(h) for h in history if not h.is_virtual]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.console.print(f"[dim red]Error saving session history: {e}[/dim red]")

    def load_session(self, session_id: str) -> list[Message] | None:
        """Loads a previously saved session from disk and applies context windows.

        Args:
            session_id (str): Formatted ID reference pointing to a `.json` disk record.

        Returns:
            Optional[List[Message]]: The filtered message list, or None if invalid.
        """
        filepath = os.path.abspath(os.path.join(self.history_dir, f"{session_id}.json"))
        base_dir = os.path.abspath(self.history_dir)
        if os.path.commonpath([base_dir, filepath]) != base_dir:
            return None

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            # Token optimization: start with the most recent N messages
            if len(data) > MAX_CONTEXT_WINDOW:
                data = data[-MAX_CONTEXT_WINDOW:]

            # Aggregate character count check to avoid TPM/429 errors
            # We keep reducing the window if it exceeds our safety threshold
            if data:
                item_lengths = [len(json.dumps(item, ensure_ascii=False)) for item in data]
                # Calculate total JSON length: items + separators (', ') + brackets ('[]')
                total_len = sum(item_lengths) + (len(data) - 1) * 2 + 2

                removed_count = 0
                while removed_count < len(data) and total_len > MAX_HISTORY_CHARS:
                    total_len -= item_lengths[removed_count]
                    if len(data) - removed_count > 1:
                        total_len -= 2  # account for ', '
                    removed_count += 1

                if removed_count > 0:
                    data = data[removed_count:]

            # Final sanity check: context must always start with a 'user' turn to avoid model error
            while data and data[0].get("role") != "user":
                data = data[1:]

            messages = [self._dict_to_message(d) for d in data]
            # Filter out any entries that failed deserialization
            return [m for m in messages if m is not None]

        except Exception as e:
            self.console.print(f"[dim red]Error loading session '{session_id}': {e}[/dim red]")
            return None

    def list_sessions(self) -> list[str]:
        """Returns all saved session IDs sorted chronologically.

        Returns:
            List[str]: Identifier list, newest last.
        """
        try:
            files = [f for f in os.listdir(self.history_dir) if f.endswith(".json")]
            files.sort()
            return [f.replace(".json", "") for f in files]
        except Exception:
            return []

    def delete_session(self, session_id: str) -> bool:
        """Removes a specific session file from disk.

        Args:
            session_id (str): Target history object ID.

        Returns:
            bool: True if targeted json existed and was unlinked, False otherwise.
        """
        filepath = os.path.abspath(os.path.join(self.history_dir, f"{session_id}.json"))
        base_dir = os.path.abspath(self.history_dir)
        if os.path.commonpath([base_dir, filepath]) != base_dir:
            return False

        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception:
            return False
