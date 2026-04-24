"""
Main autonomous agent logic module.

Manages the conversational loop, tool routing, and API interactions with the generative models.
It does NOT manage filesystem paths or raw terminal rendering.
"""

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from google.genai import types

if TYPE_CHECKING:
    from ..cli.gem_renderer import GemStyleRenderer as CliRenderer

from ..cli.console import console
from ..core.config_manager import ConfigManager
from ..core.history_manager import HistoryManager
from ..core.i18n import _
from ..core.identity_manager import KnowledgeManager
from ..core.metrics import TokenTracker
from .core.commands import CommandHandler
from .core.context import ContextManager
from .core.session import SessionManager
from .orchestrator import AgentOrchestrator
from .schema import AgentTurnStatus, Message, Role
from .tools.base import ToolRegistry
from .tools.file_tools import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from .tools.knowledge_tool import KnowledgeTool
from .tools.memory_tool import MemoryTool
from .tools.plan_tool import PlanTool
from .tools.search_tool import GlobFindTool, GrepSearchTool
from .tools.shell_tools import ShellTool
from .tools.web_tool import WebFetchTool, WebSearchTool
from .tools.working_memory_tool import WorkingMemoryTool
from .tools.user_tool import AskUserTool
from .tools.repl_tool import PythonReplTool

_logger = logging.getLogger("askgem")


@dataclass(slots=True)
class ChatAgentDependencies:
    config: ConfigManager
    history: HistoryManager
    identity: KnowledgeManager
    context: ContextManager
    session: SessionManager | None = None
    tools: ToolRegistry | None = None

    @classmethod
    def create_default(cls) -> "ChatAgentDependencies":
        config = ConfigManager(console)
        return cls(
            config=config,
            history=HistoryManager(console),
            identity=KnowledgeManager(),
            context=ContextManager(),
        )


