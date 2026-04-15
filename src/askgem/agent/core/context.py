"""
Context management module for AskGem.

Handles system instruction assembly (Memory, Missions, OS),
project structure discovery, and context window optimization.
"""

import logging
import os
import platform
from pathlib import Path

from ...core.i18n import _
from ...core.memory_manager import MemoryManager
from ...core.mission_manager import MissionManager

_logger = logging.getLogger("askgem")

# Marker files that reveal the type of project
_PROJECT_MARKERS = {
    "pyproject.toml": "Python (pyproject)",
    "setup.py": "Python (setup.py)",
    "requirements.txt": "Python (pip)",
    "package.json": "Node.js / JavaScript",
    "tsconfig.json": "TypeScript",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "Makefile": "C/C++ or generic Make",
    "CMakeLists.txt": "C/C++ (CMake)",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java/Kotlin (Gradle)",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "pubspec.yaml": "Dart/Flutter",
}

# Directories to skip during blueprint scan
_SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv",
    ".askgem", ".tox", "dist", "build", ".eggs", ".mypy_cache", ".ruff_cache",
    ".pytest_cache", ".next", "target", "coverage",
}


class ContextManager:
    """Manages the semantic context, project awareness, and memory of the agent."""

    def __init__(self):
        self.memory = MemoryManager()
        self.mission = MissionManager()

    # ------------------------------------------------------------------
    # Project Blueprint (auto-discovery)
    # ------------------------------------------------------------------
    def _get_project_blueprint(self, max_depth: int = 2) -> str:
        """Scans the CWD up to *max_depth* levels and returns a concise
        directory tree together with detected project type(s).

        The output is designed to be injected directly into the system prompt
        so the agent is aware of the project layout from turn 0.
        """
        cwd = Path.cwd()
        detected_types: list[str] = []
        tree_lines: list[str] = []

        def _walk(directory: Path, prefix: str, depth: int):
            if depth > max_depth:
                return
            try:
                entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            except PermissionError:
                return

            # Filter out hidden/skipped dirs
            entries = [
                e for e in entries
                if not (e.is_dir() and e.name in _SKIP_DIRS)
                and not (e.name.startswith(".") and e.is_dir() and e.name != ".askgem")
            ]

            for i, entry in enumerate(entries):
                is_last = (i == len(entries) - 1)
                connector = "└── " if is_last else "├── "
                child_prefix = prefix + ("    " if is_last else "│   ")

                if entry.is_dir():
                    tree_lines.append(f"{prefix}{connector}{entry.name}/")
                    _walk(entry, child_prefix, depth + 1)
                else:
                    # Detect project type from marker files
                    if entry.name in _PROJECT_MARKERS:
                        detected_types.append(_PROJECT_MARKERS[entry.name])
                    tree_lines.append(f"{prefix}{connector}{entry.name}")

        _walk(cwd, "", 0)

        # Assemble output
        project_type_str = ", ".join(set(detected_types)) if detected_types else "Unknown"
        blueprint = f"Project Root: {cwd.name}/\n"
        blueprint += f"Detected Type: {project_type_str}\n"
        blueprint += "```\n"
        blueprint += "\n".join(tree_lines[:80])  # Cap at 80 lines to save tokens
        if len(tree_lines) > 80:
            blueprint += f"\n... ({len(tree_lines) - 80} more entries)\n"
        blueprint += "\n```"
        return blueprint

    # ------------------------------------------------------------------
    # System Instruction Builder
    # ------------------------------------------------------------------
    def build_system_instruction(self) -> str:
        """Assembles the full system instruction string including
        project structure, persistent memory, and active missions."""

        # Base context from localization files
        base_context = _("sys.context", os=f"{platform.system()} {platform.release()}", cwd=os.getcwd())

        # Load persistent memory (Global and Local)
        global_memory = self.memory.read_memory(scope="global")
        local_knowledge = self.memory.read_memory(scope="local")
        mission_content = self.mission.read_missions()

        full_instruction = f"{base_context}\n\n"

        # Project blueprint (spatial awareness)
        try:
            blueprint = self._get_project_blueprint()
            full_instruction += "## PROJECT STRUCTURE (auto-discovered)\n"
            full_instruction += f"{blueprint}\n\n"
        except Exception as e:
            _logger.warning("Failed to scan project structure: %s", e)

        if global_memory:
            full_instruction += "## GLOBAL PERSISTENT MEMORY (User Preferences)\n"
            full_instruction += f"{global_memory}\n\n"

        if local_knowledge:
            full_instruction += "## LOCAL PROJECT KNOWLEDGE (.askgem_knowledge.md)\n"
            full_instruction += f"{local_knowledge}\n\n"

        if mission_content:
            full_instruction += "## ACTIVE MISSIONS AND TASKS (heartbeat.md)\n"
            full_instruction += f"{mission_content}\n\n"

        full_instruction += (
            "CRITICAL INSTRUCTION: Use 'manage_memory' with scope='local' to save project patterns, "
            "and scope='global' for user preferences. Use 'manage_mission' to track progress."
        )

        return full_instruction
