from unittest.mock import patch

import pytest

from mentask.tools.memory_tools import manage_memory, manage_mission


@pytest.fixture
def mock_memory_manager():
    with patch("mentask.tools.memory_tools._memory") as mock:
        yield mock


@pytest.fixture
def mock_mission_manager():
    with patch("mentask.tools.memory_tools._mission") as mock:
        yield mock


# --- manage_memory tests ---


def test_manage_memory_add_success(mock_memory_manager):
    mock_memory_manager.add_fact.return_value = True
    result = manage_memory(action="add", content="Test fact", category="Test Category")
    mock_memory_manager.add_fact.assert_called_once_with("Test fact", "Test Category")
    assert result == "Success: Fact remembered in 'Test Category'."


def test_manage_memory_add_missing_content(mock_memory_manager):
    result = manage_memory(action="add", content="")
    mock_memory_manager.add_fact.assert_not_called()
    assert result == "Error: content is required for 'add' action."


def test_manage_memory_add_failure(mock_memory_manager):
    mock_memory_manager.add_fact.return_value = False
    result = manage_memory(action="add", content="Test fact", category="Test Category")
    mock_memory_manager.add_fact.assert_called_once_with("Test fact", "Test Category")
    assert result == "Error: Failed to update memory."


def test_manage_memory_read(mock_memory_manager):
    mock_memory_manager.read_memory.return_value = "Memory content"
    result = manage_memory(action="read")
    mock_memory_manager.read_memory.assert_called_once()
    assert result == "Memory content"


def test_manage_memory_reset(mock_memory_manager):
    result = manage_memory(action="reset")
    mock_memory_manager.reset_memory.assert_called_once()
    assert result == "Success: Memory has been reset to default template."


def test_manage_memory_unknown_action(mock_memory_manager):
    result = manage_memory(action="unknown")
    assert result == "Error: Unknown action 'unknown'."


# --- manage_mission tests ---


def test_manage_mission_add_success(mock_mission_manager):
    mock_mission_manager.add_task.return_value = True
    result = manage_mission(action="add", task="New task")
    mock_mission_manager.add_task.assert_called_once_with("New task")
    assert result == "Success: Task 'New task' added to active missions."


def test_manage_mission_add_missing_task(mock_mission_manager):
    result = manage_mission(action="add", task="")
    mock_mission_manager.add_task.assert_not_called()
    assert result == "Error: task is required for 'add' action."


def test_manage_mission_add_failure(mock_mission_manager):
    mock_mission_manager.add_task.return_value = False
    result = manage_mission(action="add", task="New task")
    mock_mission_manager.add_task.assert_called_once_with("New task")
    assert result == "Error: Failed to update heartbeat."


def test_manage_mission_complete_success(mock_mission_manager):
    mock_mission_manager.complete_task.return_value = True
    result = manage_mission(action="complete", task="Existing task")
    mock_mission_manager.complete_task.assert_called_once_with("Existing task")
    assert result == "Success: Task matching 'Existing task' marked as completed."


def test_manage_mission_complete_missing_task(mock_mission_manager):
    result = manage_mission(action="complete", task="")
    mock_mission_manager.complete_task.assert_not_called()
    assert result == "Error: task is required for 'complete' action."


def test_manage_mission_complete_failure(mock_mission_manager):
    mock_mission_manager.complete_task.return_value = False
    result = manage_mission(action="complete", task="Non-existent task")
    mock_mission_manager.complete_task.assert_called_once_with("Non-existent task")
    assert result == "Error: Task 'Non-existent task' not found or already completed."


def test_manage_mission_read(mock_mission_manager):
    mock_mission_manager.read_missions.return_value = "Mission content"
    result = manage_mission(action="read")
    mock_mission_manager.read_missions.assert_called_once()
    assert result == "Mission content"


def test_manage_mission_unknown_action(mock_mission_manager):
    result = manage_mission(action="unknown")
    assert result == "Error: Unknown action 'unknown'."
