import asyncio
import pytest
from unittest.mock import AsyncMock, Mock

from mentask.core.process_tracker import ProcessTracker


@pytest.fixture
def process_tracker():
    tracker = ProcessTracker()
    tracker._active_processes.clear()
    return tracker


def test_singleton():
    tracker1 = ProcessTracker()
    tracker2 = ProcessTracker()
    assert tracker1 is tracker2


def test_register(process_tracker):
    mock_process = Mock(spec=asyncio.subprocess.Process)
    mock_process.pid = 1234
    process_tracker.register(mock_process)
    assert mock_process in process_tracker._active_processes


def test_unregister(process_tracker):
    mock_process = Mock(spec=asyncio.subprocess.Process)
    mock_process.pid = 1234
    process_tracker.register(mock_process)
    process_tracker.unregister(mock_process)
    assert mock_process not in process_tracker._active_processes


@pytest.mark.asyncio
async def test_kill_all_success(process_tracker):
    mock_process = AsyncMock(spec=asyncio.subprocess.Process)
    mock_process.returncode = None
    mock_process.pid = 1234

    process_tracker.register(mock_process)
    await process_tracker.kill_all()

    mock_process.kill.assert_called_once()
    mock_process.wait.assert_awaited_once()
    assert mock_process not in process_tracker._active_processes


@pytest.mark.asyncio
async def test_kill_all_already_finished(process_tracker):
    mock_process = AsyncMock(spec=asyncio.subprocess.Process)
    mock_process.returncode = 0
    mock_process.pid = 1234

    process_tracker.register(mock_process)
    await process_tracker.kill_all()

    mock_process.kill.assert_not_called()
    assert mock_process not in process_tracker._active_processes


@pytest.mark.asyncio
async def test_kill_all_timeout(process_tracker):
    mock_process = AsyncMock(spec=asyncio.subprocess.Process)
    mock_process.returncode = None
    mock_process.pid = 1234

    # Simulate wait() timing out
    mock_process.wait.side_effect = asyncio.TimeoutError()

    process_tracker.register(mock_process)
    await process_tracker.kill_all()

    mock_process.kill.assert_called_once()
    mock_process.wait.assert_awaited_once()
    assert mock_process not in process_tracker._active_processes


@pytest.mark.asyncio
async def test_kill_all_exception(process_tracker):
    mock_process = AsyncMock(spec=asyncio.subprocess.Process)
    mock_process.returncode = None
    mock_process.pid = 1234

    mock_process.kill.side_effect = Exception("Test Error")

    process_tracker.register(mock_process)
    await process_tracker.kill_all()

    mock_process.kill.assert_called_once()
    assert mock_process not in process_tracker._active_processes
