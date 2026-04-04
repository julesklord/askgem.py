import os
import pytest
from unittest.mock import patch, mock_open

from askgem.core.mission_manager import MissionManager, DEFAULT_HEARTBEAT_TEMPLATE

@pytest.fixture
def mock_heartbeat_path(tmp_path):
    """Fixture to mock get_heartbeat_path to point to a temporary file."""
    temp_file = tmp_path / "heartbeat.md"
    with patch('askgem.core.mission_manager.get_heartbeat_path', return_value=str(temp_file)):
        yield str(temp_file)

def test_init_creates_file(mock_heartbeat_path):
    """Test that MissionManager creates heartbeat.md if it doesn't exist."""
    assert not os.path.exists(mock_heartbeat_path)

    manager = MissionManager()

    assert os.path.exists(mock_heartbeat_path)
    with open(mock_heartbeat_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert content == DEFAULT_HEARTBEAT_TEMPLATE

def test_init_existing_file(mock_heartbeat_path):
    """Test that MissionManager does not overwrite existing heartbeat.md."""
    custom_content = "# Custom Mission"
    with open(mock_heartbeat_path, 'w', encoding='utf-8') as f:
        f.write(custom_content)

    manager = MissionManager()

    with open(mock_heartbeat_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert content == custom_content

def test_read_missions(mock_heartbeat_path):
    """Test reading missions returns file content."""
    custom_content = "# Active Missions\n- Mission 1"
    with open(mock_heartbeat_path, 'w', encoding='utf-8') as f:
        f.write(custom_content)

    manager = MissionManager()
    content = manager.read_missions()
    assert content == custom_content

def test_read_missions_exception(mock_heartbeat_path):
    """Test reading missions returns empty string on exception."""
    manager = MissionManager()

    # Force an exception by mocking open to raise an error
    with patch('builtins.open', side_effect=Exception("Read error")):
        content = manager.read_missions()

    assert content == ""

def test_add_task_existing_header(mock_heartbeat_path):
    """Test adding a task when '## Tasks' header exists."""
    initial_content = "# Missions\n## Tasks\n- [ ] Task 1"
    with open(mock_heartbeat_path, 'w', encoding='utf-8') as f:
        f.write(initial_content)

    manager = MissionManager()
    result = manager.add_task("Task 2")

    assert result is True
    with open(mock_heartbeat_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "- [ ] Task 2" in content
    # Order should be ## Tasks, then Task 2, then Task 1 (inserted at index + 1)
    lines = content.splitlines()
    tasks_index = lines.index("## Tasks")
    assert lines[tasks_index + 1] == "- [ ] Task 2"

def test_add_task_no_header(mock_heartbeat_path):
    """Test adding a task when '## Tasks' header does not exist."""
    initial_content = "# Missions"
    with open(mock_heartbeat_path, 'w', encoding='utf-8') as f:
        f.write(initial_content)

    manager = MissionManager()
    result = manager.add_task("New Task")

    assert result is True
    with open(mock_heartbeat_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "\n## Tasks" in content
    assert "- [ ] New Task" in content

def test_add_task_write_exception(mock_heartbeat_path):
    """Test adding a task returns False on write exception."""
    manager = MissionManager()

    # We want to allow reading the file to get content, but fail on writing
    # Mock 'builtins.open' conditionally based on mode
    original_open = open
    def mock_open_func(*args, **kwargs):
        if 'w' in (args[1] if len(args) > 1 else kwargs.get('mode', 'r')):
            raise Exception("Write error")
        return original_open(*args, **kwargs)

    with patch('builtins.open', side_effect=mock_open_func):
        result = manager.add_task("Failed Task")

    assert result is False

def test_complete_task_success(mock_heartbeat_path):
    """Test completing an existing task."""
    initial_content = "## Tasks\n- [ ] My Task\n- [ ] Other Task"
    with open(mock_heartbeat_path, 'w', encoding='utf-8') as f:
        f.write(initial_content)

    manager = MissionManager()
    result = manager.complete_task("my task")

    assert result is True
    with open(mock_heartbeat_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "- [x] My Task" in content
    assert "- [ ] Other Task" in content

def test_complete_task_not_found(mock_heartbeat_path):
    """Test completing a non-existent task returns False."""
    initial_content = "## Tasks\n- [ ] Existing Task"
    with open(mock_heartbeat_path, 'w', encoding='utf-8') as f:
        f.write(initial_content)

    manager = MissionManager()
    result = manager.complete_task("Non-existent Task")

    assert result is False
    with open(mock_heartbeat_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert content == initial_content

def test_complete_task_write_exception(mock_heartbeat_path):
    """Test completing a task returns False on write exception."""
    initial_content = "## Tasks\n- [ ] Task to Complete"
    with open(mock_heartbeat_path, 'w', encoding='utf-8') as f:
        f.write(initial_content)

    manager = MissionManager()

    original_open = open
    def mock_open_func(*args, **kwargs):
        if 'w' in (args[1] if len(args) > 1 else kwargs.get('mode', 'r')):
            raise Exception("Write error")
        return original_open(*args, **kwargs)

    with patch('builtins.open', side_effect=mock_open_func):
        result = manager.complete_task("Task to Complete")

    assert result is False
