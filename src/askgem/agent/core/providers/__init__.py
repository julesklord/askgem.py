from typing import Any
from .base import BaseProvider
from .gemini import GeminiProvider
from .openai import OpenAIProvider

def get_provider(model_name: str, config: Any) -> BaseProvider:
    """
    Factory function to instantiate the correct provider.
    """
    # Force Gemini for standard names
    if any(x in model_name.lower() for x in ["gemini", "learnlm"]):
        return GeminiProvider(model_name, config)
    
    # Check if it's a models.dev scoped ID (provider:model)
    if ":" in model_name:
        provider_prefix = model_name.split(":")[0].lower()
        if provider_prefix == "google":
            return GeminiProvider(model_name.split(":", 1)[1], config)
            
    # Fallback to OpenAI-compatible provider for everything else
    return OpenAIProvider(model_name, config)
