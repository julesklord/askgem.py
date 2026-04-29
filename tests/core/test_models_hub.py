import json
import time
from unittest.mock import MagicMock, mock_open, patch

import pytest

from mentask.core.models_hub import ModelsHub


@pytest.fixture
def reset_singleton():
    """Reset the ModelsHub singleton instance before and after each test."""
    ModelsHub._instance = None
    yield
    ModelsHub._instance = None


@pytest.fixture
def mock_config_dir(tmp_path):
    """Mock the config directory for cache paths."""
    with patch("mentask.core.models_hub.get_config_dir", return_value=tmp_path):
        yield tmp_path


def test_singleton(reset_singleton, mock_config_dir):
    hub1 = ModelsHub()
    hub2 = ModelsHub()
    assert hub1 is hub2


def test_load_cache_success(reset_singleton, mock_config_dir):
    cache_data = {"last_sync": 1000, "models_data": {"provider1": {"models": {"model1": {}}}}}
    cache_path = mock_config_dir / "models_cache.json"
    cache_path.write_text(json.dumps(cache_data), encoding="utf-8")

    hub = ModelsHub()
    assert hub._last_sync == 1000
    assert "provider1" in hub._data


def test_load_cache_missing(reset_singleton, mock_config_dir):
    hub = ModelsHub()
    assert hub._last_sync == 0
    assert hub._data == {}


def test_load_cache_invalid_json(reset_singleton, mock_config_dir):
    cache_path = mock_config_dir / "models_cache.json"
    cache_path.write_text("invalid json", encoding="utf-8")

    hub = ModelsHub()
    assert hub._last_sync == 0
    assert hub._data == {}


