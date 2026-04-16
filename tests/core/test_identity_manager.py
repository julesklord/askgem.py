import os
from unittest.mock import patch

import pytest

from askgem.core.identity_manager import KnowledgeManager


class TestKnowledgeManager:
    @pytest.fixture
    def mock_paths(self, tmp_path):
        # Create standard, global, and local directories
        standard = tmp_path / "standard"
        global_dir = tmp_path / "global"
        local_dir = tmp_path / "local"

        standard.mkdir()
        global_dir.mkdir()
        local_dir.mkdir()

        with (
            patch("askgem.core.identity_manager.get_standard_knowledge_dir", return_value=standard),
            patch("askgem.core.identity_manager.get_global_config_dir", return_value=global_dir),
            patch("askgem.core.identity_manager.get_config_dir", return_value=local_dir),
        ):
            yield {
                "standard": standard,
                "global": global_dir,
                "local": local_dir,
            }

    def test_read_knowledge_hub_hierarchical(self, mock_paths):
        # Setup files at different levels
        with open(mock_paths["standard"] / "core.md", "w", encoding="utf-8") as f:
            f.write("Standard Wisdom")

        with open(mock_paths["global"] / "user.md", "w", encoding="utf-8") as f:
            f.write("Global Preferences")

        with open(mock_paths["local"] / "project.md", "w", encoding="utf-8") as f:
            f.write("Local Logic")

        manager = KnowledgeManager()
        result = manager.read_knowledge_hub()

        assert "STANDARDIZED CORE KNOWLEDGE" in result
        assert "Standard Wisdom" in result
        assert "GLOBAL PERSONAL KNOWLEDGE" in result
        assert "Global Preferences" in result
        assert "LOCAL PROJECT KNOWLEDGE" in result
        assert "Local Logic" in result

    def test_read_knowledge_hub_local_file_only(self, mock_paths):
        # Test the legacy/shortcut .askgem_knowledge.md in the current working directory
        manager = KnowledgeManager()

        # We patch Path.cwd() to point to our local mock dir
        with patch("pathlib.Path.cwd", return_value=mock_paths["local"]):
            # Create the special hidden file
            with open(mock_paths["local"] / ".askgem_knowledge.md", "w", encoding="utf-8") as f:
                f.write("Secret Project Knowledge")

            result = manager.read_knowledge_hub()

        assert "LOCAL PROJECT KNOWLEDGE" in result
        assert "Secret Project Knowledge" in result

    def test_read_knowledge_hub_empty(self, mock_paths):
        # Should return a fallback message if no files are found
        # We must isolate CWD to avoid finding the real .askgem_knowledge.md in project root
        with patch("pathlib.Path.cwd", return_value=mock_paths["local"]):
            manager = KnowledgeManager()
            result = manager.read_knowledge_hub()
            assert result == "No extended knowledge available."

    def test_read_identity_compatibility(self, mock_paths):
        # Ensure read_identity (legacy alias) still works
        manager = KnowledgeManager()
        with open(mock_paths["standard"] / "identity.md", "w", encoding="utf-8") as f:
            f.write("I am AskGem")

        assert "I am AskGem" in manager.read_identity()
