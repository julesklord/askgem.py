"""
Tasks and dynamic functions manager for AskGem.

Handles tasks.md which tracks active goals, scheduled jobs,
and AI-generated functions that can be refined over time.
"""

import os
from .paths import get_tasks_path

DEFAULT_TASKS_TEMPLATE = """# AskGem Active Tasks & Functions
# Use this for tracking current goals and system evolution.

## Tasks
- [ ] Implement Unified Persistence (Tasks & Identity)
- [ ] Refine self-awareness of historical data

## Scheduled Functions
- [Log Cleanup]: Periodically monitor log size.
- [Memory Summarization]: Triggered at prompt threshold.

## Machine-Generated Goals
- None yet.
"""

class TasksManager:
    """Manages the ~/.askgem/tasks.md file."""

    def __init__(self):
        self.path = get_tasks_path()
        self._ensure_tasks_exists()

    def _ensure_tasks_exists(self):
        """Creates tasks.md with a template if it doesn't exist."""
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(DEFAULT_TASKS_TEMPLATE)

    def read_tasks(self) -> str:
        """Reads the full content of tasks.md.

        Returns:
            str: The raw markdown content.
        """
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""

    def add_task(self, task: str) -> bool:
        """Appends a new task to the 'Tasks' section.

        Args:
            task (str): The task description.

        Returns:
            bool: True if successful.
        """
        content = self.read_tasks()
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
        except OSError:
            return False

    def complete_task(self, task: str) -> bool:
        """Marks a task as completed in tasks.md.

        Args:
            task (str): The task text or snippet.

        Returns:
            bool: True if task was found and updated.
        """
        content = self.read_tasks()
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
            except OSError:
                return False
        return False

    def update_tasks(self, content: str) -> bool:
        """Overwrite the entire tasks file."""
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except OSError:
            return False
