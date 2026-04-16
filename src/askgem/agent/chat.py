"""
Main autonomous agent logic module.

Manages the conversational loop, tool routing, and API interactions with the generative models.
It does NOT manage filesystem paths or raw terminal rendering.
"""

import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from google.genai import types

if TYPE_CHECKING:
    from ..cli.renderer import CliRenderer

from ..cli.console import console
from ..core.config_manager import ConfigManager
from ..core.history_manager import HistoryManager
from ..core.i18n import _
from ..core.identity_manager import KnowledgeManager
from ..core.metrics import TokenTracker
from .core.commands import CommandHandler
from .core.context import ContextManager
from .core.session import SessionManager
from .core.stream import StreamProcessor
from .orchestrator import AgentOrchestrator
from .schema import AgentTurnStatus, Message, Role
from .tools.base import ToolRegistry
from .tools.file_tools import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from .tools.memory_tool import MemoryTool
from .tools.search_tool import GlobFindTool, GrepSearchTool
from .tools.shell_tools import ShellTool
from .tools.web_tool import WebFetchTool, WebSearchTool

_logger = logging.getLogger("askgem")


class ChatAgent:
    """The central agent orchestrator.
    Coordinates session, context, streaming and commands.
    """

    def __init__(self, ui_adapter: Any | None = None):
        """Initializes the chat agent and its specialized managers."""
        self.running = False
        self.config = ConfigManager(console)
        self.history = HistoryManager(console)
        self.identity = KnowledgeManager()
        # Settings
        self.model_name = self.config.settings.get("model_name", "gemini-2.5-flash-lite")
        self.edit_mode = self.config.settings.get("edit_mode", "manual")
        # Managers
        self.session = SessionManager(self.config, self.model_name)
        self.session.metrics = TokenTracker(model_name=self.model_name)
        self.metrics = self.session.metrics
        self.context = ContextManager()
        self.stream_processor = StreamProcessor(self.metrics)
        self.commands = CommandHandler(self)

        # New Agentic System with Dynamic Config
        self.tools = ToolRegistry()
        self.tools.register(ListDirTool())
        self.tools.register(ReadFileTool(self.config))
        self.tools.register(WriteFileTool())
        self.tools.register(EditFileTool())
        self.tools.register(ShellTool(self.config))
        self.tools.register(MemoryTool())

        # New Search & Web Arsenal (v0.12.0)
        self.tools.register(GrepSearchTool())
        self.tools.register(GlobFindTool())

        if self.config.settings.get("web_search_enabled", True):
            self.tools.register(WebSearchTool(self.config))
            self.tools.register(WebFetchTool())

        self.orchestrator = AgentOrchestrator(self.session, self.tools, self.config)

        # Persistent messages for the session
        self.messages: list[Message] = []
        self._setup_system_prompt()

    def _setup_system_prompt(self):
        """Injects the core identity, project context, and behavioral rules."""
        # 1. Identity (from identity.md)
        base_identity = self.identity.read_identity()

        # 2. Project context (structure, memory, missions — from ContextManager)
        project_context = self.context.build_system_instruction()

        # 3. Temporal Awareness
        import datetime
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        day_name = now.strftime("%A")

        system_text = (
            f"{base_identity}\n\n"
            f"CURRENT_TIME: {timestamp} ({day_name})\n\n"
            f"{project_context}\n"
        )
        self.messages.append(Message(role=Role.SYSTEM, content=system_text))

        # Stats
        self.session_messages = 0
        self.session_tools = 0
        self.interrupted = False

    def set_status_logger(self, logger_func: Callable[[str], None]):
        """Sets the callback for real-time status/debug logging."""
        # TODO: Implement logging in the new AgentOrchestrator if needed
        pass

    def _build_config(self) -> types.GenerateContentConfig:
        """Helper to build consistent generation config."""
        tools_list = []
        schemas = self.tools.get_all_schemas()

        if schemas:
            tools_list = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=s["name"], description=s["description"], parameters=s["parameters"]
                        )
                        for s in schemas
                    ]
                )
            ]

        temp = self.config.settings.get("temperature", 0.7)

        return types.GenerateContentConfig(
            temperature=temp,
            tools=tools_list,
            system_instruction=self.context.build_system_instruction(),
        )

    async def setup_api(self, interactive: bool = True) -> bool:
        """Proxy for SessionManager setup."""
        return await self.session.setup_api(interactive)

    async def _stream_response(self, user_input: str, renderer: "CliRenderer") -> None:
        """Core logic: feeds input to orchestrator and updates UI."""
        config = self._build_config()

        async for event in self.orchestrator.run_query(
            user_input, self.messages, config=config, confirmation_callback=renderer.ask_confirmation
        ):
            event_type = event.get("type")
            status = event.get("status")

            if status == AgentTurnStatus.THINKING:
                pass
            elif status == AgentTurnStatus.EXECUTING:
                for tc in event.get("tool_calls", []):
                    renderer.print_tool_call(tc.name, tc.arguments)
            elif event_type == "thought":
                # Thoughts arrive before text — no Live active yet, safe to print directly
                renderer.print_thought(event["content"])
            elif event_type == "text":
                # Start Live on first text chunk, not before
                if not renderer._streaming:
                    renderer.start_stream()
                renderer.update_stream(event["content"])
            elif event_type == "tool_result":
                renderer.print_tool_result(not event["is_error"], event["content"])
            elif event_type == "metrics":
                u = event["usage"]
                self.metrics.add_usage(u.input_tokens, u.output_tokens)

    async def start(self) -> None:
        """Rich CLI entry point — streaming renderer with code blocks and think panels."""
        from rich.prompt import Confirm

        from .. import __version__
        from ..cli.renderer import CliRenderer
        # Workspace Initialization Check
        local_ws = Path.cwd() / ".askgem"
        global_config_dir = Path.home() / ".askgem"
        # Only ask if we are NOT in the global config dir itself
        # and no local workspace exists.
        if not local_ws.exists() and Path.cwd() != global_config_dir:
            console.print("\n[bold indigo]📁 PROJECT WORKSPACE[/bold indigo]")
            should_init = Confirm.ask(
                "No local workspace [dim](.askgem/)[/] detected. "
                "Initialize one for this project to isolate history and knowledge?",
                default=False
            )
            if should_init:
                local_ws.mkdir(parents=True, exist_ok=True)
                console.print(f"[success][✓] Workspace initialized at {local_ws}[/success]")

        # Load theme from settings
        current_theme = self.config.settings.get("theme", "indigo")
        renderer = CliRenderer(console, theme_name=current_theme)
        self.active_renderer = renderer  # Store ref for dynamic commands

        if not await self.setup_api():
            sys.exit(1)

        self.running = True

        # ── Restore Context ───────────────────────────────────────────
        history_data = None
        sessions = self.history.list_sessions()
        if sessions:
            history_data = self.history.load_session(sessions[-1])

        await self.session.ensure_session(self._build_config(), history=history_data)

        renderer.print_welcome(__version__, self.model_name, self.edit_mode)
        if history_data:
            renderer.print_warning(f"Resumed session: [bold]{sessions[-1]}[/bold] ({len(history_data)} turns)")

        while self.running:
            try:
                # ── Prompt ────────────────────────────────────────────
                try:
                    user_input = console.input("[bold #94a3b8]  ❯  [/]").strip()
                except EOFError:
                    break
                if not user_input:
                    continue

                # ── Slash commands ─────────────────────────────────────
                if user_input.startswith("/"):
                    if user_input.lower() in ("/exit", "/quit", "/q"):
                        self.running = False
                        break
                    result = await self.commands.execute(user_input)
                    renderer.print_command_output(result)
                    continue

                # ── Agent turn ─────────────────────────────────────────
                self.session_messages += 1
                renderer.print_user(user_input)  # Echo user input before agent starts

                try:
                    await self._stream_response(user_input, renderer)
                    renderer.end_stream()  # Finalize any active stream + structured render
                    renderer.print_metrics(self.metrics.get_summary())
                except KeyboardInterrupt:
                    renderer.end_stream()
                    renderer.print_warning("Generation interrupted.")
                except Exception as exc:
                    renderer.print_error(str(exc))
                finally:
                    renderer.print_turn_divider()

            except KeyboardInterrupt:
                self.running = False
                break

        renderer.print_goodbye(_("engine.shutdown"))

    def _save_history(self, chat_session: Any) -> None:
        """Safely extracts history from various session types and persists it."""
        try:
            if hasattr(chat_session, "get_history"):
                history = chat_session.get_history()
            else:
                history = getattr(chat_session, "history", [])

            if history:
                self.history.save_session(history)
        except Exception as e:
            _logger.error("Failed to extract history for saving: %s", e)
