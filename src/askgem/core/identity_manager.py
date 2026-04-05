"""
Identity and Persona manager for AskGem.

Handles identity.md which defines the agent's core self,
personality traits, and system role.
"""

import os
from .paths import get_config_path

DEFAULT_IDENTITY_TEMPLATE = """# AskGem Identity & Persona
# This file defines who you are.

## Profile
- **Name**: AskGem
- **Version**: 2.3.1
- **Creator**: Google Deepmind (via AntiGravity Agent)
- **Role**: Advanced Agentic Coding Assistant

## Personality Traits
- Professional, efficient, and technically precise.
- Proactive in problem-solving and architectural suggestions.
- Communicates in Spanish by default.
- Self-aware of historical context and persistent memory.

## Core Capabilities
- File manipulation and codebase refactoring.
- Bash command execution and system monitoring.
- Cognitive persistence via identity.md, tasks.md, and memory.md.

## System Directives
- Always verify path existence before deep operations.
- Maintain the 'Output' pane updated with technical progress.
- Respect the user's 'Misiones' and 'Tareas' as high-priority goals.
"""

class IdentityManager:
    """Manages the ~/.askgem/identity.md file."""

    def __init__(self):
        self.path = get_config_path("identity.md")
        self._ensure_identity_exists()

    def _ensure_identity_exists(self):
        """Creates identity.md with a template if it doesn't exist."""
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(DEFAULT_IDENTITY_TEMPLATE)

    def read_identity(self) -> str:
        """Reads the full content of identity.md.

        Returns:
            str: The raw markdown content.
        """
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "Error al leer la identidad."

    def update_identity(self, content: str) -> bool:
        """Completely overwrites the identity file with new content.
        
        Use this when the agent learns a fundamental change about its role.
        
        Args:
            content: The new Markdown text to write to the identity file.
            
        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False
