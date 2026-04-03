"""
Mission and task tracking manager for AskGem.

Handles reading and writing to heartbeat.md, which tracks active
high-level goals and "missions" for the agent.
"""

import os
from .paths import get_heartbeat_path

DEFAULT_HEARTBEAT_TEMPLATE = """# AskGem Active Missions
# Use this for tracking current goals and tasks.

## Tasks
- [ ] Implement Persistent Memory (In Progress)
- [ ] Integrate with TUI Sidebar

## Recent Focus
- Agent cognitive architecture evolution.
"""

class MissionManager:
    """Manages the ~/.askgem/heartbeat.md file."""

    def __init__(self):
        self.path = get_heartbeat_path()
        self._ensure_heartbeat_exists()

    def _ensure_heartbeat_exists(self):
        """Creates heartbeat.md with a template if it doesn't exist."""
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(DEFAULT_HEARTBEAT_TEMPLATE)

    def read_missions(self) -> str:
        """Reads the full content of heartbeat.md.

        Returns:
            str: The raw markdown content.
        """
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def add_task(self, task: str) -> bool:
        """Appends a new task to the 'Tasks' section.

        Args:
            task (str): The task description.

        Returns:
            bool: True if successful.
        """
        content = self.read_missions()
        lines = content.splitlines()
        
        target_index = -1
        for i, line in enumerate(lines):
            if line.strip().lower() == "## tasks":
                target_index = i
                break
        
        if target_index != -1:
            lines.insert(target_index + 1, f"- [ ] {task}")
        else:
            lines.append("\n## Tasks")
            lines.append(f"- [ ] {task}")

        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True
        except Exception:
            return False

    def complete_task(self, task: str) -> bool:
        """Marks a task as completed in heartbeat.md.

        Args:
            task (str): The task text or snippet.

        Returns:
            bool: True if task was found and updated.
        """
        content = self.read_missions()
        lines = content.splitlines()
        updated = False
        
        for i, line in enumerate(lines):
            if task.lower() in line.lower() and "[ ]" in line:
                lines[i] = line.replace("[ ]", "[x]")
                updated = True
        
        if updated:
            try:
                with open(self.path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                return True
            except Exception:
                return False
        return False
