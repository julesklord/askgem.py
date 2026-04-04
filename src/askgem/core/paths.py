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


def get_config_dir() -> Path:
    """Gets the base configuration directory for the application.

    Returns:
        Path: A Path object pointing to the ~/.askgem directory.
    """
    config_dir = Path.home() / ".askgem"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


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
<<<<<<< Updated upstream
=======
def get_memory_path() -> str:
    """Gets the path to the general persistent memory file.

    Returns:
        str: Absolute path to memory.md
    """
    return str(get_config_dir() / "memory.md")


def get_heartbeat_path() -> str:
    """Gets the path to the active mission/tasks file (Legacy).

    Returns:
        str: Absolute path to heartbeat.md
    """
    return str(get_config_dir() / "heartbeat.md")


def get_identity_path() -> str:
    """Gets the path to the agent's identity and persona file.

    Returns:
        str: Absolute path to identity.md
    """
    return str(get_config_dir() / "identity.md")


def get_tasks_path() -> str:
    """Gets the path to the active tasks and scheduled functions file.

    Returns:
        str: Absolute path to tasks.md
    """
    return str(get_config_dir() / "tasks.md")
>>>>>>> Stashed changes
