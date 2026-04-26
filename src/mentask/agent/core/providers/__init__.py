from typing import Any

from mentask.core.models_hub import hub
from .base import BaseProvider
from .gemini import GeminiProvider
from .openai import OpenAIProvider


def get_provider(model_name: str, config: Any) -> BaseProvider:
    """
    Factory function to instantiate the correct provider.
    Consults models.dev via ModelsHub for dynamic dispatch.
    """
    # 1. Check if it's a models.dev scoped ID (provider:model)
    provider_prefix = None
    pure_model_name = model_name

    if ":" in model_name:
        provider_prefix, pure_model_name = model_name.split(":", 1)
        provider_prefix = provider_prefix.lower()

    # 2. Consult models.dev Hub for metadata
    info = hub.get_model(model_name)
    resolved_provider = info.get("_provider", "").lower() if info else None

    # Use scoped prefix if available, otherwise use resolved provider from hub
    active_provider_id = provider_prefix or resolved_provider

    # 3. Dispatch to specialized or generic provider
    if active_provider_id == "google" or any(x in pure_model_name.lower() for x in ["gemini", "learnlm"]):
        # Special handling for Google Gemini native SDK
        return GeminiProvider(pure_model_name, config)

    if active_provider_id == "openai":
        # Pure OpenAI (not just compatible)
        return OpenAIProvider(pure_model_name, config)

    # 4. Fallback to OpenAI-compatible provider for everything else (DeepSeek, Groq, etc.)
    # The OpenAIProvider handles endpoint resolution via the hub internally
    return OpenAIProvider(model_name, config)
