"""
Session management module for AskGem.

Handles API authentication, client initialization, and exponential backoff retry logic.
"""

import asyncio
import logging
import os
import random
from collections.abc import AsyncGenerator
from typing import Any, cast  # noqa: UP035

from google import genai
from google.genai import types
from rich.prompt import Prompt

from ...cli.console import console
from ...core.compression import ContextCompressor
from ...core.i18n import _
from ..schema import AssistantMessage, Message, Role, ToolCall, UsageMetrics
from .simulation import SimulationManager, SimulationSession

_logger = logging.getLogger("askgem")

RETRYABLE_KEYWORDS = (
    "429",
    "resource exhausted",
    "rate limit",
    "500",
    "internal",
    "503",
    "unavailable",
    "deadline exceeded",
    "timeout",
)


class SessionManager:
    """Manages the Google GenAI client and chat sessions."""

    def __init__(self, config_manager, model_name: str, simulation: SimulationManager | None = None):
        self.config = config_manager
        self.model_name = model_name
        self.client: genai.Client | None = None
        self.chat_session: Any | None = None
        self.simulation = simulation
        self.recent_files: list[str] = []  # Track last 5 unique files accessed

        from ...core.compression import ContextSnapper

        limit = ContextSnapper(model_name).limit
        self.compaction_threshold = int(limit * 0.8)

        self._is_compacting = False

    async def close(self):
        """Cleanly closes the API client and resources."""
        if self.client:
            # We try to access the underlying session if it exists to close it
            try:
                # The GenAI SDK uses an internal manager, we null it to trigger GC
                self.client = None
                self.chat_session = None
            except Exception:
                pass
            _logger.info("Session resources released.")

    async def setup_api(self, interactive: bool = True) -> bool:
        """Loads and validates the Google API key (Async)."""
        # Playback mode doesn't need real API keys
        if self.simulation and self.simulation.mode == "playback":
            return True

        # Priority: ConfigManager already handles Env > Settings > Keyring
        api_key = self.config.load_api_key()

        if not api_key:
            if not interactive:
                _logger.error("API key missing in non-interactive mode.")
                return False

            console.print(f"\n[error]{_('api.missing')}[/error]")
            api_key = Prompt.ask(f"[google.blue]{_('api.prompt')}[/google.blue]").strip()

            if not api_key:
                console.print(f"[error][X] {_('api.fatal')}[/error]")
                return False

            save_choice = Prompt.ask(_("api.save")).strip().lower()
            if save_choice != "n":
                self.config.save_api_key(api_key)

        # Transparency Logging
        source = "Keyring/Settings"
        color = "dim"
        if os.getenv("GOOGLE_API_KEY"):
            source = "Environment Variable (GOOGLE_API_KEY)"
            color = "bold yellow"
        elif os.getenv("GEM_API_KEY"):
            source = "Environment Variable (GEM_API_KEY)"
            color = "bold yellow"
        elif os.getenv("GEMINI_API_KEY"):
            source = "Environment Variable (GEMINI_API_KEY)"
            color = "bold yellow"

        console.print(f"[{color}]> API Key loaded from: {source} (***{api_key[-4:]})[/{color}]")

        self.client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
        return True

    async def ensure_session(self, model_config: any, history: list[Any] | None = None) -> Any:
        """Ensures an active chat session is correctly initialized."""
        if self.chat_session is not None:
            return self.chat_session

        if self.simulation:
            real_session = None
            if self.simulation.mode == "record":
                if self.client is None:
                    raise RuntimeError("API not setup for recording. Call setup_api() first.")
                real_session = self.client.aio.chats.create(
                    model=self.model_name,
                    config=model_config,
                    history=history,
                )
            self.chat_session = SimulationSession(self.simulation, real_session=real_session)
            # If no real_session (playback), we might need to set internal history
            if not real_session and history:
                self.chat_session.history = history
            return self.chat_session

        self.chat_session = self.client.aio.chats.create(
            model=self.model_name,
            config=model_config,
            history=history,
        )

    async def reset_session(self, model_config: Any) -> Any:
        """Resets the current session, forcing a clean re-initialization."""
        self.chat_session = None
        return await self.ensure_session(model_config)

    def update_recent_files(self, file_path: str):
        """Adds a file to the recent_files buffer, keeping only the last 5 unique ones."""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.append(file_path)
        if len(self.recent_files) > 5:
            self.recent_files.pop(0)

    async def _compact_history(self, history: list[Message], last_usage: UsageMetrics) -> list[Message]:
        """Summarizes the history using a sidechain call and restarts context."""
        from ...core.summarizer import Summarizer

        _logger.info("Context limit approached. Initiating auto-compaction.")
        console.print(f"\n[warning][⏳] {_('engine.compacting')}[/warning]")

        # 1. Create summarization context (no tools, high density prompt)
        raw_summary_response = await self.generate_response(
            history=history,
            tools_schema=[],
            config=types.GenerateContentConfig(
                system_instruction=Summarizer.BASE_SUMMARIZATION_PROMPT,
            ),
        )

        raw_text = raw_summary_response["message"].content
        clean_summary = Summarizer.format_summary(raw_text)

        # 2. Build new history starting with system and boundary
        new_history = [msg for msg in history if msg.role == Role.SYSTEM]
        new_history.append(
            Message(
                role=Role.SYSTEM,
                content="[COMPACTION BOUNDARY] The previous conversation has been summarized to save tokens.",
            )
        )

        continuation_text = Summarizer.get_user_continuation_message(clean_summary)

        # Re-inject recent files context
        if self.recent_files:
            files_context = "\n\nRETAINED CONTEXT (Recent Files):\n"
            for path in self.recent_files:
                if os.path.exists(path):
                    try:
                        with open(path, encoding="utf-8") as f:
                            content = f.read()
                            if len(content) > 2000:
                                content = content[:2000] + "..."
                            files_context += f"\nFile: {path}\n```\n{content}\n```\n"
                    except Exception:
                        pass
            continuation_text += files_context

        new_history.append(Message(role=Role.USER, content=continuation_text))

        # 3. Calculate savings if metrics available
        if hasattr(self, "metrics") and last_usage:
            # We estimate savings as the difference between the full history and the new summary context
            saved = last_usage.input_tokens - 1000
            if saved > 0:
                self.metrics.add_savings(saved)

        _logger.info("Compaction complete.")
        return new_history

    async def handle_retryable_error(self, e: Exception, attempt: int, max_retries: int, base_delay: float) -> bool:
        """Evaluates if an API error is retryable and sleeps if appropriate."""
        error_str = str(e).lower()
        is_retryable = any(keyword in error_str for keyword in RETRYABLE_KEYWORDS)

        if is_retryable and attempt < max_retries:
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            _logger.warning("Retryable API error (attempt %d/%d): %s", attempt, max_retries, e)
            console.print(
                f"\n[warning]{_('engine.retry', attempt=attempt, max=max_retries, delay=f'{delay:.1f}')}[/warning]"
            )
            await asyncio.sleep(delay)
            return True
        if is_retryable:
            _logger.error("All %d retry attempts exhausted: %s", max_retries, e)
        return False

    async def generate_response(
        self,
        history: list[Message],
        tools_schema: list[dict[str, Any]],
        config: types.GenerateContentConfig | None = None,
    ) -> dict[str, Any]:
        """Stateless bridge that collects all chunks from generate_stream."""
        # This keeps existing code (like Summarizer) working without changes
        full_text = ""
        thought = None
        tool_calls = []
        usage = UsageMetrics()

        async for chunk in self.generate_stream(history, tools_schema, config):
            if chunk["type"] == "text":
                full_text += chunk["content"]
            elif chunk["type"] == "thought":
                thought = chunk["content"]
            elif chunk["type"] == "tool_call":
                tool_calls.append(chunk["content"])
            elif chunk["type"] == "metrics":
                usage = chunk["content"]

        return {
            "message": AssistantMessage(
                content=full_text, thought=thought, tool_calls=tool_calls, model=self.model_name, usage=usage
            )
        }

    async def generate_stream(
        self,
        history: list[Message],
        tools_schema: list[dict[str, Any]],
        config: types.GenerateContentConfig | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Provides a real-time stream of parts (text, thought, tool_calls, metrics)."""
        if not self.client:
            raise RuntimeError("API not setup.")

        # 1. Prepare system instruction and history
        system_instruction = "You are AskGem, an autonomous coding agent."
        non_system_history = [msg for msg in history if msg.role != Role.SYSTEM]
        system_msgs = [msg for msg in history if msg.role == Role.SYSTEM]
        if system_msgs:
            system_instruction = str(system_msgs[-1].content)

        # Auto-compaction check (0.8 of threshold)
        last_usage = getattr(history[-1], "usage", None) if history else None
        if not self._is_compacting and last_usage and last_usage.input_tokens > (self.compaction_threshold * 0.8):
            try:
                self._is_compacting = True
                history[:] = await self._compact_history(history, last_usage)
                non_system_history = [msg for msg in history if msg.role != Role.SYSTEM]
            finally:
                self._is_compacting = False

        gem_history = []
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
                assistant_msg = cast("AssistantMessage", msg)
                for tc in assistant_msg.tool_calls:
                    parts.append(types.Part(function_call=types.FunctionCall(name=tc.name, args=tc.arguments)))
            else:
                # User or fallback
                if isinstance(msg.content, list):
                    # Multi-part content (Images, etc)
                    for item in msg.content:
                        if isinstance(item, dict):
                            # Assume it's a part-like dict
                            parts.append(types.Part(**item))
                        else:
                            parts.append(types.Part(text=str(item)))
                else:
                    parts.append(types.Part(text=ContextCompressor.smart_compress(str(msg.content))))
            if parts:
                gemini_history.append(types.Content(role=role, parts=parts))

        if not config:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[
                    types.Tool(
                        function_declarations=[
                            types.FunctionDeclaration(
                                name=t["name"], description=t["description"], parameters=t["parameters"]
                            )
                            for t in tools_schema
                        ]
                    )
                ]
                if tools_schema
                else None,
            )

        # 2. Main Stream Loop with Exponential Backoff
        attempt = 1
        max_retries = 5
        import uuid

        while attempt <= max_retries:
            try:
                # Actual streaming call to Gemini SDK
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
                should_retry = await self.handle_retryable_error(e, attempt, max_retries, base_delay=2.0)
                if not should_retry:
                    raise e
                attempt += 1
