from typing import Any

from mentask.core.models_hub import hub

from .base import BaseProvider
from .cli import CLIProvider
from .gemini import GeminiProvider
from .gemma import GemmaProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider


def get_provider(model_name: str, config: Any) -> BaseProvider:
    """
    Factory function to instantiate the correct provider.
    Consults models.dev via ModelsHub for dynamic dispatch.
    """
    # 0. Check for local mode enforcement
    # ChatAgent passes local_mode through dependencies or we check config/settings
    is_local_mode = False
    if hasattr(config, "settings"):
        is_local_mode = config.settings.get("local_mode", False)

    # 1. Check if it's a models.dev scoped ID (provider:model)
    provider_prefix = None
    pure_model_name = model_name

    if ":" in model_name:
        provider_prefix, pure_model_name = model_name.split(":", 1)
        provider_prefix = provider_prefix.lower()

    # 1.5. Check for CLI bridge
    from mentask.core.model_discovery import get_installed_cli_binaries
    installed_clis = get_installed_cli_binaries()

    if provider_prefix == "cli" or provider_prefix in installed_clis:
        # Backward compatibility, explicit tag, or direct binary:model notation
        return CLIProvider(model_name, config)

    # 2. Local/Specialized detect logic
    if is_local_mode or provider_prefix == "ollama" or "ollama" in pure_model_name.lower():
        # Special case: Gemma through Ollama needs Gemma formatting
        if "gemma" in pure_model_name.lower():
            return GemmaProvider(model_name, config)
        return OllamaProvider(model_name, config)

    # 3. Consult models.dev Hub for metadata
    provider_meta = hub.get_provider_for_model(model_name)
    resolved_provider = provider_meta.get("id", "").lower() if provider_meta else None

    # Use scoped prefix if available, otherwise use resolved provider from hub
    active_provider_id = provider_prefix or resolved_provider

    # 3. Dispatch to specialized or generic provider
    if active_provider_id == "google" or any(x in pure_model_name.lower() for x in ["gemini", "learnlm"]):
        # Special handling for Google Gemini native SDK
        return GeminiProvider(pure_model_name, config)

    if active_provider_id == "gemma" or "gemma" in pure_model_name.lower():
        return GemmaProvider(pure_model_name, config)

    if active_provider_id == "openai":
        # Pure OpenAI (not just compatible)
        return OpenAIProvider(pure_model_name, config)

    # 4. Fallback to OpenAI-compatible provider for everything else (DeepSeek, Groq, etc.)
    # The OpenAIProvider handles endpoint resolution via the hub internally
    return OpenAIProvider(model_name, config)
