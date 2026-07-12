import logging
from typing import Any

from .openai import OpenAIProvider

_logger = logging.getLogger("mentask.agent.providers.ollama")


class OllamaProvider(OpenAIProvider):
    """
    Provider for local Ollama instances.
    Defaults to http://localhost:11434/v1 and uses OpenAI-compatible mode.
    """

    def __init__(self, model_name: str, config: Any):
        # We strip the 'ollama:' prefix if present for the internal model name
        pure_model = (
            model_name.split(":", 1)[1] if ":" in model_name and model_name.startswith("ollama:") else model_name
        )
        super().__init__(pure_model, config)
        self.api_base = "http://localhost:11434/v1"
        self.request_timeout = 300  # Ollama needs more time to load models

    async def setup(self) -> bool:
        """
        Setup for Ollama.
        Usually doesn't require an API key, but we'll try to load one if configured.
        """
        # Try to resolve custom endpoint from config if user wants to override localhost
        custom_endpoint = self.config.settings.get("ollama_endpoint")
        if custom_endpoint:
            self.api_base = custom_endpoint

        # Load API key (rarely needed for local Ollama, but supported)
        res = self.config.load_api_key("ollama", return_source=True)
        if res and isinstance(res, tuple) and len(res) == 2:
            self.api_key, self.key_source = res
        else:
            # Default for Ollama
            self.api_key = "ollama"
            self.key_source = "Default (Local)"

        _logger.info(f"Ollama Provider initialized at {self.api_base} with model {self.model_name}")
        return True
