import asyncio
import logging
import random
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from ....core.compression import ContextCompressor
from ...schema import Message, Role, ToolCall, UsageMetrics
from .base import BaseProvider

_logger = logging.getLogger("mentask")


class GeminiProvider(BaseProvider):
    """
    Provider implementation for Google Gemini models using the official GenAI SDK.
    """

    def __init__(self, model_name: str, config: Any):
        super().__init__(model_name, config)
        self.client: Any | None = None
        self.api_key: str | None = None

    async def setup(self) -> bool:
        from google import genai
        self.api_key = self.config.load_api_key("google")
        if not self.api_key:
            return False

        self.client = genai.Client(api_key=self.api_key, http_options={"api_version": "v1beta"})
        return True

    async def generate_stream(
        self,
        history: list[Message],
        tools_schema: list[dict[str, Any]],
        config: Any | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        from google.genai import types
        if not self.client:
            raise RuntimeError("GeminiProvider not setup.")

        # 1. Prepare system instruction and history
        system_instruction = "You are mentask, an autonomous coding agent."
        non_system_history = [msg for msg in history if msg.role != Role.SYSTEM]
        system_msgs = [msg for msg in history if msg.role == Role.SYSTEM]
        if system_msgs:
            system_instruction = str(system_msgs[-1].content)

        gemini_history = []
        for msg in non_system_history:
            role = "user" if msg.role in (Role.USER, Role.TOOL) else "model"
            parts = []
            if msg.role == Role.TOOL:
                parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=msg.metadata.get("tool_name", "unknown"),
                            id=msg.metadata.get("tool_call_id", ""),
                            response={"result": ContextCompressor.smart_compress(msg.content)},
                        )
                    )
                )
            elif msg.role == Role.ASSISTANT:
                content = msg.content
                if content:
                    parts.append(types.Part(text=ContextCompressor.smart_compress(content)))

                # Check for tool_calls if it's an AssistantMessage
                from ...schema import AssistantMessage

                if isinstance(msg, AssistantMessage):
                    for tc in msg.tool_calls:
                        parts.append(types.Part(function_call=types.FunctionCall(name=tc.name, args=tc.arguments)))
            else:
                # User or fallback
                if isinstance(msg.content, list):
                    for item in msg.content:
                        if isinstance(item, dict):
                            parts.append(types.Part(**item))
                        else:
                            parts.append(types.Part(text=str(item)))
                else:
                    parts.append(types.Part(text=ContextCompressor.smart_compress(str(msg.content))))

            if parts:
                gemini_history.append(types.Content(role=role, parts=parts))

        if not config or isinstance(config, dict):
            agnostic_config = config or {}
            system_instruction = agnostic_config.get("system_instruction", system_instruction)
            temp = agnostic_config.get("temperature", 0.7)

            # Tools can come from config or tools_schema argument
            active_tools = agnostic_config.get("tools", tools_schema)

            config = types.GenerateContentConfig(
                temperature=temp,
                system_instruction=system_instruction,
                tools=[
                    types.Tool(
                        function_declarations=[
                            types.FunctionDeclaration(
                                name=t["name"], description=t["description"], parameters=t["parameters"]
                            )
                            for t in active_tools
                        ]
                    )
                ]
                if active_tools
                else None,
            )

        # 2. Main Stream Loop with Exponential Backoff
        attempt = 1
        max_retries = 5
        base_delay = 2.0

        while attempt <= max_retries:
            try:
                async for chunk in await self.client.aio.models.generate_content_stream(
                    model=self.model_name, contents=gemini_history, config=config
                ):
                    if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                        yield {
                            "type": "metrics",
                            "content": UsageMetrics(
                                input_tokens=chunk.usage_metadata.prompt_token_count or 0,
                                output_tokens=chunk.usage_metadata.candidates_token_count or 0,
                            ),
                        }

                    if chunk.candidates:
                        cand = chunk.candidates[0]
                        if cand.content and cand.content.parts:
                            for part in cand.content.parts:
                                if hasattr(part, "text") and part.text:
                                    yield {"type": "text", "content": part.text}
                                if hasattr(part, "thought") and part.thought:
                                    yield {"type": "thought", "content": part.thought}
                                if hasattr(part, "function_call") and part.function_call:
                                    fc = part.function_call
                                    yield {
                                        "type": "tool_call",
                                        "content": ToolCall(
                                            id=getattr(fc, "id", None) or str(uuid.uuid4()),
                                            name=fc.name,
                                            arguments=fc.args or {},
                                        ),
                                    }
                break
            except Exception as e:
                # Basic retry logic moved here from SessionManager
                error_str = str(e).lower()
                retryable = any(kw in error_str for kw in ("429", "rate limit", "500", "503", "unavailable"))

                if retryable and attempt < max_retries:
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    _logger.warning(f"Retryable error in GeminiProvider (attempt {attempt}/{max_retries}): {e}")
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                raise e

    async def list_models(self) -> list[str]:
        if not self.client:
            return []
        try:
            models = []
            async for m in await self.client.aio.models.list():
                if "generateContent" in (m.supported_actions or []):
                    models.append(m.name.replace("models/", ""))
            return models
        except Exception as e:
            _logger.error(f"Error listing Gemini models: {e}")
            return []
