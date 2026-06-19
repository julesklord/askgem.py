import asyncio
import json
import logging
import urllib.error
import urllib.request
from collections.abc import AsyncGenerator
from typing import Any

from mentask.core.constants import DEFAULT_REQUEST_TIMEOUT, OPENAI_DEFAULT_API_BASE

from ....core.subprocess_safety import validate_url_scheme
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
        self.api_base: str = OPENAI_DEFAULT_API_BASE  # Default
        self.request_timeout = DEFAULT_REQUEST_TIMEOUT  # Default timeout in seconds

    async def setup(self) -> bool:
        """Resolves API Base and Key dynamically using models.dev metadata."""

        from ....core.models_hub import hub
        from ....tools.web_tools import is_safe_url

        # 1. Try to find provider info in the Hub
        provider_meta = hub.get_provider_for_model(self.model_name)

        provider_id = "openai"  # Default

        if provider_meta:
            provider_id = provider_meta["id"]
            candidate_endpoint = provider_meta.get("api")

            if candidate_endpoint:
                if candidate_endpoint.startswith("https://") and is_safe_url(candidate_endpoint):
                    self.api_base = candidate_endpoint
                    _logger.info(f"Resolved endpoint for {provider_id}: {self.api_base}")
                else:
                    _logger.warning(f"Rejected unsafe or non-HTTPS endpoint for {provider_id}: {candidate_endpoint}")

        # 2. Resolve API Key
        # Priority: Specific provider key via ConfigManager > Generic fallback
        # Check env variables suggested by models.dev
        env_vars = provider_meta.get("env", []) if provider_meta else []

        # Try specific provider ID first
        res = self.config.load_api_key(provider_id, return_source=True)

        # If not found, try the suggested env names from models.dev
        if res and not res[0] and env_vars:
            for env_name in env_vars:
                # We normalize env names (e.g. DEEPSEEK_API_KEY -> deepseek) to check config
                normalized = env_name.replace("_API_KEY", "").lower()
                res_env = self.config.load_api_key(normalized, return_source=True)
                if res_env and res_env[0]:
                    res = res_env
                    provider_id = normalized
                    break

        if res and isinstance(res, tuple) and len(res) == 2:
            self.api_key, self.key_source = res
        else:
            self.api_key, self.key_source = None, None

        if not self.api_key and provider_id != "openai":
            # Fallback to generic openai key if specific one is missing
            res2 = self.config.load_api_key("openai", return_source=True)
            if res2 and isinstance(res2, tuple) and len(res2) == 2:
                self.api_key, self.key_source = res2

        if not self.api_key:
            _logger.warning(f"No API key found for {self.model_name} (provider: {provider_id})")
            return False

        return True

    async def generate_stream(
        self,
        history: list[Message],
        tools_schema: list[dict[str, Any]],
        config: Any | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:

        url = f"{self.api_base}/chat/completions"
        system_instruction = config.get("system_instruction") if config else None
        messages = self._build_messages(history, system_instruction)

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

        validate_url_scheme(url)
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        def _do_request():
            return urllib.request.urlopen(req, timeout=self.request_timeout)  # nosec B310

        try:
            response = await asyncio.to_thread(_do_request)

            in_thought = False
            # Buffer for tool calls: index -> {id, name, arguments_str}
            tool_calls_buffer = {}

            while True:
                line_raw = await asyncio.to_thread(response.readline)
                if not line_raw:
                    break

                line = line_raw.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue

                raw_data = line[6:]
                if raw_data == "[DONE]":
                    break

                try:
                    chunk = json.loads(raw_data)
                except Exception as e:  # nosec B112
                    _logger.debug(f"Failed to parse OpenAI SSE chunk: {e}")
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
                    for tc_delta in delta["tool_calls"]:
                        idx = tc_delta.get("index", 0)
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {"id": "", "name": "", "arguments": ""}

                        if "id" in tc_delta:
                            tool_calls_buffer[idx]["id"] += tc_delta["id"]

                        if "function" in tc_delta:
                            f = tc_delta["function"]
                            if "name" in f:
                                tool_calls_buffer[idx]["name"] += f["name"]
                            if "arguments" in f:
                                tool_calls_buffer[idx]["arguments"] += f["arguments"]

                if "usage" in chunk:
                    u = chunk["usage"]
                    yield {
                        "type": "metrics",
                        "content": UsageMetrics(
                            input_tokens=u.get("prompt_tokens", 0), output_tokens=u.get("completion_tokens", 0)
                        ),
                    }

            # Emit all buffered tool calls after the stream ends
            for idx in sorted(tool_calls_buffer.keys()):
                tc = tool_calls_buffer[idx]
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                    yield {
                        "type": "tool_call",
                        "content": ToolCall(
                            id=tc["id"] or "unknown",
                            name=tc["name"],
                            arguments=args,
                        ),
                    }
                except json.JSONDecodeError as e:
                    _logger.error(f"Failed to parse tool call arguments for {tc['name']}: {e}. Raw: {tc['arguments']}")

        except Exception as e:
            _logger.error(f"OpenAIProvider error: {e}")
            raise e

    def _build_messages(self, history: list[Message], system_instruction: str | None) -> list[dict[str, Any]]:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        from ....core.compression import ContextCompressor

        for msg in history:
            if msg.role == Role.SYSTEM:
                continue  # Already handled or will be merged

            role = "user" if msg.role == Role.USER else "assistant"
            if msg.role == Role.TOOL:
                # OpenAI tool response format
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": msg.metadata.get("tool_call_id"),
                    "content": ContextCompressor.smart_compress(str(msg.content)),
                }
                if msg.metadata.get("tool_name"):
                    tool_msg["name"] = msg.metadata.get("tool_name")
                messages.append(tool_msg)  # type: ignore[arg-type]
            else:
                compressed_content = ContextCompressor.smart_compress(str(msg.content))
                msg_dict: dict[str, Any] = {
                    "role": role,
                    "content": compressed_content,
                }

                # Check for tool_calls if it's an AssistantMessage
                from ...schema import AssistantMessage

                if isinstance(msg, AssistantMessage) and msg.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments)
                                if isinstance(tc.arguments, dict)
                                else str(tc.arguments),
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                    # Local models/Ollama often expect content to be strictly null if there are tool_calls and no text
                    if not compressed_content:
                        msg_dict["content"] = None
                elif not compressed_content:
                    msg_dict["content"] = ""

                messages.append(msg_dict)
        return messages

    async def list_models(self) -> list[str]:
        """Returns models from the Hub that are compatible with this provider."""
        from ....core.models_hub import hub

        # Determine target provider based on active base URL or model name
        target_provider = "openai"
        if ":" in self.model_name:
            target_provider = self.model_name.split(":")[0]
        elif "groq" in self.api_base.lower():
            target_provider = "groq"
        elif "deepseek" in self.api_base.lower():
            target_provider = "deepseek"

        # Search the hub for all models from this provider
        results = hub.search(provider=target_provider)

        # If no results for specific provider, try searching by query
        if not results and target_provider != "openai":
            results = hub.search(query=target_provider)

        if not results:
            # Fallback to general search if still nothing
            results = hub.search("")

        # Return scoped IDs if they exist, otherwise raw IDs
        model_list = []
        for m in results:
            m_id = m["id"]
            provider_meta = m.get("_provider")
            p_id = provider_meta.get("id") if isinstance(provider_meta, dict) else provider_meta

            if p_id and p_id != "openai":
                model_list.append(f"{p_id}:{m_id}")
            else:
                model_list.append(m_id)

        return sorted(list(set(model_list)))

    async def check_health(self, model_name: str) -> tuple[bool, str | None]:
        if not self.api_key:
            return False, "401"

        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        validate_url_scheme(url)
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        def _do_request():
            try:
                # Use a reasonable timeout for health checks, scaled with request_timeout
                health_timeout = max(10, self.request_timeout // 3)
                with urllib.request.urlopen(req, timeout=health_timeout):  # nosec B310
                    return True, None
            except urllib.error.HTTPError as e:
                return False, str(e.code)
            except Exception:
                return False, "ERR"

        return await asyncio.to_thread(_do_request)
