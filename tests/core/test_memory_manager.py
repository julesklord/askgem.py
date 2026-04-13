import os
from unittest.mock import patch

import pytest

from askgem.core.memory_manager import MemoryManager


@pytest.fixture
def mock_memory_path(tmp_path):
    memory_file = str(tmp_path / "memory.md")
    with patch("askgem.core.memory_manager.get_memory_path") as mock_path:
        mock_path.return_value = memory_file
        yield memory_file


def test_init_creates_memory(mock_memory_path):
    assert not os.path.exists(mock_memory_path)

    MemoryManager()

    assert os.path.exists(mock_memory_path)
    with open(mock_memory_path, encoding="utf-8") as f:
        content = f.read()

    assert "# AskGem Persistent Memory" in content


def test_read_memory(mock_memory_path):
    manager = MemoryManager()

    # Overwrite the file manually to test read_memory
    test_content = "Some test content"
    with open(mock_memory_path, "w", encoding="utf-8") as f:
        f.write(test_content)

    result = manager.read_memory()
    assert result == test_content


def test_read_memory_handles_missing_file(mock_memory_path):
    manager = MemoryManager()

    # Delete the file manually
    os.remove(mock_memory_path)

    result = manager.read_memory()
    assert result == ""


def test_add_fact_existing_category(mock_memory_path):
    manager = MemoryManager()

    # By default, template has "## Lessons Learned & Facts"
    success = manager.add_fact("Water is wet.", "Lessons Learned & Facts")
    assert success is True

    content = manager.read_memory()
    assert "- Water is wet." in content

    lines = content.splitlines()
    category_index = lines.index("## Lessons Learned & Facts")
    assert lines[category_index + 1] == "- Water is wet."


def test_add_fact_new_category(mock_memory_path):
    manager = MemoryManager()

    success = manager.add_fact("Python is fun.", "New Category")
    assert success is True

    content = manager.read_memory()
    assert "## New Category" in content
    assert "- Python is fun." in content

    lines = content.splitlines()
    # Find exact indices
    category_index = -1
    for i, line in enumerate(lines):
        if line.strip() == "## New Category":
            category_index = i
            break

    assert category_index != -1
    assert lines[category_index + 1] == "- Python is fun."


def test_add_fact_file_error(mock_memory_path):
    manager = MemoryManager()

    # Try mocking builtins.open only when called from memory_manager.py's add_fact inside try-except
    # Instead of builtins.open, we can make the file directory read-only or patch the file object
    # The safest way is to patch builtins.open, but we should make sure it only fails for 'w'

    original_open = open
    def mock_open(*args, **kwargs):
        if len(args) > 1 and args[1] == 'w':
            raise OSError("Mocked error")
        return original_open(*args, **kwargs)

    with patch("builtins.open", side_effect=mock_open):
        success = manager.add_fact("This won't be saved.", "Lessons Learned & Facts")

    assert success is False


def test_reset_memory(mock_memory_path):
    manager = MemoryManager()

    # Modify the content
    manager.add_fact("Temporary fact", "Lessons Learned & Facts")
    content_before = manager.read_memory()
    assert "Temporary fact" in content_before

    manager.reset_memory()

    content_after = manager.read_memory()
    assert "Temporary fact" not in content_after
    assert "# AskGem Persistent Memory" in content_after
