"""
Main autonomous agent logic module.

Manages the conversational loop, tool routing, and API interactions with the generative models.
It does NOT manage filesystem paths or raw terminal rendering.
"""

import logging
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
from .tools.analysis_tools import AnalyzeTool
from .tools.base import ToolRegistry
from .tools.delegation_tools import SubagentTool
from .tools.file_tools import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from .tools.knowledge_tool import KnowledgeTool
from .tools.memory_tool import MemoryTool
from .tools.plan_tool import PlanTool
from .tools.plugin_tools import ForgePluginTool
from .tools.repl_tool import PythonReplTool
from .tools.search_tool import GlobFindTool, GrepSearchTool
from .tools.shell_tools import ShellTool
from .tools.user_tool import AskUserTool
from .tools.web_tool import WebFetchTool, WebSearchTool
from .tools.working_memory_tool import WorkingMemoryTool

_logger = logging.getLogger("mentask")


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

        from ..core.mcp_manager import MCPManager

        self.mcp = MCPManager(self.config)

        self.orchestrator = AgentOrchestrator(self.session, self.tools, self.config)

        self.messages: list[Message] = []
        self._setup_system_prompt()

        # Turn metrics tracking
        self.turn_tokens_prompt = 0
        self.turn_tokens_candidate = 0

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
        registry.register(AnalyzeTool())
        registry.register(ForgePluginTool(registry))
        registry.register(SubagentTool(self.session, registry, self.config))

        if self.config.settings.get("web_search_enabled", True):
            registry.register(WebSearchTool(self.config))
            registry.register(WebFetchTool())

        return registry

    async def initialize_mcp(self):
        """Connects to MCP servers and registers their tools."""
        try:
            await self.mcp.connect_all()
            mcp_tools = await self.mcp.get_all_tools()

            from .tools.mcp_tool import MCPToolWrapper

            for tool_info in mcp_tools:
                self.tools.register(MCPToolWrapper(self.mcp, tool_info))
                _logger.info(f"MCP Tool '{tool_info.name}' registered to agent.")
        except Exception as e:
            _logger.error(f"Failed to initialize MCP: {e}")

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
            renderer.show_thinking()
            return

        if status == AgentTurnStatus.COMPLETED:
            renderer.stop_thinking()
            return

        if status == AgentTurnStatus.EXECUTING:
            renderer.stop_thinking()
            if renderer._streaming:
                renderer.end_stream()

            # Print agent label with tool name for the new atomic prompt
            tool_calls = event.get("tool_calls", [])
            self.session_tools += len(tool_calls)
            tool_name = tool_calls[0].name if tool_calls else None
            renderer._print_agent_label(tool=tool_name)
            renderer._label_printed = True

            for tool_call in tool_calls:
                renderer.print_tool_call(tool_call.name, tool_call.arguments)
            return

        if event_type == "thought":
            renderer.stop_thinking()
            if renderer._streaming:
                renderer.end_stream()
            renderer.print_thought(event["content"])
            return

        if event_type == "text":
            renderer.stop_thinking()
            if not renderer._streaming:
                renderer.start_stream(is_natural=True)
            renderer.update_stream(event["content"])
            return

        if event_type == "tool_result":
            renderer.stop_thinking()
            renderer.print_tool_result(not event["is_error"], event["content"], tool_name=event.get("tool_name"))
            return

        if event_type == "metrics":
            usage = event["usage"]
            self.metrics.add_usage(usage.input_tokens, usage.output_tokens)
            self.turn_tokens_prompt += usage.input_tokens
            self.turn_tokens_candidate += usage.output_tokens
            return

        if event_type == "error":
            renderer.stop_thinking()
            renderer.print_error(event["content"])
            return

    def _maybe_initialize_workspace(self, confirm_ask: Callable[..., bool]) -> None:
        local_ws = Path.cwd() / ".mentask"
        global_config_dir = Path.home() / ".mentask"
        if local_ws.exists() or Path.cwd() == global_config_dir:
            return

        console.print("\n[bold indigo]📁 PROJECT WORKSPACE[/bold indigo]")
        should_init = confirm_ask(
            "No local workspace [dim](.mentask/)[/] detected. "
            "Initialize one for this project to isolate history and knowledge?",
            default=False,
        )
        if should_init:
            local_ws.mkdir(parents=True, exist_ok=True)
            console.print(f"[success][✓] Workspace initialized at {local_ws}[/success]")

    async def _ensure_trust(self, renderer: Any) -> None:
        """Prompts the user to trust the current directory if it's untrusted."""
        trust = self.orchestrator.trust
        cwd = os.getcwd()
        if trust.is_trusted(cwd):
            return

        renderer.console.print("\n  [bold yellow]󰚌 UNTRUSTED DIRECTORY[/bold yellow]")
        renderer.console.print(f"  The directory [cyan]{cwd}[/] is not trusted.")
        renderer.console.print("  Trusting allows the agent to execute tools without excessive confirmations.\n")

        choices = "[b]p[/b]ermanent, [b]s[/b]ession, [b]n[/b]o"
        prompt = f"  Trust this directory? ({choices}) [n]: "

        renderer.console.print(prompt, end="")
        try:
            # We use standard input here because prompt_toolkit session isn't ready yet
            choice = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = "n"

        if choice == "p":
            await trust.add_trust(cwd)
            renderer.console.print("  [green]✓ Directory trusted permanently.[/green]\n")
        elif choice == "s":
            trust.add_session_trust(cwd)
            renderer.console.print("  [green]✓ Directory trusted for this session.[/green]\n")
        else:
            renderer.console.print("  [dim]Directory remains untrusted.[/dim]\n")

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

        # Reset turn metrics
        self.turn_tokens_prompt = 0
        self.turn_tokens_candidate = 0

        try:
            await self._stream_response(user_input, renderer)
            if hasattr(renderer, "end_stream"):
                renderer.end_stream()

            # Compact turn metrics
            total_turn = self.turn_tokens_prompt + self.turn_tokens_candidate
            summary = f"{total_turn:,} tokens" if total_turn > 0 else ""
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
            renderer.stop_thinking()
            renderer.print_turn_divider(model=self.model_name)

    async def close(self):
        """Cleanup resources."""
        from ..core.process_tracker import tracker

        await tracker.kill_all()
        await self.orchestrator.executor.shutdown()
        await self.session.close()
        await self.mcp.shutdown()

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

        await self.initialize_mcp()

        self.running = True
        sessions, history_data, is_new_session = self._restore_last_session()

        await self.session.ensure_session(self._build_config(), history=None)

        renderer.print_welcome(__version__, self.model_name, self.edit_mode)
        await self._ensure_trust(renderer)

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
                with patch_stdout(raw=True):
                    renderer.expand_artifact(-1)

            from prompt_toolkit.completion import NestedCompleter

            from ..cli import themes

            # Build nested completion map
            completion_dict = {cmd: None for cmd in self.commands.get_all_commands()}

            # Add specific sub-commands
            completion_dict["/theme"] = {t: None for t in themes.THEMES}
            completion_dict["/mode"] = {"auto": None, "manual": None}
            completion_dict["/usage"] = {"--reset": None, "-r": None}
            completion_dict["/stream"] = {"transient": None, "continuous": None}

            # Dynamic prompt styles from engine
            styles = {s: None for s in renderer.prompt_engine.STYLES}
            completion_dict["/prompt"] = {"--theme": styles, "--nerdfonts": {"on": None, "off": None}}

            # For /model, we fetch available models from the provider for autocompletion
            models = await self.session.list_models()
            if models:
                completion_dict["/model"] = {m: None for m in models}
            else:
                completion_dict["/model"] = {self.model_name: None}

            completer = NestedCompleter.from_nested_dict(completion_dict)

            session = PromptSession(key_bindings=kb, completer=completer)
        else:
            renderer.print_warning(
                "Interactive features (Ctrl+O) disabled.\n"
                "  Install: [bold white]pip install prompt_toolkit[/bold white]"
            )

        while self.running:
            try:
                # Generate dynamic prompt
                style = self.config.settings.get("prompt_style", "atomic")
                renderer.prompt_style = style
                is_trusted = self.orchestrator.trust.is_trusted(os.getcwd())
                cost = self.metrics.calculate_cost(
                    self.metrics.total_prompt_tokens, self.metrics.total_candidate_tokens
                )

                user_prompt_rich = renderer.prompt_engine.build_user_prompt(style, os.getcwd(), is_trusted, cost)

                if HAS_PT:
                    from prompt_toolkit.formatted_text import ANSI

                    # Convert Rich to ANSI for prompt_toolkit
                    with renderer.console.capture() as capture:
                        renderer.console.print(user_prompt_rich, end="")
                    prompt_msg = ANSI(capture.get())

                    with patch_stdout():
                        try:
                            user_input = (await session.prompt_async(prompt_msg)).strip()
                        except (EOFError, KeyboardInterrupt):
                            break
                else:
                    try:
                        renderer.console.print(user_prompt_rich, end="")
                        user_input = input().strip()
                    except EOFError:
                        break

                if not user_input:
                    continue

                # Print the input for history/visibility (the renderer handles clearing the raw prompt)
                renderer.print_user(user_input, prompt_text=user_prompt_rich)

                # Check for slash commands
                if user_input.startswith("/"):
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
