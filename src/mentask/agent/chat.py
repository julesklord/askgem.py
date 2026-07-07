"""
Main autonomous agent logic module.

Manages the conversational loop, tool routing, and API interactions with the generative models.
It does NOT manage filesystem paths or raw terminal rendering.
"""

import logging
import os
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from ..cli.console import console
from ..cli.contextual_prompts import (
    ContextType,
    ContextualConfigManager,
    ContextualOrchestrator,
    ContextualPromptLibrary,
)
from ..cli.prompts import PromptContext
from ..core.config_manager import ConfigManager
from ..core.exceptions import ProviderError
from ..core.history_manager import HistoryManager
from ..core.i18n import _
from ..core.identity_manager import KnowledgeManager
from ..core.metrics import TokenTracker
from .core.commands import CommandHandler
from .core.context import ContextManager
from .core.session import SessionManager
from .orchestrator import AgentOrchestrator
from .schema import (
    AgentEvent,
    AgentTurnStatus,
    EventSink,
    Message,
    Role,
    StatusEvent,
    TextChunkEvent,
    ThoughtEvent,
    ToolCallEvent,
    ToolResult,
    ToolResultEvent,
)
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
from .tools.worktree_tools import EnterWorktreeTool, ExitWorktreeTool

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
        local_mode: bool = False,
    ):
        """Initializes the chat agent and its specialized managers."""
        self.running = False
        self.requested_session_id = session_id  # Requested session ID (None = new)
        self.local_mode = local_mode
        self._listeners: list[Any] = []
        deps = dependencies or ChatAgentDependencies.create_default()
        self.config = deps.config
        self.history = deps.history
        self.identity = deps.identity

        self.model_name = self.config.settings.get("model_name", "gemini-2.0-flash-lite")

        # In local mode, force a local model and persist flag in settings
        if self.local_mode:
            self.config.settings["local_mode"] = True
            if not any(x in self.model_name.lower() for x in ["ollama", "local", "lms"]):
                self.model_name = "ollama:qwen3.5"

        self.edit_mode = self.config.settings.get("edit_mode", "manual")
        self.session = deps.session or SessionManager(self.config, self.model_name)

        # Security: If local_mode is active, ensure we didn't accidentally pick a cloud provider
        if self.local_mode:
            from .core.providers.gemma import GemmaProvider
            from .core.providers.ollama import OllamaProvider

            if not isinstance(self.session.provider, (OllamaProvider, GemmaProvider)):
                # Re-initialize session with forced local provider if factory failed
                self.model_name = "ollama:qwen3.5"
                self.session = SessionManager(self.config, self.model_name)

        self.session.metrics = getattr(self.session, "metrics", None)
        if self.session.metrics is None:
            self.session.metrics = TokenTracker(model_name=self.model_name)
        self.metrics = self.session.metrics
        self.context = deps.context
        self.commands = CommandHandler(self)

        self.tools = deps.tools or self._build_tool_registry()

        from ..core.mcp_manager import MCPManager

        self.mcp = MCPManager(self.config)

        self.orchestrator = AgentOrchestrator(self.session, self.tools, self.config)

        # Contextual System
        self.contextual_config = ContextualConfigManager()
        self.contextual_orchestrator = ContextualOrchestrator(self.contextual_config, console)

        self.messages: list[Message] = []
        self._setup_system_prompt()

        # Turn metrics tracking
        self.turn_tokens_prompt = 0
        self.turn_tokens_candidate = 0
        self.is_new_session = True

        # Autocompletion
        self._completer = None
        from ..cli.interactive_shell import InteractiveShell
        self.interactive_shell = InteractiveShell(self.config)

    def _verify_model_for_mode(self, model_name: str) -> bool:
        """Ensures the selected model is allowed in the current mode."""
        if not self.local_mode:
            return True

        is_local = any(x in model_name.lower() for x in ["ollama", "local", "lms", "127.0.0.1", "localhost"])
        return is_local

    def _setup_system_prompt(self):
        """Injects the core identity, knowledge index, project context, and behavioral rules."""
        base_identity = self.identity.read_identity()
        knowledge_index = self.identity.get_knowledge_index()
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        day_name = now.strftime("%A")

        # Detect model family
        model_id = self.model_name.lower()
        model_family = "claude" if "claude" in model_id else "gpt" if "gpt" in model_id else "groq"

        contextual_prompt = self.contextual_orchestrator.prepare_system_prompt(model_family)

        self.system_prompt = (
            f"{contextual_prompt}\n\n"
            f"{base_identity}\n\n"
            f"## KNOWLEDGE HUB INDEX\n"
            f"You have access to the following knowledge modules via 'query_knowledge(module_name=...)'.\n"
            f"Consult them if you need specific guidance on architecture, rules, or standards:\n"
            f"{knowledge_index}\n\n"
            f"CURRENT_TIME: {timestamp} ({day_name})\n"
        )

        if self.config.settings.get("readonly_mode", False):
            self.system_prompt += (
                "\n## READ-ONLY MODE ACTIVE\n"
                "You are currently in a restricted READ-ONLY mode. Your primary goal is to analyze, read, and explore.\n"
                "- DO NOT modify, delete, or overwrite any existing files or directories.\n"
                "- You ARE permitted to create NEW files if they are necessary for your analysis or to provide the requested output (e.g., creating a report, a scratchpad, or a new script as requested).\n"
                "- If you need to suggest changes to existing code, provide them in your response or in a new file, but DO NOT apply them to the original files.\n"
            )

        self.session_messages = 0
        self.session_tools = 0
        self.session_files = 0
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
        registry.register(EnterWorktreeTool())
        registry.register(ExitWorktreeTool())

        from .tools.git_tools import GitCommitTool

        registry.register(GitCommitTool())

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

    def _build_config(self, relevant_memory: str = "") -> dict[str, Any]:
        """Builds a provider-agnostic configuration dictionary."""
        schemas = self.tools.get_all_schemas()
        temp = self.config.settings.get("temperature", 0.7)

        # Only include blueprint on the very first turn to save tokens
        # For CLI Bridge: first turn of a NEW session needs --session-id, otherwise --resume
        is_first_turn = self.is_new_session and self.session_messages == 1
        full_instruction = f"{self.system_prompt}\n\n{self.context.build_system_instruction(include_blueprint=self.session_messages <= 1, relevant_memory=relevant_memory)}"

        return {
            "temperature": temp,
            "tools": schemas,
            "system_instruction": full_instruction,
            "session_id": self.history.current_session_id,
            "is_first_turn": is_first_turn,
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

    def register_listener(self, listener: Any) -> None:
        """Registers a callback listener for agent events."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unregister_listener(self, listener: Any) -> None:
        """Unregisters a callback listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def dispatch_event(self, event: AgentEvent) -> None:
        """Dispatches an AgentEvent to all registered listeners."""
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                _logger.error(f"Error in agent event listener: {e}")

    async def stream_response(self, user_input: str) -> AsyncGenerator[AgentEvent, None]:
        """Exposes a clean, structured, typed agent event stream decoupled from UI rendering."""
        processed_input = self._process_input(user_input)

        relevant_memory = ""
        if self.session_messages > 0 or self.local_mode:
            relevant_memory = await self.context.get_relevant_context(user_input, self.orchestrator)

        config = self._build_config(relevant_memory=relevant_memory)

        async for event in self.orchestrator.run_query(
            processed_input, self.messages, config=config
        ):
            event_type = event.get("type")
            status = event.get("status")

            if status:
                status_enum = AgentTurnStatus(status)
                status_event = StatusEvent(status=status_enum, message=event.get("content"))
                self.dispatch_event(status_event)
                yield status_event

                if status_enum == AgentTurnStatus.EXECUTING:
                    tool_calls = event.get("tool_calls", [])
                    self.session_tools += len(tool_calls)
                    for tc in tool_calls:
                        tc_event = ToolCallEvent(tool_call=tc)
                        self.dispatch_event(tc_event)
                        yield tc_event

            elif event_type == "thought":
                thought_event = ThoughtEvent(content=event["content"])
                self.dispatch_event(thought_event)
                yield thought_event

            elif event_type == "text":
                text_event = TextChunkEvent(content=event["content"])
                self.dispatch_event(text_event)
                yield text_event

            elif event_type == "tool_result":
                is_success = not event.get("is_error", False)
                tool_name = event.get("tool_name", "")
                if is_success and tool_name in ("write_file", "edit_file"):
                    self.session_files += 1
                res = ToolResult(
                    tool_call_id=event.get("tool_call_id", ""),
                    content=event.get("content", ""),
                    is_error=event.get("is_error", False)
                )
                res_event = ToolResultEvent(result=res)
                self.dispatch_event(res_event)
                yield res_event

            elif event_type == "metrics":
                usage = event["usage"]
                self.metrics.add_usage(usage.input_tokens, usage.output_tokens)
                self.turn_tokens_prompt += usage.input_tokens
                self.turn_tokens_candidate += usage.output_tokens

    async def _stream_response(self, user_input: str, renderer: EventSink) -> None:
        """Consumes the decoupled stream_response and updates the CLI renderer."""
        renderer.reset_turn()
        async for event in self.stream_response(user_input):
            if isinstance(event, StatusEvent):
                if event.status == AgentTurnStatus.THINKING:
                    renderer.show_thinking()
                elif event.status == AgentTurnStatus.COMPLETED:
                    renderer.stop_thinking()
                elif event.status == AgentTurnStatus.EXECUTING:
                    renderer.stop_thinking()
                    if renderer._streaming:
                        renderer.end_stream()
            elif isinstance(event, ToolCallEvent):
                renderer._print_agent_label(tool=event.tool_call.name)
                renderer._label_printed = True
                renderer.print_tool_call(event.tool_call.name, event.tool_call.arguments)
            elif isinstance(event, ThoughtEvent):
                renderer.stop_thinking()
                if renderer._streaming:
                    renderer.end_stream()
                renderer.print_thought(event.content)
            elif isinstance(event, TextChunkEvent):
                renderer.stop_thinking()
                if not renderer._streaming:
                    renderer.start_stream(is_natural=True)
                renderer.update_stream(event.content)
            elif isinstance(event, ToolResultEvent):
                renderer.stop_thinking()
                is_success = not event.result.is_error
                renderer.print_tool_result(is_success, event.result.content, tool_name="")

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
            from mentask.core.paths import ensure_dir
            ensure_dir(local_ws)
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
            raw_choice = input().strip().lower()
            # Normalize single letter or full word
            if raw_choice.startswith("p"):
                choice = "p"
            elif raw_choice.startswith("s") or raw_choice.startswith("y"):
                choice = "s"
            else:
                choice = "n"
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

    async def _restore_last_session(self) -> tuple[list[str], list[Message] | None, bool]:
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
            history_data = await self.history.load_session(self.requested_session_id)
            self.history.current_session_id = self.requested_session_id
            is_new = False
            # else: session doesn't exist, create new (is_new stays True)
        # If no session_id requested: always create NEW (don't auto-resume)
        # User must explicitly provide session_id to resume

        if history_data:
            self.messages.extend([message for message in history_data if message.role != Role.SYSTEM])
            # Restore model from last AssistantMessage if available
            from .schema import AssistantMessage

            for msg in reversed(history_data):
                if isinstance(msg, AssistantMessage) and getattr(msg, "model", ""):  # type: ignore[arg-type]
                    saved_model = msg.model
                    _logger.info(f"Session resume: restoring model '{saved_model}'")
                    self.model_name = saved_model
                    self.config.settings["model_name"] = saved_model
                    break
            else:
                # Fallback: check metadata on regular messages
                for msg in reversed(history_data):
                    m = (msg.metadata or {}).get("session_model")
                    if m:
                        self.model_name = m
                        self.config.settings["model_name"] = m
                        _logger.info(f"Session resume: restoring model from metadata '{m}'")
                        break

        return sessions, history_data, is_new

    async def _handle_command_input(self, user_input: str, renderer: EventSink) -> bool:
        if not user_input.startswith("/"):
            return False

        cmd = user_input.lower().split()[0]

        if cmd in ("/exit", "/quit", "/q"):
            self.running = False
            return True

        if cmd == "/context":
            self.show_context_menu()
            return True

        if cmd == "/theme":
            # Pass to CommandHandler for standard theme switching
            pass

        if cmd == "/info":
            self.show_context_info()
            return True

        if cmd in ("/stats", "/cost"):
            # Minimalist stats
            stats = {
                "context": self.contextual_config.get_active_context().value,
                "model": self.model_name,
            }
            # Format manually to avoid NeonRenderer dependency
            renderer.console.print(f"\n  [bold {renderer.C_BRAND}]STATS[/]")
            renderer.console.print(f"  [dim]Context:[/] {stats['context']}")
            renderer.console.print(f"  [dim]Model:[/]   {stats['model']}")
            renderer.console.print()
            return True

        result = await self.commands.execute(user_input)
        renderer.print_command_output(result)

        if cmd in ("/model", "/auth"):
            # Check if model is allowed in current mode
            if cmd == "/model":
                parts = user_input.split()
                if len(parts) > 1:
                    target_model = parts[1]
                    if not self._verify_model_for_mode(target_model):
                        renderer.print_error(
                            f"Cannot switch to '{target_model}' in LOCAL MODE. Only local models are allowed."
                        )
                        return True

            await self._update_completer()

        return True

    def show_context_menu(self) -> None:
        """Interactive menu to select context."""
        from rich.panel import Panel
        from rich.prompt import Prompt

        self.active_renderer.console.print("\n")
        self.active_renderer.console.print(
            Panel(
                "[bold]Select your working context[/bold]\n"
                + "1. 🧑‍💻 Coding (Software engineering)\n"
                + "2. 🎵 Music Production (Music production)\n"
                + "3. 📊 Analysis (Data analysis)\n"
                + "4. 🎨 Creative (Creative)\n"
                + "5. 💬 General (General)",
                title="[bold cyan]Available Contexts[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

        choice = Prompt.ask("[cyan]Select context[/cyan]", choices=["1", "2", "3", "4", "5"], default="5")

        context_map = {
            "1": ContextType.CODING,
            "2": ContextType.MUSIC_PRODUCTION,
            "3": ContextType.ANALYSIS,
            "4": ContextType.CREATIVE,
            "5": ContextType.GENERAL,
        }

        selected = context_map[choice]
        self.contextual_config.set_context(selected)
        self._setup_system_prompt()  # Refresh system prompt
        renderer = self.active_renderer
        renderer.console.print(f"\n  [bold {renderer.C_SUCCESS}]✓[/] Context changed to {selected.value}\n")

    def show_context_info(self) -> None:
        """Displays current context info."""
        from rich.panel import Panel

        context = self.contextual_config.get_active_context()
        prompt = ContextualPromptLibrary.get(context)

        self.active_renderer.console.print()
        self.active_renderer.console.print(
            Panel(
                f"[bold cyan]{prompt.context.value.upper()}[/bold cyan]\n\n"
                f"[yellow]Tone:[/yellow] {prompt.tone}\n"
                f"[yellow]Constraints:[/yellow]\n" + "\n".join(f"  • {c}" for c in prompt.constraints),
                title="[bold]Context Details[/bold]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        self.active_renderer.console.print()

    async def _handle_user_turn(self, user_input: str, renderer: EventSink) -> None:
        self.session_messages += 1
        renderer.reset_turn()

        # Reset turn metrics
        self.turn_tokens_prompt = 0
        self.turn_tokens_candidate = 0

        try:
            await self._stream_response(user_input, renderer)
            # Guard against double end_stream: _handle_stream_event may have already
            # called it (e.g. on EXECUTING transition mid-turn).
            if hasattr(renderer, "end_stream") and renderer._streaming:
                renderer.end_stream()

            # Compact turn metrics
            total_turn = self.turn_tokens_prompt + self.turn_tokens_candidate
            summary = f"{total_turn:,} tokens" if total_turn > 0 else ""
            renderer.print_metrics(summary)

            # Update status bar data before each turn
            cost = self.metrics.calculate_cost(self.metrics.total_prompt_tokens, self.metrics.total_candidate_tokens)
            renderer.update_status_bar(
                model=self.model_name,
                tokens=self.metrics.total_prompt_tokens + self.metrics.total_candidate_tokens,
                cost=cost,
            )

            # Unify status bar and divider into one call
            renderer.print_turn_divider(model=self.model_name)

            await self._save_history()
        except KeyboardInterrupt:
            # Check if stream is active before ending
            if renderer._streaming and hasattr(renderer, "end_stream"):
                renderer.end_stream()
            renderer.print_warning("Generation interrupted.")
        except Exception as exc:
            renderer.print_error(str(exc))
        finally:
            renderer.stop_thinking()

    async def close(self):
        """Cleanup resources."""
        from ..core.process_tracker import tracker

        await tracker.kill_all()
        await self.orchestrator.executor.shutdown()
        await self.session.close()
        await self.mcp.shutdown()

    async def _update_completer(self):
        """Dynamically updates the autocompletion NestedCompleter with all model sources."""
        return await self.interactive_shell.update_completer(self)

    async def start(self) -> None:
        """Rich CLI entry point — streaming renderer with code blocks and think panels."""
        from rich.prompt import Confirm

        from .. import __version__
        from ..cli.gem_renderer import GemStyleRenderer

        self._maybe_initialize_workspace(Confirm.ask)

        current_theme = self.config.settings.get("theme", "indigo")
        stream_delay = self.config.settings.get("stream_delay", 0.015)
        nf_enabled = self.config.settings.get("nerdfonts_enabled", True)
        renderer = GemStyleRenderer(
            console, theme_name=current_theme, stream_delay=stream_delay, use_nerdfonts=nf_enabled
        )
        renderer.show_thinking_details = self.config.settings.get("show_thinking", True)
        self.active_renderer = renderer
        self.set_status_logger(renderer.print_status)

        if not await self.setup_api():
            raise ProviderError("Failed to configure API provider. Run without --local or configure credentials.")

        await self.initialize_mcp()

        self.running = True
        original_model = self.model_name
        sessions, history_data, is_new_session = await self._restore_last_session()
        self.is_new_session = is_new_session

        # If session resume changed the model, re-init the provider with the restored model
        if not is_new_session and self.model_name != original_model:
            _logger.info(f"Re-initializing provider for restored model: {self.model_name}")
            await self.session.switch_model(self.model_name)

        await self.session.ensure_session(self._build_config(), history=None)
        await self.orchestrator.executor.initialize()

        if is_new_session:
            renderer.print_splash_screen()
        renderer.print_welcome(__version__, self.model_name, self.edit_mode)
        await self._ensure_trust(renderer)

        if not is_new_session:
            res_id = self.requested_session_id or sessions[-1]
            renderer.print_warning(
                f"Resumed session: [bold]{res_id}[/bold] ({len(history_data) if history_data else 0} turns)"
            )
            if history_data:
                renderer.replay_history(history_data)
        else:
            renderer.print_warning(f"New session: [bold]{self.history.current_session_id}[/bold]")

        # Setup interactive shell
        if self.interactive_shell.has_interactive_features:
            # Initialize completer with dynamic data
            if self.local_mode:
                from ..core.models_hub import hub

                hub.sync_local(config=self.config)
                if not hub._local_models:
                    renderer.console.print("\n  [bold yellow]󰚌 OLLAMA NOT DETECTED[/bold yellow]")
                    renderer.console.print(
                        "  Local mode is active but no Ollama models were found at http://localhost:11434."
                    )
                    renderer.console.print("\n  [bold]How to fix this:[/bold]")
                    renderer.console.print("  1. [cyan]Install Ollama:[/] Download from https://ollama.com")
                    renderer.console.print("  2. [cyan]Start the server:[/] Run 'ollama serve' or open the app")
                    renderer.console.print(
                        "  3. [cyan]Pull a model:[/] Run 'ollama pull llama3' (or your preferred model)"
                    )
                    renderer.console.print(
                        "\n  [dim]MentAsk will try to reconnect automatically when you switch models.[/dim]\n"
                    )

            await self._update_completer()
        else:
            renderer.print_warning(
                "Interactive features disabled.\n  Install: [bold white]pip install prompt_toolkit[/bold white]"
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

                prompt_context = PromptContext(
                    style_name=style, cwd=os.getcwd(), is_trusted=is_trusted, cost=cost, model_id=self.model_name
                )
                user_prompt_rich = renderer.prompt_engine.build_user_prompt(prompt_context)

                # Update status bar data before each turn
                renderer.update_status_bar(
                    model=self.model_name,
                    mode=self.edit_mode,
                    tokens=self.metrics.total_prompt_tokens + self.metrics.total_candidate_tokens,
                    cost=cost,
                )

                if self.interactive_shell.has_interactive_features:
                    from prompt_toolkit.formatted_text import ANSI

                    # Convert Rich to ANSI for prompt_toolkit
                    with renderer.console.capture() as capture:
                        renderer.console.print(user_prompt_rich, end="")
                    prompt_msg = ANSI(capture.get())

                    try:
                        is_multiline = self.config.settings.get("multiline_prompt", False)
                        user_input = await self.interactive_shell.prompt_user(prompt_msg, is_multiline=is_multiline)
                    except KeyboardInterrupt:
                        break
                else:
                    try:
                        renderer.console.print(user_prompt_rich, end="")
                        user_input = input().strip()
                    except (EOFError, KeyboardInterrupt):
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

        await self._save_history()
        await self.close()
        renderer.print_goodbye(_("engine.shutdown"), session_id=self.history.current_session_id)

    async def _save_history(self) -> None:
        """Persists the current Orchestrator messages to disk asynchronously."""
        try:
            if self.messages:
                await self.history.save_session(self.messages)
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
