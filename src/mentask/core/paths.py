"""
Path resolution utilities for mentask.

This module provides centralized access to application data directories (e.g., ~/.mentask),
ensuring consistent paths across different OS environments and avoiding circular
imports between core logic and CLI managers.

Key directories handled:
- Config: ~/.mentask (API keys, settings.json)
- Sessions: ~/.mentask/sessions/ (Chat session persistence)

This module does NOT handle the creation or parsing of files within these directories.
"""

import subprocess
import sys
from contextlib import suppress
from pathlib import Path

from mentask.core.constants import PERSISTENT_MEMORY_FILENAME

# ─────────────────────────────────────────────────────────────────────────────
# Windows hidden-attribute helper
# ─────────────────────────────────────────────────────────────────────────────


def _hide_on_windows(path: Path) -> None:
    """Mark *path* as hidden on Windows (no-op on other platforms)."""
    if sys.platform == "win32" and path.is_dir():
        with suppress(Exception):
            subprocess.run(
                ["attrib", "+h", str(path)],
                check=False,
                capture_output=True,
                timeout=5,
            )


def ensure_dir(path: Path) -> Path:
    """Create a directory (and parents) and mark it hidden on Windows."""
    path.mkdir(parents=True, exist_ok=True)
    _hide_on_windows(path)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Standard knowledge (bundled)
# ─────────────────────────────────────────────────────────────────────────────


def get_standard_knowledge_dir() -> Path:
    """Returns the internal package directory containing standard knowledge modules."""
    return Path(__file__).parent.parent / "agent" / "standard"


# ─────────────────────────────────────────────────────────────────────────────
# Config directories
# ─────────────────────────────────────────────────────────────────────────────


def get_global_config_dir() -> Path:
    """Always returns the global ~/.mentask directory."""
    return ensure_dir(Path.home() / ".mentask")


def get_config_dir() -> Path:
    """Gets the active configuration directory.
    Prioritizes a local .mentask/ directory in the CWD if it exists.
    Otherwise, falls back to the global ~/.mentask directory.
    """
    local_dir = Path.cwd() / ".mentask"
    if local_dir.is_dir():
        return local_dir
    return get_global_config_dir()


def get_config_path(filename: str) -> str:
    """Gets the absolute path for a specific configuration file."""
    return str(get_config_dir() / filename)


# ─────────────────────────────────────────────────────────────────────────────
# Subdirectories (auto-created on first access)
# ─────────────────────────────────────────────────────────────────────────────


def get_history_dir() -> str:
    """Gets the directory used for storing chat session histories."""
    return str(ensure_dir(get_config_dir() / "sessions"))


def get_backups_dir() -> Path:
    """Gets the directory used for storing file backups."""
    return ensure_dir(get_config_dir() / "backups")


def get_plugins_dir() -> Path:
    """Gets the directory used for storing dynamic agent plugins."""
    return ensure_dir(get_config_dir() / "plugins")


# ─────────────────────────────────────────────────────────────────────────────
# Well-known file paths
# ─────────────────────────────────────────────────────────────────────────────


def get_global_memory_path() -> str:
    """Gets the path to the global user preferences memory file (~/.mentask/memory.md)."""
    return str(get_global_config_dir() / PERSISTENT_MEMORY_FILENAME)


def get_memory_path() -> str:
    """Gets the path to the memory file in the active configuration directory."""
    return str(get_config_dir() / PERSISTENT_MEMORY_FILENAME)


def get_local_knowledge_path() -> str:
    """Gets the path to the project-specific knowledge file (Local)."""
    return str(Path.cwd() / ".mentask_knowledge.md")


def get_heartbeat_path() -> str:
    """Gets the path to the active mission/tasks file."""
    return str(get_config_dir() / "heartbeat.md")


def get_tasks_path() -> str:
    """Gets the path to the tasks and functions file."""
    return str(get_config_dir() / "tasks.md")