def test_save_cache(reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._last_sync = 2000
    hub._data = {"provider2": {"models": {"model2": {}}}}
    hub._save_cache()

    cache_path = mock_config_dir / "models_cache.json"
    assert cache_path.exists()

    with open(cache_path, encoding="utf-8") as f:
        data = json.load(f)
        assert data["last_sync"] == 2000
        assert "provider2" in data["models_data"]


def test_save_cache_error(reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._last_sync = 2000
    hub._data = {"provider2": {"models": {"model2": {}}}}

    # Mock open to raise an exception
    with patch("builtins.open", mock_open()) as mock_file:
        mock_file.side_effect = OSError("Mocked IO error")
        # Should not raise an exception, just log the error
        hub._save_cache()


@patch("urllib.request.urlopen")
def test_sync_success(mock_urlopen, reset_singleton, mock_config_dir):
    mock_data = {"provider3": {"models": {"model3": {}}}}

    import io

    mock_json = json.dumps(mock_data).encode("utf-8")
    mock_response = MagicMock()
    mock_response.__enter__.return_value = io.BytesIO(mock_json)
    mock_urlopen.return_value = mock_response

    with patch.object(ModelsHub, "_load_cache"):
        hub = ModelsHub()
        hub._last_sync = 0

        with patch.object(hub, "_save_cache"):
            hub.sync()

    assert hub._last_sync > 0
    assert "provider3" in hub._data


@patch("urllib.request.urlopen")
def test_sync_ttl_skip(mock_urlopen, reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._last_sync = time.time() - 900  # Less than CACHE_TTL (86400) difference

    hub.sync()

    mock_urlopen.assert_not_called()


@patch("urllib.request.urlopen")
def test_sync_force(mock_urlopen, reset_singleton, mock_config_dir):
    mock_data = {"provider4": {"models": {"model4": {}}}}

    import io

    mock_json = json.dumps(mock_data).encode("utf-8")
    mock_response = MagicMock()
    mock_response.__enter__.return_value = io.BytesIO(mock_json)
    mock_urlopen.return_value = mock_response

    with patch.object(ModelsHub, "_load_cache"):
        hub = ModelsHub()
        hub._last_sync = time.time() - 900  # Less than CACHE_TTL difference

        with patch.object(hub, "_save_cache"):
            hub.sync(force=True)

    mock_urlopen.assert_called_once()
    assert hub._last_sync > 0
    assert "provider4" in hub._data


@patch("urllib.request.urlopen")
def test_sync_network_error(mock_urlopen, reset_singleton, mock_config_dir):
    mock_urlopen.side_effect = Exception("Network error")

    hub = ModelsHub()
    hub._last_sync = 0
    hub._data = {"existing": "data"}  # Should not be overwritten

    hub.sync()

    assert hub._last_sync == 0  # Should not be updated
    assert hub._data == {"existing": "data"}


def test_get_model_direct(reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._data = {
        "google": {"id": "google", "name": "Google", "models": {"gemini-2.0-flash": {"name": "Gemini 2.0 Flash"}}}
    }

    # Direct match
    model = hub.get_model("gemini-2.0-flash")
    assert model is not None
    assert model["name"] == "Gemini 2.0 Flash"


def test_get_model_scoped(reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._data = {
        "google": {"id": "google", "name": "Google", "models": {"gemini-2.0-flash": {"name": "Gemini 2.0 Flash"}}}
    }

    # Scoped match
    model = hub.get_model("google:gemini-2.0-flash")
    assert model is not None
    assert model["name"] == "Gemini 2.0 Flash"


def test_get_model_not_found(reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._data = {
        "google": {"id": "google", "name": "Google", "models": {"gemini-2.0-flash": {"name": "Gemini 2.0 Flash"}}}
    }

    model = hub.get_model("gpt-4")
    assert model is None


@patch.object(ModelsHub, "sync")
def test_get_model_triggers_sync(mock_sync, reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._data = {}  # Empty data should trigger sync

    hub.get_model("gemini-2.0-flash")

    mock_sync.assert_called_once()


def test_search_by_query(reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._data = {
        "google": {
            "id": "google",
            "name": "Google",
            "models": {
                "gemini-2.0-flash": {"name": "Gemini 2.0 Flash", "tool_call": True},
                "gemini-2.0-pro": {"name": "Gemini 2.0 Pro", "tool_call": True},
            },
        },
        "openai": {"id": "openai", "name": "OpenAI", "models": {"gpt-4": {"name": "GPT 4", "tool_call": True}}},
    }

    results = hub.search(query="gemini")
    assert len(results) == 2
    assert results[0]["name"] == "Gemini 2.0 Flash"
    assert results[0]["_provider"] == "google"


def test_search_by_provider(reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._data = {
        "google": {"id": "google", "name": "Google", "models": {"gemini-2.0-flash": {"name": "Gemini 2.0 Flash"}}},
        "openai": {"id": "openai", "name": "OpenAI", "models": {"gpt-4": {"name": "GPT 4"}}},
    }

    results = hub.search(provider="openai")
    assert len(results) == 1
    assert results[0]["name"] == "GPT 4"


def test_search_by_capability(reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._data = {
        "google": {
            "id": "google",
            "models": {
                "gemini-2.0-flash": {"name": "Gemini 2.0 Flash", "tool_call": True},
                "gemini-vision": {"name": "Gemini Vision", "attachment": True},
            },
        }
    }

    # Test tool_call map
    results = hub.search(capability="tools")
    assert len(results) == 1
    assert results[0]["name"] == "Gemini 2.0 Flash"

    # Test vision map
    results = hub.search(capability="vision")
    assert len(results) == 1
    assert results[0]["name"] == "Gemini Vision"


@patch.object(ModelsHub, "sync")
def test_search_triggers_sync(mock_sync, reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._data = {}  # Empty data should trigger sync

    hub.search()

    mock_sync.assert_called_once()


def test_get_pricing_success(reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._data = {"google": {"models": {"gemini-2.0-flash": {"cost": {"input": "0.15", "output": 0.60}}}}}

    pricing = hub.get_pricing("gemini-2.0-flash")
    assert pricing["input"] == 0.15
    assert pricing["output"] == 0.60


@patch.object(ModelsHub, "sync")
def test_get_pricing_not_found(mock_sync, reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._data = {}

    pricing = hub.get_pricing("gpt-4")
    assert pricing["input"] == 0.0
    assert pricing["output"] == 0.0


def test_get_pricing_no_cost_info(reset_singleton, mock_config_dir):
    hub = ModelsHub()
    hub._data = {
        "google": {
            "models": {
                "gemini-2.0-flash": {}  # No cost block
            }
        }
    }

    pricing = hub.get_pricing("gemini-2.0-flash")
    assert pricing["input"] == 0.0
    assert pricing["output"] == 0.0
