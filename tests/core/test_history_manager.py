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
        assert len(manager.current_session_id) == 8

    def test_save_session_empty(self, manager, tmp_path):
        manager.save_session([])
        files = os.listdir(tmp_path)
        # Should create an empty list in the file?
        # Looking at save_session: json.dump([], f, ...)
        assert len(files) == 1
        filepath = os.path.join(tmp_path, files[0])
        with open(filepath) as f:
            assert json.load(f) == []

    def test_save_session(self, manager, tmp_path):
        msg = Message(role=Role.USER, content="hello")
        manager.save_session([msg])

        filepath = os.path.join(tmp_path, f"{manager.current_session_id}.json")
        assert os.path.exists(filepath)

        with open(filepath) as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["content"] == "hello"

    def test_load_session_basic(self, manager, tmp_path):
        session_id = "test_session"
        filepath = os.path.join(tmp_path, f"{session_id}.json")
        data = [{"role": "user", "content": "hello", "uuid": str(uuid.uuid4())}]
        with open(filepath, "w") as f:
            json.dump(data, f)

        loaded = manager.load_session(session_id)
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

    def test_load_session_path_traversal(self, manager):
        # load_session uses .resolve() to check for path traversal
        assert manager.load_session("../../../etc/passwd") is None
