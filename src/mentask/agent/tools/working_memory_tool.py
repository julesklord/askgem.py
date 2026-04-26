import json
from pathlib import Path

from .base import BaseTool, ToolResult


class WorkingMemoryTool(BaseTool):
    """Scratchpad for inter-turn reasoning state."""

    name = "working_memory"
    description = (
        "Store or retrieve temporary reasoning state within the current session. "
        "Use this to remember hypotheses, partial conclusions, or debugging state "
        "across multiple turns. Cleared when session ends."
    )

    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["read", "write", "clear"]},
            "key": {"type": "string", "description": "Memory key (e.g., 'hypothesis', 'next_steps')"},
            "value": {"type": "string", "description": "Value to store (for write action)"},
        },
        "required": ["action", "key"],
    }

    def __init__(self):
        super().__init__()
        self.memory_file = Path.cwd() / ".mentask" / "working_memory.json"

    def _ensure_dir(self):
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

    async def execute(self, action: str, key: str, value: str = "") -> ToolResult:
        data = {}
        if self.memory_file.exists():
            try:
                with open(self.memory_file, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        if action == "read":
            result = data.get(key, f"Key '{key}' not found in working memory.")
            return ToolResult(content=str(result), is_error=False)

        elif action == "write":
            self._ensure_dir()
            data[key] = value
            try:
                with open(self.memory_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return ToolResult(content=f"Stored '{key}' in working memory.", is_error=False)
            except Exception as e:
                return ToolResult(content=f"Failed to write: {e}", is_error=True)

        elif action == "clear":
            if key in data:
                del data[key]
                try:
                    with open(self.memory_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                    return ToolResult(content=f"Cleared '{key}' from working memory.", is_error=False)
                except Exception as e:
                    return ToolResult(content=f"Failed to clear: {e}", is_error=True)
            return ToolResult(content=f"Key '{key}' not found.", is_error=False)

        return ToolResult(content=f"Unknown action: {action}", is_error=True)
