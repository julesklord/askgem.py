import pytest
from unittest.mock import MagicMock, patch

from mentask.agent.core.providers.openai import OpenAIProvider

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.load_api_key.return_value = "fake_key"
    return config

@pytest.mark.anyio
async def test_openai_provider_safe_endpoint(mock_config):
    """Test that a valid global HTTPS endpoint is accepted."""
    provider = OpenAIProvider("fake_provider:model_x", mock_config)

    with patch("mentask.core.models_hub.ModelsHub.get_model") as mock_get_model, \
         patch("mentask.core.models_hub.hub._data", new_callable=dict) as mock_data, \
         patch("mentask.tools.web_tools.is_safe_url", return_value=True):

        mock_get_model.return_value = {"id": "model_x"}
        mock_data.update({
            "providers": {
                "fake_provider": {
                    "endpoint": "https://api.valid-global-provider.com/v1"
                }
            }
        })

        success = await provider.setup()

        assert success is True
        assert provider.api_base == "https://api.valid-global-provider.com/v1"

@pytest.mark.anyio
async def test_openai_provider_rejects_http(mock_config):
    """Test that an HTTP endpoint is rejected, retaining default api_base."""
    provider = OpenAIProvider("fake_provider:model_x", mock_config)

    with patch("mentask.core.models_hub.ModelsHub.get_model") as mock_get_model, \
         patch("mentask.core.models_hub.hub._data", new_callable=dict) as mock_data, \
         patch("mentask.tools.web_tools.is_safe_url", return_value=True):

        mock_get_model.return_value = {"id": "model_x"}
        mock_data.update({
            "providers": {
                "fake_provider": {
                    "endpoint": "http://api.insecure-provider.com/v1"
                }
            }
        })

        success = await provider.setup()

        assert success is True
        assert provider.api_base == "https://api.openai.com/v1"

@pytest.mark.anyio
async def test_openai_provider_rejects_unsafe_url(mock_config):
    """Test that a URL failing is_safe_url (e.g. localhost/SSRF) is rejected."""
    provider = OpenAIProvider("fake_provider:model_x", mock_config)

    with patch("mentask.core.models_hub.ModelsHub.get_model") as mock_get_model, \
         patch("mentask.core.models_hub.hub._data", new_callable=dict) as mock_data, \
         patch("mentask.tools.web_tools.is_safe_url", return_value=False):

        mock_get_model.return_value = {"id": "model_x"}
        mock_data.update({
            "providers": {
                "fake_provider": {
                    "endpoint": "https://127.0.0.1/v1"
                }
            }
        })

        success = await provider.setup()

        assert success is True
        assert provider.api_base == "https://api.openai.com/v1"
