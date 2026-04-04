import os
import pytest
from unittest.mock import patch

from askgem.core.tasks_manager import TasksManager, DEFAULT_TASKS_TEMPLATE

@pytest.fixture
def mock_tasks_path(tmp_path):
    """Fixture to mock get_tasks_path to point to a temporary file."""
    temp_file = tmp_path / "tasks.md"
    with patch('askgem.core.tasks_manager.get_tasks_path', return_value=str(temp_file)):
        yield str(temp_file)

def test_init_creates_file(mock_tasks_path):
    """Test that TasksManager creates tasks.md if it doesn't exist."""
    assert not os.path.exists(mock_tasks_path)

    manager = TasksManager()

    assert os.path.exists(mock_tasks_path)
    with open(mock_tasks_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert content == DEFAULT_TASKS_TEMPLATE

def test_init_existing_file(mock_tasks_path):
    """Test that TasksManager does not overwrite existing tasks.md."""
    custom_content = "# Custom Tasks"
    with open(mock_tasks_path, 'w', encoding='utf-8') as f:
        f.write(custom_content)

    manager = TasksManager()

    with open(mock_tasks_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert content == custom_content

def test_read_tasks(mock_tasks_path):
    """Test reading tasks returns file content."""
    custom_content = "# Active Tasks\n- Task 1"
    with open(mock_tasks_path, 'w', encoding='utf-8') as f:
        f.write(custom_content)

    manager = TasksManager()
    content = manager.read_tasks()
    assert content == custom_content

def test_read_tasks_exception(mock_tasks_path):
    """Test reading tasks returns empty string on OSError."""
    manager = TasksManager()

    # Force an exception by mocking open to raise an error
    with patch('builtins.open', side_effect=OSError("Read error")):
        content = manager.read_tasks()

    assert content == ""

def test_add_task_existing_header(mock_tasks_path):
    """Test adding a task when '## Tasks' header exists."""
    initial_content = "# Tasks\n## Tasks\n- [ ] Task 1"
    with open(mock_tasks_path, 'w', encoding='utf-8') as f:
        f.write(initial_content)

    manager = TasksManager()
    result = manager.add_task("Task 2")

    assert result is True
    with open(mock_tasks_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "- [ ] Task 2" in content
    # Order should be ## Tasks, then Task 2, then Task 1 (inserted at index + 1)
    lines = content.splitlines()
    tasks_index = lines.index("## Tasks")
    assert lines[tasks_index + 1] == "- [ ] Task 2"

def test_add_task_no_header(mock_tasks_path):
    """Test adding a task when '## Tasks' header does not exist."""
    initial_content = "# Some Header"
    with open(mock_tasks_path, 'w', encoding='utf-8') as f:
        f.write(initial_content)

    manager = TasksManager()
    result = manager.add_task("New Task")

    assert result is True
    with open(mock_tasks_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "## Tasks" in content
    assert "- [ ] New Task" in content

def test_add_task_write_exception(mock_tasks_path):
    """Test adding a task returns False on write exception."""
    manager = TasksManager()

    # We want to allow reading the file to get content, but fail on writing
    # Mock 'builtins.open' conditionally based on mode
    original_open = open
    def mock_open_func(*args, **kwargs):
        if 'w' in (args[1] if len(args) > 1 else kwargs.get('mode', 'r')):
            raise OSError("Write error")
        return original_open(*args, **kwargs)

    with patch('builtins.open', side_effect=mock_open_func):
        result = manager.add_task("Failed Task")

    assert result is False

def test_complete_task_success(mock_tasks_path):
    """Test completing an existing task."""
    initial_content = "## Tasks\n- [ ] My Task\n- [ ] Other Task"
    with open(mock_tasks_path, 'w', encoding='utf-8') as f:
        f.write(initial_content)

    manager = TasksManager()
    result = manager.complete_task("my task")

    assert result is True
    with open(mock_tasks_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "- [x] My Task" in content
    assert "- [ ] Other Task" in content

def test_complete_task_not_found(mock_tasks_path):
    """Test completing a non-existent task returns False."""
    initial_content = "## Tasks\n- [ ] Existing Task"
    with open(mock_tasks_path, 'w', encoding='utf-8') as f:
        f.write(initial_content)

    manager = TasksManager()
    result = manager.complete_task("Non-existent Task")

    assert result is False
    with open(mock_tasks_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert content == initial_content

def test_complete_task_write_exception(mock_tasks_path):
    """Test completing a task returns False on write exception."""
    initial_content = "## Tasks\n- [ ] Task to Complete"
    with open(mock_tasks_path, 'w', encoding='utf-8') as f:
        f.write(initial_content)

    manager = TasksManager()

    original_open = open
    def mock_open_func(*args, **kwargs):
        if 'w' in (args[1] if len(args) > 1 else kwargs.get('mode', 'r')):
            raise OSError("Write error")
        return original_open(*args, **kwargs)

    with patch('builtins.open', side_effect=mock_open_func):
        result = manager.complete_task("Task to Complete")

    assert result is False

def test_update_tasks_success(mock_tasks_path):
    """Test updating all tasks."""
    manager = TasksManager()
    new_content = "# All New Tasks\n- One\n- Two"
    result = manager.update_tasks(new_content)

    assert result is True
    with open(mock_tasks_path, 'r', encoding='utf-8') as f:
        assert f.read() == new_content

def test_update_tasks_exception(mock_tasks_path):
    """Test updating all tasks returns False on OSError."""
    manager = TasksManager()
    new_content = "# Fails"

    with patch('builtins.open', side_effect=OSError("Write error")):
        result = manager.update_tasks(new_content)

    assert result is False