class ChatAgent:
    """The central agent orchestrator.
    Coordinates session, context, streaming and commands.
    """

    def __init__(
        self,
        ui_adapter: Any | None = None,
        dependencies: ChatAgentDependencies | None = None,
        session_id: str | None = None,
    ):
        """Initializes the chat agent and its specialized managers."""
        self.running = False
        self.requested_session_id = session_id  # Requested session ID (None = new)
        deps = dependencies or ChatAgentDependencies.create_default()
        self.config = deps.config
        self.history = deps.history
        self.identity = deps.identity

        self.model_name = self.config.settings.get("model_name", "gemini-2.5-flash-lite")
        self.edit_mode = self.config.settings.get("edit_mode", "manual")
        self.session = deps.session or SessionManager(self.config, self.model_name)
        self.session.metrics = getattr(self.session, "metrics", None) or TokenTracker(model_name=self.model_name)
        self.metrics = self.session.metrics
        self.context = deps.context
        self.commands = CommandHandler(self)

        self.tools = deps.tools or self._build_tool_registry()

        self.orchestrator = AgentOrchestrator(self.session, self.tools, self.config)

        # Persistent messages for the session
        self.messages: list[Message] = []
        self._setup_system_prompt()

    def _setup_system_prompt(self):
        """Injects the core identity, knowledge index, project context, and behavioral rules."""
        base_identity = self.identity.read_identity()
        knowledge_index = self.identity.get_knowledge_index()
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        day_name = now.strftime("%A")

        self.system_prompt = (
            f"{base_identity}\n\n"
            f"## KNOWLEDGE HUB INDEX\n"
            f"You have access to the following knowledge modules via 'query_knowledge(module_name=...)'.\n"
            f"Consult them if you need specific guidance on architecture, rules, or standards:\n"
            f"{knowledge_index}\n\n"
            f"CURRENT_TIME: {timestamp} ({day_name})\n"
        )

        self.session_messages = 0
        self.session_tools = 0
        self.interrupted = False

    def _build_tool_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(ListDirTool())
        registry.register(ReadFileTool(self.config))
        registry.register(WriteFileTool())
        registry.register(EditFileTool())
        registry.register(ShellTool(self.config))
        registry.register(MemoryTool())
        registry.register(WorkingMemoryTool())
        registry.register(PlanTool())
        registry.register(KnowledgeTool(self.identity))
        registry.register(GrepSearchTool())
        registry.register(GlobFindTool())
        registry.register(AskUserTool())
        registry.register(PythonReplTool())

        if self.config.settings.get("web_search_enabled", True):
            registry.register(WebSearchTool(self.config))
            registry.register(WebFetchTool())

        return registry

    def set_status_logger(self, logger_func: Callable[[str], None]):
        """Sets the callback for real-time status/debug logging."""
        self.orchestrator.status_callback = logger_func

    def _build_config(self) -> dict[str, Any]:
        """Builds a provider-agnostic configuration dictionary."""
        schemas = self.tools.get_all_schemas()
        temp = self.config.settings.get("temperature", 0.7)

        # Only include blueprint on the very first turn to save tokens
        is_first_turn = self.session_messages == 0
        full_instruction = (
            f"{self.system_prompt}\n\n{self.context.build_system_instruction(include_blueprint=is_first_turn)}"
        )

        return {
            "temperature": temp,
            "tools": schemas,
            "system_instruction": full_instruction,
        }

    async def setup_api(self, interactive: bool = True) -> bool:
        """Proxy for SessionManager setup."""
        return await self.session.setup_api(interactive)

    def _process_input(self, user_input: str) -> str | list[dict[str, Any]]:
        """Detects if input is a file path and converts to multimodal Parts."""
        path = Path(user_input.strip())
        if path.exists() and path.is_file():
            ext = path.suffix.lower()
            # Media extensions supported by Gemini 2.0+
            media_exts = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
                ".heic": "image/heic",
                ".heif": "image/heif",
                ".mp3": "audio/mpeg",
                ".wav": "audio/wav",
                ".ogg": "audio/ogg",
                ".mp4": "video/mp4",
                ".mov": "video/mov",
                ".avi": "video/avi",
            }
            if ext in media_exts:
                mime = media_exts[ext]
                # Read as bytes and wrap in inline_data Part
                import base64

                with open(path, "rb") as f:
                    b64_data = base64.b64encode(f.read()).decode("utf-8")

                return [
                    {"text": f"Analyzing file: {path.name}"},
                    {"inline_data": {"mime_type": mime, "data": b64_data}},
                ]
        return user_input

    async def _stream_response(self, user_input: str, renderer: "CliRenderer") -> None:
        """Core logic: feeds input to orchestrator and updates UI."""
        renderer.reset_turn()
        processed_input = self._process_input(user_input)
        config = self._build_config()

        async for event in self.orchestrator.run_query(
            processed_input, self.messages, config=config, confirmation_callback=renderer.ask_confirmation
        ):
            event_type = event.get("type")
            status = event.get("status")
            self._handle_stream_event(renderer, status, event_type, event)

    def _handle_stream_event(
        self, renderer: "CliRenderer", status: AgentTurnStatus | None, event_type: str | None, event: dict[str, Any]
    ) -> None:
        if status == AgentTurnStatus.THINKING:
            return

        if status == AgentTurnStatus.EXECUTING:
            if renderer._streaming:
                renderer.end_stream()
            for tool_call in event.get("tool_calls", []):
                renderer.print_tool_call(tool_call.name, tool_call.arguments)
            return

        if event_type == "thought":
            if renderer._streaming:
                renderer.end_stream()
            renderer.print_thought(event["content"])
            return

        if event_type == "text":
            if not renderer._streaming:
                renderer.start_stream()
            renderer.update_stream(event["content"])
            return

        if event_type == "tool_result":
            renderer.print_tool_result(not event["is_error"], event["content"], tool_name=event.get("tool_name"))
            return

        if event_type == "metrics":
            usage = event["usage"]
            self.metrics.add_usage(usage.input_tokens, usage.output_tokens)
            return

        if event_type == "error":
            renderer.print_error(event["content"])
            return

    def _maybe_initialize_workspace(self, confirm_ask: Callable[..., bool]) -> None:
        local_ws = Path.cwd() / ".askgem"
        global_config_dir = Path.home() / ".askgem"
        if local_ws.exists() or Path.cwd() == global_config_dir:
            return

        console.print("\n[bold indigo]📁 PROJECT WORKSPACE[/bold indigo]")
        should_init = confirm_ask(
            "No local workspace [dim](.askgem/)[/] detected. "
            "Initialize one for this project to isolate history and knowledge?",
            default=False,
        )
        if should_init:
            local_ws.mkdir(parents=True, exist_ok=True)
            console.print(f"[success][✓] Workspace initialized at {local_ws}[/success]")

    def _restore_last_session(self) -> tuple[list[str], list[Message] | None, bool]:
        """Restores session history.

        Creates a NEW session by default unless a specific session_id is requested.

        Returns:
            tuple: (all_sessions, history_data, is_new_session)
        """
        history_data = None
        is_new = True
        sessions = self.history.list_sessions()

        # If a specific session_id was requested, load it
        if self.requested_session_id and self.requested_session_id in sessions:
            history_data = self.history.load_session(self.requested_session_id)
            self.history.current_session_id = self.requested_session_id
            is_new = False
            # else: session doesn't exist, create new (is_new stays True)
        # If no session_id requested: always create NEW (don't auto-resume)
        # User must explicitly provide session_id to resume

        if history_data:
            self.messages.extend([message for message in history_data if message.role != Role.SYSTEM])

        return sessions, history_data, is_new

    async def _handle_command_input(self, user_input: str, renderer: "CliRenderer") -> bool:
        if not user_input.startswith("/"):
            return False

        if user_input.lower() in ("/exit", "/quit", "/q"):
            self.running = False
            return True

        result = await self.commands.execute(user_input)
        renderer.print_command_output(result)
        return True

    async def _handle_user_turn(self, user_input: str, renderer: "CliRenderer") -> None:
        self.session_messages += 1
        renderer.reset_turn()
        renderer.print_user(user_input)

        try:
            await self._stream_response(user_input, renderer)
            if hasattr(renderer, "end_stream"):
                renderer.end_stream()
            # Pass summary string directly to renderer divider instead of calling metrics.get_summary()
            summary = self.metrics.get_summary()
            renderer.print_metrics(summary)
            self._save_history()
        except KeyboardInterrupt:
            # Check if stream is active before ending
            if renderer._streaming and hasattr(renderer, "end_stream"):
                renderer.end_stream()
            renderer.print_warning("Generation interrupted.")
        except Exception as exc:
            renderer.print_error(str(exc))
        finally:
            renderer.print_turn_divider()

    async def close(self):
        """Cleanup resources."""
        await self.session.close()

    async def start(self) -> None:
        """Rich CLI entry point — streaming renderer with code blocks and think panels."""
        from rich.prompt import Confirm

        from .. import __version__
        from ..cli.gem_renderer import GemStyleRenderer

        # Try to import prompt_toolkit for interactive features
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.key_binding import KeyBindings
            from prompt_toolkit.patch_stdout import patch_stdout

            HAS_PT = True
        except ImportError:
            HAS_PT = False

        self._maybe_initialize_workspace(Confirm.ask)

        current_theme = self.config.settings.get("theme", "indigo")
        stream_delay = self.config.settings.get("stream_delay", 0.015)
        renderer = GemStyleRenderer(console, theme_name=current_theme, stream_delay=stream_delay)
        self.active_renderer = renderer
        self.set_status_logger(renderer.print_status)

        if not await self.setup_api():
            sys.exit(1)

        self.running = True
        sessions, history_data, is_new_session = self._restore_last_session()

        await self.session.ensure_session(self._build_config(), history=None)

        renderer.print_welcome(__version__, self.model_name, self.edit_mode)

        if not is_new_session:
            res_id = self.requested_session_id or sessions[-1]
            renderer.print_warning(
                f"Resumed session: [bold]{res_id}[/bold] ({len(history_data) if history_data else 0} turns)"
            )
        else:
            renderer.print_warning(f"New session: [bold]{self.history.current_session_id}[/bold]")

        # Setup prompt_toolkit if available
        if HAS_PT:
            kb = KeyBindings()

            @kb.add("c-o")
            def _expand_last(event):
                """Expand the last tool artifact on Ctrl+O."""
                with patch_stdout():
                    renderer.expand_artifact(-1)

            session = PromptSession(key_bindings=kb)
        else:
            renderer.print_warning(
                "Interactive features (Ctrl+O) disabled.\n"
                "  Install: [bold white]pip install prompt_toolkit[/bold white]"
            )

        while self.running:
            try:
                if HAS_PT:
                    with patch_stdout():
                        try:
                            user_input = (await session.prompt_async("  >  ")).strip()
                        except (EOFError, KeyboardInterrupt):
                            break
                else:
                    try:
                        user_input = console.input("[bold #94a3b8]  >  [/]").strip()
                    except EOFError:
                        break

                if not user_input:
                    continue

                handled = await self._handle_command_input(user_input, renderer)
                if handled:
                    continue

                await self._handle_user_turn(user_input, renderer)
            except KeyboardInterrupt:
                self.running = False
                break

        self._save_history()
        await self.close()
        renderer.print_goodbye(_("engine.shutdown"), session_id=self.history.current_session_id)

    def _save_history(self) -> None:
        """Persists the current Orchestrator messages to disk."""
        try:
            if self.messages:
                self.history.save_session(self.messages)
        except Exception as e:
            _logger.error("Failed to save history: %s", e)

    async def compress_history(self) -> str:
        """Summarizes conversation history to save tokens."""
        from ..core.summarizer import Summarizer

        if len(self.messages) < 10:
            return "Conversation too short to compress."

        # Keep last 4 messages (2 turns)
        to_summarize = self.messages[:-4]
        to_keep = self.messages[-4:]

        temp_history = [Message(role=Role.USER, content=Summarizer.BASE_SUMMARIZATION_PROMPT)]
        temp_history.extend(to_summarize)

        summary_text = ""
        async for event in self.orchestrator.provider.stream_turn(temp_history, [], config=self._build_config()):
            if event["type"] == "text":
                summary_text += event["content"]
            elif event["type"] == "metrics":
                usage = event["usage"]
                self.metrics.add_usage(usage.input_tokens, usage.output_tokens)

        formatted = Summarizer.format_summary(summary_text)
        summary_message = Message(role=Role.SYSTEM, content=Summarizer.get_user_continuation_message(formatted))

        self.messages = [summary_message] + to_keep
        return f"Compressed {len(to_summarize)} messages into a summary."
