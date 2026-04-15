import json
import os
from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from askgem.core.history_manager import HistoryManager, _safe_dict_cast

# Patch the console so no Rich output is emitted during tests
_mock_console = MagicMock()


class TestSafeDictCast:
    def test_safe_dict_cast_none(self):
        assert _safe_dict_cast(None) == {}

    def test_safe_dict_cast_dict(self):
        d = {"a": 1, "b": 2}
        assert _safe_dict_cast(d) == d

    def test_safe_dict_cast_items(self):
        class DummyWithItems:
            def items(self):
                return [("a", 1), ("b", 2)]

        assert _safe_dict_cast(DummyWithItems()) == {"a": 1, "b": 2}

    def test_safe_dict_cast_iterable(self):
        assert _safe_dict_cast([("a", 1), ("b", 2)]) == {"a": 1, "b": 2}

    def test_safe_dict_cast_fallback(self):
        assert _safe_dict_cast(123) == {"__raw__": "123"}


class TestHistoryManager:
    @pytest.fixture
    def manager(self, tmp_path):
        with patch("askgem.core.history_manager.get_history_dir") as mock_dir:
            mock_dir.return_value = str(tmp_path)
            yield HistoryManager(_mock_console)

    def test_init(self, manager, tmp_path):
        assert manager.history_dir == str(tmp_path)
        assert isinstance(manager.current_session_id, str)

    def test_content_to_dict_text(self, manager):
        content = types.Content(role="user", parts=[types.Part.from_text(text="hello")])
        result = manager._content_to_dict(content)
        assert result == {"role": "user", "parts": [{"text": "hello"}]}

    def test_content_to_dict_function_call(self, manager):
        content = types.Content(
            role="model", parts=[types.Part.from_function_call(name="my_func", args={"arg1": "val1"})]
        )
        result = manager._content_to_dict(content)
        assert result == {"role": "model", "parts": [{"function_call": {"name": "my_func", "args": {"arg1": "val1"}}}]}

    def test_content_to_dict_function_response(self, manager):
        content = types.Content(
            role="user", parts=[types.Part.from_function_response(name="my_func", response={"res1": "val1"})]
        )
        result = manager._content_to_dict(content)
        assert result == {
            "role": "user",
            "parts": [{"function_response": {"name": "my_func", "response": {"res1": "val1"}}}],
        }

    def test_dict_to_content_text(self, manager):
        data = {"role": "user", "parts": [{"text": "hello"}]}
        content = manager._dict_to_content(data)
        assert content.role == "user"
        assert len(content.parts) == 1
        assert content.parts[0].text == "hello"

    def test_dict_to_content_function_call(self, manager):
        data = {"role": "model", "parts": [{"function_call": {"name": "my_func", "args": {"arg1": "val1"}}}]}
        content = manager._dict_to_content(data)
        assert content.role == "model"
        assert len(content.parts) == 1
        assert content.parts[0].function_call.name == "my_func"
        # args might be generic struct, check value inside
        assert "arg1" in content.parts[0].function_call.args

    def test_dict_to_content_function_response(self, manager):
        data = {"role": "user", "parts": [{"function_response": {"name": "my_func", "response": {"res1": "val1"}}}]}
        content = manager._dict_to_content(data)
        assert content.role == "user"
        assert len(content.parts) == 1
        assert content.parts[0].function_response.name == "my_func"
        assert "res1" in content.parts[0].function_response.response

    def test_dict_to_content_empty_parts(self, manager):
        data = {"role": "user", "parts": []}
        content = manager._dict_to_content(data)
        assert content is None

    def test_dict_to_content_invalid_part(self, manager):
        # A part with no recognized key should be ignored, resulting in empty parts
        data = {"role": "user", "parts": [{"unknown": "data"}]}
        content = manager._dict_to_content(data)
        assert content is None

    def test_save_session_empty(self, manager, tmp_path):
        manager.save_session([])
        files = os.listdir(tmp_path)
        assert len(files) == 0

    def test_save_session(self, manager, tmp_path):
        content = types.Content(role="user", parts=[types.Part.from_text(text="hello")])
        manager.save_session([content])

        filepath = os.path.join(tmp_path, f"{manager.current_session_id}.json")
        assert os.path.exists(filepath)

        with open(filepath) as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0] == {"role": "user", "parts": [{"text": "hello"}]}

    def test_load_session_not_exists(self, manager):
        assert manager.load_session("nonexistent") is None

    def test_load_session_basic(self, manager, tmp_path):
        session_id = "test_session"
        filepath = os.path.join(tmp_path, f"{session_id}.json")
        data = [{"role": "user", "parts": [{"text": "hello"}]}]
        with open(filepath, "w") as f:
            json.dump(data, f)

        loaded = manager.load_session(session_id)
        assert len(loaded) == 1
        assert loaded[0].role == "user"
        assert loaded[0].parts[0].text == "hello"

    def test_load_session_context_window(self, manager, tmp_path):
        session_id = "test_session"
        filepath = os.path.join(tmp_path, f"{session_id}.json")

        # Create 25 messages, alternating user/model
        data = []
        for i in range(25):
            role = "user" if i % 2 == 0 else "model"
            data.append({"role": role, "parts": [{"text": f"msg {i}"}]})

        with open(filepath, "w") as f:
            json.dump(data, f)

        with patch("askgem.core.history_manager.MAX_CONTEXT_WINDOW", 20):
            loaded = manager.load_session(session_id)

        # Should keep the last 20 messages, but might drop 1 more if it doesn't start with user
        # Since we have 25, the last 20 starts at index 5. Index 5 is odd (model), so it drops one
        # to start at index 6 (user), resulting in 19 messages.
        assert loaded[0].role == "user"
        assert len(loaded) <= 20

    def test_load_session_char_limit(self, manager, tmp_path):
        session_id = "test_session"
        filepath = os.path.join(tmp_path, f"{session_id}.json")

        data = [
            {"role": "user", "parts": [{"text": "x" * 1000}]},
            {"role": "model", "parts": [{"text": "y" * 1000}]},
            {"role": "user", "parts": [{"text": "z" * 1000}]},
        ]

        with open(filepath, "w") as f:
            json.dump(data, f)

        # Set limit to 2500 chars, which means the 3 messages (3000 chars) won't fit
        with patch("askgem.core.history_manager.MAX_HISTORY_CHARS", 2500):
            loaded = manager.load_session(session_id)

        # Should drop the first message, so the new first is model. Then it will drop the model
        # message to ensure it starts with "user". So it should only have the last "user" message.
        assert len(loaded) == 1
        assert loaded[0].role == "user"
        assert loaded[0].parts[0].text == "z" * 1000

    def test_list_sessions(self, manager, tmp_path):
        # Create some files
        open(os.path.join(tmp_path, "session1.json"), "w").close()
        open(os.path.join(tmp_path, "session2.json"), "w").close()
        open(os.path.join(tmp_path, "not_a_session.txt"), "w").close()

        sessions = manager.list_sessions()
        assert len(sessions) == 2
        assert "session1" in sessions
        assert "session2" in sessions

    def test_delete_session(self, manager, tmp_path):
        session_id = "test_session"
        filepath = os.path.join(tmp_path, f"{session_id}.json")
        open(filepath, "w").close()

        assert manager.delete_session(session_id) is True
        assert not os.path.exists(filepath)

    def test_delete_session_not_exists(self, manager):
        assert manager.delete_session("nonexistent") is False

    def test_load_session_path_traversal(self, manager):
        assert manager.load_session("../../../etc/passwd") is None

    def test_delete_session_path_traversal(self, manager):
        assert manager.delete_session("../../../etc/passwd") is False
