import json
import os
import uuid
from unittest.mock import MagicMock, patch

import pytest

from mentask.agent.schema import Message, Role
from mentask.core.history_manager import HistoryManager

# Patch the console so no Rich output is emitted during tests
_mock_console = MagicMock()


class TestHistoryManager:
    @pytest.fixture
    def manager(self, tmp_path):
        # Patching the actual source in core.paths
        with patch("mentask.core.paths.get_history_dir") as mock_dir:
            mock_dir.return_value = str(tmp_path)
            yield HistoryManager(_mock_console)

    def test_init(self, manager, tmp_path):
        assert manager.history_dir == str(tmp_path)
        assert len(manager.current_session_id) in (8, 36)

    @pytest.mark.asyncio
    async def test_save_session_empty(self, manager, tmp_path):
        await manager.save_session([])
        files = os.listdir(tmp_path)
        # Should create an empty list in the file?
        # Looking at save_session: json.dump([], f, ...)
        assert len(files) == 1
        filepath = os.path.join(tmp_path, files[0])
        with open(filepath) as f:
            assert json.load(f) == []

    @pytest.mark.asyncio
    async def test_save_session(self, manager, tmp_path):
        msg = Message(role=Role.USER, content="hello")
        await manager.save_session([msg])

        filepath = os.path.join(tmp_path, f"{manager.current_session_id}.json")
        assert os.path.exists(filepath)

        with open(filepath) as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["content"] == "hello"

    @pytest.mark.asyncio
    async def test_load_session_basic(self, manager, tmp_path):
        session_id = "test_session"
        filepath = os.path.join(tmp_path, f"{session_id}.json")
        data = [{"role": "user", "content": "hello", "uuid": str(uuid.uuid4())}]
        with open(filepath, "w") as f:
            json.dump(data, f)

        loaded = await manager.load_session(session_id)
        assert len(loaded) == 1
        assert loaded[0].role == Role.USER
        assert loaded[0].content == "hello"

    def test_list_sessions(self, manager, tmp_path):
        # HistoryManager uses sorted(p.glob("*.json"), key=lambda f: f.stat().st_mtime)
        # We need to make sure they have different mtimes if we want a specific order,
        # but just testing count is enough here.
        (tmp_path / "session1.json").write_text("[]")
        (tmp_path / "session2.json").write_text("[]")

        sessions = manager.list_sessions()
        assert len(sessions) == 2
        assert "session1" in sessions
        assert "session2" in sessions

    def test_delete_session(self, manager, tmp_path):
        session_id = "test_session"
        filepath = tmp_path / f"{session_id}.json"
        filepath.write_text("[]")

        assert manager.delete_session(session_id) is True
        assert not filepath.exists()

    @pytest.mark.asyncio
    async def test_load_session_path_traversal(self, manager):
        # load_session uses .resolve() to check for path traversal
        assert await manager.load_session("../../../etc/passwd") is None

    def test_cleanup_old_sessions(self, manager, tmp_path):
        import time
        # Create session files with different timestamps
        f1 = tmp_path / "session_old.json"
        f1.write_text("[]")
        # Back-date modification time by 32 days
        os.utime(f1, (time.time() - 32 * 86400, time.time() - 32 * 86400))

        f2 = tmp_path / "session_new.json"
        f2.write_text("[]")

        # Run cleanup
        manager.cleanup_old_sessions(max_age_days=30, max_count=5)

        # old session should be deleted, new one should remain
        assert not f1.exists()
        assert f2.exists()

    def test_cleanup_max_count_sessions(self, manager, tmp_path):
        import time
        # Create multiple session files
        for i in range(10):
            f = tmp_path / f"session_{i}.json"
            f.write_text("[]")
            # Set progressive timestamps so we can order them
            mtime = time.time() - (10 - i) * 60
            os.utime(f, (mtime, mtime))

        # Run cleanup with max_count limit of 5
        manager.cleanup_old_sessions(max_age_days=30, max_count=5)

        # Only the 5 newest ones should remain (sessions 5, 6, 7, 8, 9)
        for i in range(5):
            assert not (tmp_path / f"session_{i}.json").exists()
        for i in range(5, 10):
            assert (tmp_path / f"session_{i}.json").exists()

    def test_cleanup_old_backups(self, manager, tmp_path):
        import time
        # Create a mock backups directory
        backups_dir = tmp_path / "backups"
        backups_dir.mkdir()

        # Create old and new backup directories
        old_backup = backups_dir / "20260601_120000"
        old_backup.mkdir()
        # Back-date folder modification time by 10 days
        os.utime(old_backup, (time.time() - 10 * 86400, time.time() - 10 * 86400))

        new_backup = backups_dir / "20260619_120000"
        new_backup.mkdir()

        with patch("mentask.core.paths.get_backups_dir", return_value=backups_dir):
            manager.cleanup_old_backups(max_age_days=7)

        # Old backup folder should be deleted, new folder should remain
        assert not old_backup.exists()
        assert new_backup.exists()


def test_json_serializable():
    from mentask.core.history_manager import json_serializable

    # Test object with to_dict
    class ObjWithToDict:
        def to_dict(self):
            return {"a": 1}

    assert json_serializable(ObjWithToDict()) == {"a": 1}

    # Test object with __dict__
    class ObjWithDict:
        def __init__(self):
            self.b = 2

    assert json_serializable(ObjWithDict()) == {"b": 2}

    # Test object that can be cast to dict
    assert json_serializable([("c", 3)]) == {"c": 3}

    # Test object that fails dict casting and falls back to __raw__
    assert json_serializable(42) == {"__raw__": "42"}

    # Test uncastable object (not a tuple list)
    class Uncastable:
        def __repr__(self):
            return "<Uncastable>"

        # Hide __dict__ just in case
        @property
        def __dict__(self):
            raise AttributeError

    assert json_serializable(Uncastable()) == {"__raw__": "<Uncastable>"}
