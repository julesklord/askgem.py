"""
Session management module for mentask.

Handles provider selection, authentication, and context lifecycle (compaction).
"""

import logging
import os
from collections.abc import AsyncGenerator
from typing import Any  # noqa: UP035

from rich.panel import Panel
from rich.prompt import Prompt

from ...cli.console import console
from ...core.i18n import _
from ..schema import AssistantMessage, Message, Role, UsageMetrics
from .providers import get_provider
from .simulation import SimulationManager

_logger = logging.getLogger("mentask")


class SessionManager:
    """Manages the model provider and chat session lifecycle."""

    def __init__(self, config_manager, model_name: str, simulation: SimulationManager | None = None):
        self.config = config_manager
        self.model_name = model_name
        self.simulation = simulation
        self.recent_files: list[str] = []  # Track last 5 unique files accessed
        self.metrics: Any | None = None  # Will be assigned by ChatAgent or initialized later

        # Initialize provider via factory
        self.provider = get_provider(model_name, config_manager)

        from ...core.compression import ContextSnapper

        limit = ContextSnapper(model_name).limit
        self.compaction_threshold = int(limit * 0.8)
        self._is_compacting = False

    async def list_models(self) -> list[str]:
        """Lists available models from the active provider."""
        try:
            return await self.provider.list_models()
        except Exception as e:
            _logger.warning(f"Failed to list models from provider: {e}")
            return []

    async def switch_model(self, new_model_name: str) -> bool:
        """Switches the active model and re-initializes the provider if needed."""
        self.model_name = new_model_name
        self.provider = get_provider(new_model_name, self.config)

        # Update metrics to use the new model's pricing
        if self.metrics:
            self.metrics.model_name = new_model_name

        from ...core.compression import ContextSnapper

        limit = ContextSnapper(new_model_name).limit
        self.compaction_threshold = int(limit * 0.8)

        return await self.setup_api()

    async def setup_api(self, interactive: bool = True) -> bool:
        """Loads and validates the API key for the selected provider."""
        # Playback mode doesn't need real API keys
        if self.simulation and self.simulation.mode == "playback":
            return True

        success = await self.provider.setup()

        if not success:
            if not interactive:
                _logger.error("API key missing in non-interactive mode.")
                return False

            # Determine provider name for the prompt
            provider_class = self.provider.__class__.__name__.replace("Provider", "")

            # --- Start Improved Setup UI ---
            console.print(
                Panel.fit(
                    f"[bold yellow]󰚌 SETUP REQUIRED: {provider_class.upper()}[/bold yellow]\n"
                    f"No valid credentials found for the active engine.",
                    border_style="yellow",
                )
            )

            from ...core.models_hub import hub

            hub.sync_local()
            local_clis = [m for m in hub._local_models.values() if m["_provider"]["id"] == "cli"]
            ollama_running = any(m["_provider"]["id"] == "ollama" for m in hub._local_models.values())

            choices = ["k", "m"]
            menu = "[bold]Options:[/bold]\n"
            menu += "  [bold cyan]k[/bold] - Enter API Key manually\n"
            if local_clis or ollama_running:
                menu += "  [bold green]l[/bold] - Use a local agent (Ollama/CLI Bridge)\n"
                choices.append("l")
            menu += "  [bold magenta]m[/bold] - Switch to a different provider\n"

            console.print(menu)
            action = Prompt.ask("Action", choices=choices, default="k")

            if action == "l":
                # List local models
                options = list(hub._local_models.keys())
                for i, m in enumerate(options, 1):
                    console.print(f"  {i}. {m}")
                idx = int(Prompt.ask("Select model #", choices=[str(i + 1) for i in range(len(options))], default="1"))
                selected = options[idx - 1]
                # Force prefix if needed
                if selected in [m["id"] for m in hub._local_models.values() if m["_provider"]["id"] == "cli"]:
                    await self.switch_model(f"cli:{selected}")
                else:
                    await self.switch_model(f"ollama:{selected}")
                return await self.setup_api()

            if action == "m":
                new_model = Prompt.ask("Enter model ID (e.g. deepseek:deepseek-chat, openai:gpt-4o)")
                await self.switch_model(new_model)
                return await self.setup_api()

            # Default: Manual Key entry
            provider_id = "google" if provider_class == "Gemini" else "openai"
            if provider_class == "OpenAI" and ":" in self.model_name:
                provider_id = self.model_name.split(":")[0].lower()

            console.print(f"\n[error]{_('api.missing', provider=provider_id.upper())}[/error]")
            prompt_msg = _("api.prompt", provider=provider_id.upper())
            api_key = Prompt.ask(f"[bold cyan]{prompt_msg}[/bold cyan]").strip()

            if not api_key:
                console.print(f"[error][X] {_('api.fatal')}[/error]")
                return False

            save_choice = Prompt.ask(_("api.save")).strip().lower()
            if save_choice != "n":
                self.config.save_api_key(api_key, provider=provider_id)

            # Re-try setup with new key
            return await self.provider.setup()
            # --- End Improved Setup UI ---

        # Log active provider
        source = getattr(self.provider, "key_source", "Unknown")
        provider_name = self.provider.__class__.__name__.replace("Provider", "")
        console.print(f"[dim]> Engine: [bold]{provider_name}[/] | Source: {source}[/dim]")

        return True

    async def ensure_session(self, model_config: Any, history: list[Any] | None = None) -> Any:
        """Stub for backward compatibility with legacy ChatAgent code."""
        # The new provider system is mostly stateless or manages its own session
        return self

    async def reset_session(self, model_config: Any) -> Any:
        """Resets the current session."""
        return self

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

        # 1. Create summarization context
        raw_summary_response = await self.generate_response(
            history=history,
            tools_schema=[],
            config=None,  # System instruction is handled by provider logic usually or we'd need a way to pass it
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
                    except (OSError, UnicodeDecodeError) as e:
                        _logger.warning(f"Failed to read recent file {path} for compaction context: {e}")
            continuation_text += files_context

        new_history.append(Message(role=Role.USER, content=continuation_text))

        # 3. Calculate savings
        if self.metrics and last_usage:
            saved = last_usage.input_tokens - 1000
            if saved > 0:
                self.metrics.add_savings(saved)

        _logger.info("Compaction complete.")
        return new_history

    async def generate_response(
        self,
        history: list[Message],
        tools_schema: list[dict[str, Any]],
        config: Any | None = None,
    ) -> dict[str, Any]:
        """Stateless bridge that collects all chunks from generate_stream."""
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
        config: Any | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Provides a real-time stream of parts from the active provider."""

        # Auto-compaction check
        last_usage = getattr(history[-1], "usage", None) if history else None
        if not self._is_compacting and last_usage and last_usage.input_tokens > (self.compaction_threshold * 0.8):
            try:
                self._is_compacting = True
                history[:] = await self._compact_history(history, last_usage)
            finally:
                self._is_compacting = False

        async for event in self.provider.generate_stream(history, tools_schema, config=config):
            yield event

    async def close(self):
        """Cleanup resources."""
        pass
