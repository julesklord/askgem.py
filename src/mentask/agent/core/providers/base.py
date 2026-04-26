from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from ...schema import Message


class BaseProvider(ABC):
    """
    Abstract base class for all LLM providers (Gemini, OpenAI, etc.).
    """

    def __init__(self, model_name: str, config: Any):
        self.model_name = model_name
        self.config = config

    @abstractmethod
    async def setup(self) -> bool:
        """Initializes the provider's client/API."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        history: list[Message],
        tools_schema: list[dict[str, Any]],
        config: Any | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Streams a response from the model.
        Yields chunks of type: text, thought, tool_call, metrics.
        """
        pass

    async def list_models(self) -> list[str]:
        """Returns a list of available models for this provider."""
        return []
