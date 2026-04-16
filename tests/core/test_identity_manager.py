import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from askgem.core.identity_manager import KnowledgeManager


@pytest.fixture
def mock_dirs(tmp_path):
    standard_dir = tmp_path / "standard"
    global_dir = tmp_path / "global"
    active_dir = tmp_path / "active"

    standard_dir.mkdir()
    global_dir.mkdir()
    active_dir.mkdir()

    with patch("askgem.core.identity_manager.get_standard_knowledge_dir", return_value=standard_dir), \
         patch("askgem.core.identity_manager.get_global_config_dir", return_value=global_dir), \
         patch("askgem.core.identity_manager.get_config_dir", return_value=active_dir):
        yield standard_dir, global_dir, active_dir


def test_read_knowledge_hub_empty(mock_dirs):
    manager = KnowledgeManager()
    with patch("pathlib.Path.cwd", return_value=mock_dirs[2]):
        result = manager.read_knowledge_hub()
    assert result == "No extended knowledge available."


def test_read_knowledge_hub_with_files(mock_dirs):
    standard_dir, global_dir, active_dir = mock_dirs

    (standard_dir / "std.md").write_text("Standard info", encoding="utf-8")
    (global_dir / "glob.md").write_text("Global info", encoding="utf-8")
    (active_dir / "act.md").write_text("Active info", encoding="utf-8")

    manager = KnowledgeManager()

    with patch("pathlib.Path.cwd", return_value=active_dir):
        result = manager.read_knowledge_hub()

    assert "STANDARDIZED CORE KNOWLEDGE" in result
    assert "Standard info" in result
    assert "GLOBAL PERSONAL KNOWLEDGE" in result
    assert "Global info" in result
    assert "LOCAL PROJECT KNOWLEDGE" in result
    assert "Active info" in result


def test_read_identity_legacy_wrapper(mock_dirs):
    standard_dir, global_dir, active_dir = mock_dirs
    (standard_dir / "std.md").write_text("Standard info", encoding="utf-8")

    manager = KnowledgeManager()
    with patch("pathlib.Path.cwd", return_value=active_dir):
        result = manager.read_identity()

    assert "STANDARDIZED CORE KNOWLEDGE" in result
    assert "Standard info" in result
