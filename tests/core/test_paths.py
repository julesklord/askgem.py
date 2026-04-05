import os
from pathlib import Path
from unittest.mock import patch

import pytest

from askgem.core.paths import (
    get_config_dir,
    get_config_path,
    get_history_dir,
    get_memory_path,
    get_heartbeat_path,
)


@pytest.fixture
def mock_home(tmp_path):
    with patch("pathlib.Path.home", return_value=tmp_path):
        yield tmp_path


def test_get_config_dir(mock_home):
    config_dir = get_config_dir()

    # Check that it returns a Path object
    assert isinstance(config_dir, Path)

    # Check that it returns the correct path
    expected_path = mock_home / ".askgem"
    assert config_dir == expected_path


def test_get_config_path(mock_home):
    filename = "test_config.json"
    config_path = get_config_path(filename)

    # Check that it returns a string
    assert isinstance(config_path, str)

    # Check that the path is correct
    expected_path = str(mock_home / ".askgem" / filename)
    assert config_path == expected_path


def test_get_history_dir(mock_home):
    history_dir = get_history_dir()

    # Check that it returns a string
    assert isinstance(history_dir, str)

    # Check that the path is correct
    expected_path = str(mock_home / ".askgem" / "history")
    assert history_dir == expected_path


def test_get_memory_path(mock_home):
    memory_path = get_memory_path()

    # Check that it returns a string
    assert isinstance(memory_path, str)

    # Check that the path is correct
    expected_path = str(mock_home / ".askgem" / "memory.md")
    assert memory_path == expected_path


def test_get_heartbeat_path(mock_home):
    heartbeat_path = get_heartbeat_path()

    # Check that it returns a string
    assert isinstance(heartbeat_path, str)

    # Check that the path is correct
    expected_path = str(mock_home / ".askgem" / "heartbeat.md")
    assert heartbeat_path == expected_path
