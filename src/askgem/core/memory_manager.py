"""
General persistent memory manager for AskGem.

Handles reading and writing to memory.md, which stores long-term facts,
user preferences, and project-specific context.
"""

import os

from .paths import get_memory_path

DEFAULT_MEMORY_TEMPLATE = """# AskGem Persistent Memory
# Last Updated: {date}

## User Profile & Preferences
- Preferred Language: Spanish (Default)
- Tech Stack: Python, Gemini API

## Project Context
- Current Project: askgem.py
- Environment: Linux

## Lessons Learned & Facts
- 

## Rules & Constraints
- Always communicate and perform internal reasoning in Spanish.
"""

class MemoryManager:
    """Manages the ~/.askgem/memory.md file."""

    def __init__(self):
        self.path = get_memory_path()
        self._ensure_memory_exists()

    def _ensure_memory_exists(self):
        """Creates memory.md with a template if it doesn't exist."""
        if not os.path.exists(self.path):
            from datetime import datetime
            content = DEFAULT_MEMORY_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d"))
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(content)

    def read_memory(self) -> str:
        """Reads the full content of memory.md.

        Returns:
            str: The raw markdown content.
        """
        try:
            with open(self.path, encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def add_fact(self, fact: str, category: str = "Lessons Learned & Facts") -> bool:
        """Appends a new fact to a specific category in memory.md.

        Args:
            fact (str): The fact to remember.
            category (str): The markdown section to append to.

        Returns:
            bool: True if successful.
        """
        content = self.read_memory()
        lines = content.splitlines()

        target_index = -1
        for i, line in enumerate(lines):
            if line.strip().lower() == f"## {category}".lower():
                target_index = i
                break

        if target_index != -1:
            # Insert after the header
            lines.insert(target_index + 1, f"- {fact}")
        else:
            # Category not found, append to end
            lines.append(f"\n## {category}")
            lines.append(f"- {fact}")

        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True
        except Exception:
            return False

    def reset_memory(self):
        """Wipes the memory file and recreates it from template."""
        if os.path.exists(self.path):
            os.remove(self.path)
        self._ensure_memory_exists()
