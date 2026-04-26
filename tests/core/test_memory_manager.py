import os
from unittest.mock import patch

import pytest

from mentask.core.memory_manager import MemoryManager


@pytest.fixture
def mock_memory_paths(tmp_path):
    path_global = tmp_path / "global_memory.md"
    path_local = tmp_path / "local_memory.md"

    with (
        patch("mentask.core.memory_manager.get_memory_path", return_value=str(path_global)),
        patch("mentask.core.memory_manager.get_local_knowledge_path", return_value=str(path_local)),
    ):
        yield {"global": path_global, "local": path_local}


class TestMemoryManager:
    def test_init_creates_global_memory(self, mock_memory_paths):
        assert not os.path.exists(mock_memory_paths["global"])
        MemoryManager()
        assert os.path.exists(mock_memory_paths["global"])

    def test_read_memory_all(self, mock_memory_paths):
        manager = MemoryManager()
        # Setup files
        with open(mock_memory_paths["global"], "w", encoding="utf-8") as f:
            f.write("Global Preference")
        with open(mock_memory_paths["local"], "w", encoding="utf-8") as f:
            f.write("Local Pattern")

        result = manager.read_memory(scope="all")
        assert "GLOBAL PERSISTENT MEMORY" in result
        assert "Global Preference" in result
        assert "LOCAL PROJECT KNOWLEDGE" in result
        assert "Local Pattern" in result

    def test_read_memory_specific_scope(self, mock_memory_paths):
        manager = MemoryManager()
        with open(mock_memory_paths["global"], "w", encoding="utf-8") as f:
            f.write("Only Global")

        assert "Only Global" in manager.read_memory(scope="global")
        assert "Only Global" not in manager.read_memory(scope="local")

    def test_add_fact_local_by_default(self, mock_memory_paths):
        manager = MemoryManager()
        success = manager.add_fact("New local fact", category="Lessons Learned & Facts")
        assert success is True

        # Check local file
        with open(mock_memory_paths["local"], encoding="utf-8") as f:
            content = f.read()
        assert "New local fact" in content

    def test_add_fact_global(self, mock_memory_paths):
        manager = MemoryManager()
        success = manager.add_fact("User loves coffee", scope="global", category="User Profile & Preferences")
        assert success is True

        with open(mock_memory_paths["global"], encoding="utf-8") as f:
            content = f.read()
        assert "User loves coffee" in content

    def test_reset_memory_local(self, mock_memory_paths):
        manager = MemoryManager()
        manager.add_fact("To be deleted", scope="local")
        assert os.path.exists(mock_memory_paths["local"])

        manager.reset_memory(scope="local")
        assert not os.path.exists(mock_memory_paths["local"])

    def test_reset_memory_global_recreates(self, mock_memory_paths):
        manager = MemoryManager()
        manager.reset_memory(scope="global")
        # For global, reset_memory recreates from template
        assert os.path.exists(mock_memory_paths["global"])
