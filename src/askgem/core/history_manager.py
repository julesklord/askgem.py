"""
Session history persistence module.

It manages saving, loading, and listing prior chat contexts to and from disk.
It does NOT manage API integrations or session configurations directly.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.genai import types

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

    def _content_to_dict(self, content: types.Content) -> Dict[str, Any]:
        """Converts a SDK Content object into a JSON-serializable dictionary.

        Args:
            content (types.Content): The generative AI SDK content struct.

        Returns:
            Dict[str, Any]: A serializable dictionary equivalent.
        """
        parts_list = []
        for part in content.parts:
            if part.text:
                parts_list.append({"text": part.text})
            elif part.function_call:
                parts_list.append(
                    {
                        "function_call": {
                            "name": part.function_call.name,
                            "args": _safe_dict_cast(part.function_call.args),
                        }
                    }
                )
            elif part.function_response:
                parts_list.append(
                    {
                        "function_response": {
                            "name": part.function_response.name,
                            "response": _safe_dict_cast(part.function_response.response),
                        }
                    }
                )
        return {"role": content.role, "parts": parts_list}

    def _dict_to_content(self, data: Dict[str, Any]) -> Optional[types.Content]:
        """Rebuilds a SDK Content object from a stored dictionary.

        Args:
            data (Dict[str, Any]): The loaded dictionary data block.

        Returns:
            Optional[types.Content]: Formatted content, or None on failure.
        """
        try:
            parts = []
            for p in data.get("parts", []):
                if "text" in p:
                    parts.append(types.Part.from_text(text=p["text"]))
                elif "function_call" in p:
                    parts.append(
                        types.Part.from_function_call(
                            name=p["function_call"]["name"],
                            args=p["function_call"]["args"],
                        )
                    )
                elif "function_response" in p:
                    parts.append(
                        types.Part.from_function_response(
                            name=p["function_response"]["name"],
                            response=p["function_response"]["response"],
                        )
                    )
            if not parts:
                return None
            return types.Content(role=data.get("role", "user"), parts=parts)
        except Exception as e:
            self.console.print(f"[dim red]Warning: Could not deserialize a history entry: {e}[/dim red]")
            return None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def save_session(self, history: List[types.Content]) -> None:
        """Serializes the current chat history to disk under the active session ID.

        Safe to call repeatedly — it overwrites the same file each time.

        Args:
            history (List[types.Content]): Current conversation list from SDK.
        """
        if not history:
            return

        filepath = os.path.join(self.history_dir, f"{self.current_session_id}.json")
        try:
            serialized = [self._content_to_dict(h) for h in history]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.console.print(f"[dim red]Error saving session history: {e}[/dim red]")

    def load_session(self, session_id: str) -> Optional[List[types.Content]]:
        """Loads a previously saved session from disk and applies context windows.

        Args:
            session_id (str): Formatted ID reference pointing to a `.json` disk record.

        Returns:
            Optional[List[types.Content]]: The filtered message list, or None if invalid.
        """
        filepath = os.path.join(self.history_dir, f"{session_id}.json")
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
            while data and len(json.dumps(data, ensure_ascii=False)) > MAX_HISTORY_CHARS:
                data = data[1:]

            # Final sanity check: context must always start with a 'user' turn to avoid model error
            while data and data[0].get("role") != "user":
                data = data[1:]

            contents = [self._dict_to_content(d) for d in data]
            # Filter out any entries that failed deserialization
            return [c for c in contents if c is not None]

        except Exception as e:
            self.console.print(f"[dim red]Error loading session '{session_id}': {e}[/dim red]")
            return None

    def list_sessions(self) -> List[str]:
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
        filepath = os.path.join(self.history_dir, f"{session_id}.json")
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception:
            return False
