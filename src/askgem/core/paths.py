"""
Path resolution utilities for askgem.

This module provides centralized access to application data directories,
ensuring consistent paths and avoiding circular imports between managers.

This module does NOT handle the creation or parsing of files within these directories.
"""

from pathlib import Path


def get_config_dir() -> Path:
    """Gets the base configuration directory for the application.

    Returns:
        Path: A Path object pointing to ~/.askgem.
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
