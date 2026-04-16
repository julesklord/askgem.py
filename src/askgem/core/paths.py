"""
Path resolution utilities for askgem.

This module provides centralized access to application data directories (e.g., ~/.askgem),
ensuring consistent paths across different OS environments and avoiding circular
imports between core logic and CLI managers.

Key directories handled:
- Config: ~/.askgem (API keys, settings.json)
- History: ~/.askgem/history/ (Chat session persistence)

This module does NOT handle the creation or parsing of files within these directories.
"""

from pathlib import Path


def get_global_config_dir() -> Path:
    """Always returns the global ~/.askgem directory."""
    config_dir = Path.home() / ".askgem"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_dir() -> Path:
    """Gets the active configuration directory.
    Prioritizes a local .askgem/ directory in the CWD if it exists.
    Otherwise, falls back to the global ~/.askgem directory.

    Returns:
        Path: A Path object pointing to the active .askgem directory.
    """
    local_dir = Path.cwd() / ".askgem"
    if local_dir.is_dir():
        return local_dir

    return get_global_config_dir()


def get_config_path(filename: str) -> str:
    """Gets the absolute path for a specific configuration file.

    Args:
        filename (str): The name of the file within the configuration directory.

    Returns:
        str: The absolute path to the configuration file.
    """
    return str(get_config_dir() / filename)


def get_history_dir() -> str:
    """Gets the directory used for storing chat session histories.

    Returns:
        str: The absolute path to the history directory.
    """
    history_dir = get_config_dir() / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    return str(history_dir)
def get_memory_path() -> str:
    """Gets the path to the general persistent memory file (Global)."""
    return str(get_config_dir() / "memory.md")


def get_local_knowledge_path() -> str:
    """Gets the path to the project-specific knowledge file (Local)."""
    from pathlib import Path
    return str(Path.cwd() / ".askgem_knowledge.md")


def get_heartbeat_path() -> str:
    """Gets the path to the active mission/tasks file.

    Returns:
        str: Absolute path to heartbeat.md
    """
    return str(get_config_dir() / "heartbeat.md")


def get_tasks_path() -> str:
    """Gets the path to the tasks and functions file.

    Returns:
        str: Absolute path to tasks.md
    """
    return str(get_config_dir() / "tasks.md")


def get_backups_dir() -> Path:
    """Gets the directory used for storing file backups.

    Returns:
        Path: A Path object pointing to the ~/.askgem/backups directory.
    """
    backups_dir = get_config_dir() / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    return backups_dir
