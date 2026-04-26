import asyncio
import json
import logging
import urllib.parse
import urllib.request
from collections.abc import AsyncGenerator
from typing import Any

from ...schema import Message, Role, ToolCall, UsageMetrics
from .base import BaseProvider

_logger = logging.getLogger("mentask")


class OpenAIProvider(BaseProvider):
    """
    Provider for OpenAI-compatible APIs (DeepSeek, Groq, local LLMs, etc.).
    Uses urllib for lightweight integration without extra dependencies.
    """

    def __init__(self, model_name: str, config: Any):
        super().__init__(model_name, config)
        self.api_key: str | None = None
        self.api_base: str = "https://api.openai.com/v1"  # Default

    async def setup(self) -> bool:
        """Resolves API Base and Key dynamically using models.dev metadata."""
        import os

        from ....core.models_hub import hub

        # 1. Try to find model info in the Hub
        info = hub.get_model(self.model_name)
        provider_id = None

        if info:
            # We assume the model ID might have a preferred provider or we pick the first one
            # Models.dev doesn't directly link model to provider endpoint in a simple way
            # unless we search the providers list.

            # For now, let's look at the providers listed in the Hub data
            providers = hub._data.get("providers", {})

            # If the model ID is scoped (provider:model), we use that provider
            if ":" in self.model_name:
                provider_id = self.model_name.split(":")[0]

            if provider_id and provider_id in providers:
                p_info = providers[provider_id]
                self.api_base = p_info.get("endpoint", self.api_base)
                _logger.info(f"Resolved endpoint for {provider_id}: {self.api_base}")

        # 2. Resolve API Key
        # Priority: Specific provider key via ConfigManager > Generic fallback
        active_id = provider_id or "openai"
        self.api_key = self.config.load_api_key(active_id)

        if not self.api_key and active_id != "openai":
            # Fallback to generic openai key if specific one is missing
            self.api_key = self.config.load_api_key("openai")

        if not self.api_key:
            _logger.warning(f"No API key found for {self.model_name} (provider: {active_id})")
            return False

        return True

    async def generate_stream(
        self,
        history: list[Message],
        tools_schema: list[dict[str, Any]],
        config: Any | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:

        url = f"{self.api_base}/chat/completions"
        # Prepare messages
        messages = []
        system_instruction = config.get("system_instruction") if config else None

        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        from ....core.compression import ContextCompressor

        for msg in history:
            if msg.role == Role.SYSTEM:
                continue  # Already handled or will be merged

            role = "user" if msg.role == Role.USER else "assistant"
            if msg.role == Role.TOOL:
                # OpenAI tool response format
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.metadata.get("tool_call_id"),
                        "content": ContextCompressor.smart_compress(str(msg.content)),
                    }
                )
            else:
                messages.append({"role": role, "content": ContextCompressor.smart_compress(str(msg.content))})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "temperature": config.get("temperature", 0.7) if config else 0.7,
        }

        if tools_schema:
            payload["tools"] = [{"type": "function", "function": t} for t in tools_schema]

        data = json.dumps(payload).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        def _do_request():
            return urllib.request.urlopen(req, timeout=60)

        try:
            response = await asyncio.to_thread(_do_request)

            in_thought = False

            for line in response:
                line = line.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue

                raw_data = line[6:]
                if raw_data == "[DONE]":
                    break

                try:
                    chunk = json.loads(raw_data)
                except Exception:
                    continue

                delta = chunk["choices"][0].get("delta", {})

                if "content" in delta and delta["content"]:
                    content = delta["content"]

                    # Parse DeepSeek-style <think> tags
                    if "<think>" in content:
                        in_thought = True
                        content = content.replace("<think>", "")

                    if "</think>" in content:
                        in_thought = False
                        content = content.replace("</think>", "")

                    if in_thought:
                        yield {"type": "thought", "content": content}
                    elif content.strip():
                        yield {"type": "text", "content": content}

                if "tool_calls" in delta:
                    for tc in delta["tool_calls"]:
                        if "function" in tc:
                            yield {
                                "type": "tool_call",
                                "content": ToolCall(
                                    id=tc.get("id", "unknown"),
                                    name=tc["function"].get("name", ""),
                                    arguments=json.loads(tc["function"].get("arguments", "{}")),
                                ),
                            }

                if "usage" in chunk:
                    u = chunk["usage"]
                    yield {
                        "type": "metrics",
                        "content": UsageMetrics(
                            input_tokens=u.get("prompt_tokens", 0), output_tokens=u.get("completion_tokens", 0)
                        ),
                    }
        except Exception as e:
            _logger.error(f"OpenAIProvider error: {e}")
            raise e

    async def list_models(self) -> list[str]:
        """Returns models from the Hub that are compatible with this provider."""
        from ....core.models_hub import hub

        # Return top 20 models from the hub as a fallback or models matching current prefix
        results = hub.search("")
        return [m["id"] for m in results[:20]]
