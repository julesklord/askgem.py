"""
Main autonomous agent logic module.

Manages the conversational loop, tool routing, and API interactions with the generative models.
It does NOT manage filesystem paths or raw terminal rendering.
"""

import asyncio
import logging
import os
import platform
import sys
from typing import Callable, List, Optional, Union

from google import genai
from google.genai import types
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table

from ..cli.console import console
from ..core.config_manager import ConfigManager
from ..core.history_manager import HistoryManager
from ..core.i18n import _
from ..core.memory_manager import MemoryManager
from ..core.metrics import TokenTracker
from ..core.mission_manager import MissionManager
from ..core.paths import get_config_dir
from .tools_registry import ToolDispatcher

# Debug logger — writes to ~/.askgem/askgem.log so silent SDK failures
# leave a trace without crashing the streaming UI.
_log_path = os.path.join(str(get_config_dir()), "askgem.log")
logging.basicConfig(
    filename=_log_path,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_logger = logging.getLogger("askgem")

_RETRYABLE_KEYWORDS = (
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


class ChatAgent:
    """The central agent session manager handling interaction loops and tools."""

    def __init__(self):
        """Initializes the chat agent, loading defaults and instantiating managers."""
        self.running = False
        self.config = ConfigManager(console)
        self.history = HistoryManager(console)
        self.memory = MemoryManager()
        self.mission = MissionManager()
        self.client = None
        self.chat_session = None

        # Load persisted settings
        self.model_name = self.config.settings.get("model_name", "gemini-2.5-pro")
        self.edit_mode = self.config.settings.get("edit_mode", "manual")

        # Centralized tool dispatcher & Milestone 2/3 registration
        self.dispatcher = ToolDispatcher(
            config=self.config,
            logger=None,  # Will be set by Dashboard
        )

        # Milestone 4: Metrics engine
        self.metrics = TokenTracker(model_name=self.model_name)
        self.session_messages = 0
        self.session_tools = 0
        self.interrupted = False

    def set_status_logger(self, logger_func: Callable[[str], None]):
        """Sets the callback for real-time status/debug logging.
        
        Args:
            logger_func: A callable that accepts a string to log status updates.
        """

    # ------------------------------------------------------------------ #
    # Setup                                                                #
    # ------------------------------------------------------------------ #

    async def setup_api(self, interactive: bool = True) -> bool:
        """Loads and validates the Google API key (Async).

        Args:
            interactive: If False, skips interactive console prompts for missing keys.

        Returns:
            bool: True if the client was successfully initialized, False otherwise.
        """
        api_key = self.config.load_api_key()

        if not api_key:
            if not interactive:
                _logger.error("API key missing in non-interactive mode.")
                return False

            console.print(f"\n[error]{_('api.missing')}[/error]")
            # Note: Prompt.ask is blocking, but in Dashboard we will use TUI input.
            # In legacy CLI, it's fine for now.
            api_key = Prompt.ask(f"[google.blue]{_('api.prompt')}[/google.blue]").strip()

            if not api_key:
                console.print(f"[error][X] {_('api.fatal')}[/error]")
                return False

            save_choice = Prompt.ask(_("api.save")).strip().lower()
            if save_choice != "n":
                self.config.save_api_key(api_key)

        # Milestone 4.1: Use AsyncClient for TUI responsive streaming
        self.client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
        return True

    def _build_config(self) -> types.GenerateContentConfig:
        """Assembles the model config including live OS context and persistent memory.

        Returns:
            types.GenerateContentConfig: The SDK config payload for generation.
        """
        # Base context from localization files
        base_context = _("sys.context", os=f"{platform.system()} {platform.release()}", cwd=os.getcwd())

        # Load persistent memory and active missions
        memory_content = self.memory.read_memory()
        mission_content = self.mission.read_missions()

        full_instruction = f"{base_context}\n\n"
        full_instruction += "## INFORMACIÓN DE MEMORIA PERSISTENTE (memory.md)\n"
        full_instruction += f"{memory_content}\n\n"
        full_instruction += "## MISIONES Y TAREAS ACTIVAS (heartbeat.md)\n"
        full_instruction += f"{mission_content}\n\n"
        full_instruction += "INSTRUCCIÓN CRÍTICA: Usa 'manage_memory' para guardar hechos importantes y 'manage_mission' para rastrear tu progreso."

        return types.GenerateContentConfig(
            temperature=0.7,
            tools=self.dispatcher.get_tools_list(),
            system_instruction=full_instruction,
        )

    # ------------------------------------------------------------------ #
    # Core response loop                                                 #
    # ------------------------------------------------------------------ #

    def _extract_function_calls(
        self, chunk: types.Part, seen_calls: set
    ) -> List[types.FunctionCall]:
        """Extracts unique function calls from a streaming response chunk.

        Handles both standard SDK properties and candidate parts fallbacks for various
        SDK versions.

        Args:
            chunk (types.Part): The chunk received from the stream.
            seen_calls (set): A set of (name, args) tuples to prevent duplicate execution.

        Returns:
            List[types.FunctionCall]: A list of newly discovered function calls.
        """
        found = []

        # --- Primary detection: SDK aggregated helper property ---
        try:
            for fc in chunk.function_calls or []:
                key = (fc.name, str(sorted(fc.args.items()) if fc.args else []))
                if key not in seen_calls:
                    seen_calls.add(key)
                    found.append(fc)
        except (AttributeError, TypeError) as _sdk_err:
            _logger.debug("SDK function_calls property not present or malformed in chunk: %s", _sdk_err)

        # --- Fallback detection: direct candidate parts traversal ---
        try:
            for candidate in chunk.candidates or []:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", []) or []
                for part in parts:
                    fc = getattr(part, "function_call", None)
                    if fc and getattr(fc, "name", None):
                        key = (fc.name, str(sorted(fc.args.items()) if fc.args else []))
                        if key not in seen_calls:
                            seen_calls.add(key)
                            found.append(fc)
        except (AttributeError, TypeError) as _candidate_err:
            _logger.debug("Candidate parts traversal failed: %s", _candidate_err)

        return found

    async def _stream_response(
        self, user_input: Union[str, List], callback: Optional[Callable[[str], None]] = None
    ) -> None:
        """Sends a message to the model and streams the response (Async).

        Orchestrates the retry logic, streaming process, tool execution,
        and post-turn maintenance (autosave and context summarization).

        Args:
            user_input: The user or tool generated message payload.
            callback: Optional async function to receive streamed text chunks.
        """
        import random

        max_retries = 3
        base_delay = 2.0  # seconds

        for attempt in range(1, max_retries + 1):
            try:
                await self._ensure_session()
                full_text, function_calls_received = await self._process_stream(user_input, callback)

                await self._handle_tool_executions(function_calls_received, callback)

                if not full_text and not function_calls_received:
                    console.print(f"[dim]{_('engine.rate_limit_hint')}[/dim]")

                await self._post_turn_maintenance()
                return

            except Exception as e:
                if not await self._handle_retryable_error(e, attempt, max_retries, base_delay):
                    console.print(f"[error]{_('engine.api_error')}[/error] {e}")
                    return

    async def _process_stream(
        self, user_input: Union[str, List], callback: Optional[Callable[[str], None]]
    ) -> tuple[str, List[types.FunctionCall]]:
        """Processes the generator stream, updating UI and collecting function calls.
        
        Args:
            user_input: The user or tool generated message payload.
            callback: Optional async function to receive streamed text chunks.
            
        Returns:
            A tuple containing the full accumulated text response and a list of requested tool calls.
        """
        full_text = ""
        seen_calls: set = set()
        function_calls_received: List[types.FunctionCall] = []
        self.interrupted = False
        
        response_stream = await self.chat_session.send_message_stream(message=user_input)

        if callback:
            async for chunk in response_stream:
                if self.interrupted:
                    callback("\n\n[bold red][INTERRUMPIDO POR EL USUARIO][/bold red]")
                    break

                if chunk.text:
                    callback(chunk.text)
                    full_text += chunk.text

                self._process_chunk_metadata(chunk, seen_calls, function_calls_received)
        else:
            # Legacy CLI Output mode (using rich.Live)
            from rich.live import Live
            from rich.markdown import Markdown

            with Live(Markdown("Pensando..."), console=console, auto_refresh=False) as live:
                async for chunk in response_stream:
                    if self.interrupted:
                        live.update(Markdown(full_text + "\n\n[bold red][INTERRUMPIDO POR EL USUARIO][/bold red]"))
                        break

                    if chunk.text:
                        full_text += chunk.text
                        live.update(Markdown(full_text))
                        live.refresh()

                    self._process_chunk_metadata(chunk, seen_calls, function_calls_received)
                    
        return full_text, function_calls_received

    def _process_chunk_metadata(self, chunk: types.Part, seen_calls: set, function_calls_received: List[types.FunctionCall]) -> None:
        """Extracts function calls and tracks metrics from a single chunk.
        
        Args:
            chunk: The streaming part chunk received from the API.
            seen_calls: The set of already processed function call IDs/signatures.
            function_calls_received: List mutating reference where new calls are appended.
        """
        new_calls = self._extract_function_calls(chunk, seen_calls)
        function_calls_received.extend(new_calls)

        if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
            self.metrics.add_usage(
                chunk.usage_metadata.prompt_token_count, chunk.usage_metadata.candidates_token_count
            )

    async def _handle_tool_executions(self, function_calls: List[types.FunctionCall], callback: Optional[Callable[[str], None]]) -> None:
        """Executes requested tools and feeds the results back into the model.
        
        Args:
            function_calls: List of requested tools returned by the LLM.
            callback: The UI streaming callback to pass down recursively.
        """
        if not function_calls:
            return
            
        function_responses = []
        for fc in function_calls:
            self.session_tools += 1
            function_responses.append(await self.dispatcher.execute(fc))
            
        if function_responses:
            # Recursive loop for tool feedback
            await self._stream_response(function_responses, callback=callback)

    async def _post_turn_maintenance(self) -> None:
        """Handles session saving and token compression after a turn."""
        if self.chat_session:
            raw_history = self.chat_session.get_history()
            if raw_history:
                self.history.save_session(raw_history)

        # Check if we need to summarize to liberate tokens for the next turn
        await self._summarize_context()

    async def _handle_retryable_error(self, e: Exception, attempt: int, max_retries: int, base_delay: float) -> bool:
        """Evaluates if an API error is retryable and sleeps if appropriate.
        Returns True if the error is handled (sleeping), False to raise or stop.
        """
        import random
        error_str = str(e).lower()
        is_retryable = any(keyword in error_str for keyword in _RETRYABLE_KEYWORDS)

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

    async def _summarize_context(self) -> None:
        """Triggered when history length exceeds a safety threshold.
        """
        if not self.chat_session:
            return

        history = self.chat_session.get_history()
        # Threshold optimized for Gemini Pro / AI Pro: 100 turns
        if len(history) < 100:
            return

        _logger.info("Context threshold reached (%d messages). Starting summarization...", len(history))

        # We keep the first message (usually user intent) and the last 6 messages (active context)
        first_msg = history[0]
        active_context = history[-6:]
        to_summarize = history[1:-6]

        # Create a temporary session to summarize
        summary_prompt = "Resume los puntos clave, decisiones técnicas y descubrimientos de esta conversación hasta ahora en un solo párrafo conciso en español. No pierdas detalles sobre rutas de archivos o comandos ejecutados."

        try:
            # We use the base client to avoid messing with the current session
            temp_response = await self.client.models.generate_content(
                model=self.model_name,
                contents=to_summarize + [types.Content(role="user", parts=[types.Part.from_text(text=summary_prompt)])],
                config=types.GenerateContentConfig(temperature=0.3),
            )

            summary_text = temp_response.text
            _logger.info("Context summarized successfully.")

            # Reconstruct history: [Original Start] + [Summary Hub] + [Recent Context]
            summary_part = types.Part.from_text(text=f"[RESUMEN DE CONTEXTO ANTERIOR]: {summary_text}")
            summary_content = types.Content(role="model", parts=[summary_part])

            new_history = [first_msg, summary_content] + active_context

            # Re-initialize the active session with the compacted history
            self.chat_session = self.client.aio.chats.create(
                model=self.model_name, config=self._build_config(), history=new_history
            )

        except Exception as e:
            _logger.error("Failed to summarize context: %s", e)

    # ------------------------------------------------------------------ #
    # Slash commands                                                       #
    # ------------------------------------------------------------------ #

    async def _process_slash_command(self, user_input: str) -> None:
        """Parses and dispatches mid-conversation slash commands (Async).

        Args:
            user_input (str): The raw string command prefixed with '/'.
        """
        parts = user_input.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if command == "/help":
            self._cmd_help()

        elif command == "/model":
            await self._cmd_model(args)

        elif command == "/mode":
            self._cmd_mode(args)

        elif command == "/clear":
            await self._cmd_clear()

        elif command == "/history":
            await self._cmd_history(args)

        elif command == "/stats":
            self._cmd_stats()

        elif command == "/stop":
            self.interrupted = True
            if self.dispatcher.logger:
                self.dispatcher.logger("[bold red]Generation Interrupted by User.[/bold red]")

        elif command == "/reset":
            await self._cmd_reset()

        elif command == "/abort":
            self.interrupted = True
            if self.dispatcher.logger:
                self.dispatcher.logger("[bold red]Process Aborted.[/bold red]")

        else:
            console.print(f"[warning]{_('cmd.unknown')}[/warning] {command} {_('cmd.hint_help')}")

    def _cmd_help(self) -> None:
        """Prints a formatted table of all available slash commands."""
        table = Table(title=_("cmd.help.title"), show_header=True, header_style="google.blue")
        table.add_column(_("cmd.help.header.cmd"), style="success", no_wrap=True)
        table.add_column(_("cmd.help.header.desc"))

        table.add_row("/help", _("cmd.desc.help"))
        table.add_row("/model", _("cmd.desc.model_list"))
        table.add_row("/model <name>", _("cmd.desc.model_switch"))
        table.add_row("/mode auto", _("cmd.desc.mode_auto"))
        table.add_row("/mode manual", _("cmd.desc.mode_manual"))
        table.add_row("/clear", _("cmd.desc.clear"))
        table.add_row("/history list", _("cmd.desc.history_list"))
        table.add_row("/history load <id>", _("cmd.desc.history_load"))
        table.add_row("/history delete <id>", _("cmd.desc.history_delete"))
        table.add_row("/usage", _("cmd.desc.usage"))
        table.add_row("/stats", _("cmd.desc.stats"))
        table.add_row("/stop", "Detiene la generación actual")
        table.add_row("/reset", "Reinicia la sesión y borra el historial")
        table.add_row("/abort", "Aborta la operación actual")
        table.add_row("exit / quit / q", _("cmd.desc.exit"))

        console.print(table)

    async def _cmd_model(self, args: List[str]) -> None:
        """Lists available models or switches to the specified one (Async)."""
        if not args:
            console.print(f"[warning]{_('cmd.active_model')}[/warning] {self.model_name}")
            try:
                console.print(f"[dim]{_('cmd.model.fetching')}[/dim]")
                available = []
                # Use aio for model listing
                models_response = await self.client.aio.models.list()
                async for model_obj in models_response:
                    actions = getattr(model_obj, "supported_actions", None) or getattr(
                        model_obj, "supported_generation_methods", []
                    )
                    if "generateContent" in actions:
                        clean_name = model_obj.name.replace("models/", "")
                        if "gemini" in clean_name.lower():
                            available.append(clean_name)

                if available:
                    console.print(f"\n[bold]{_('cmd.model.available')}[/bold]")
                    for m in sorted(available):
                        active_marker = " [success]← active[/success]" if m == self.model_name else ""
                        console.print(f"  • [google.blue]{m}[/google.blue]{active_marker}")
            except Exception as e:
                console.print(f"[dim]{_('cmd.model.could_not_retrieve', e=e)}[/dim]")

            console.print(f"\n[dim]{_('cmd.model.usage')}[/dim]")
            return

        new_model = args[0]
        self.model_name = new_model
        self.config.settings["model_name"] = new_model
        self.config.save_settings()

        # Preserve history
        current_history = self.chat_session.get_history() if self.chat_session else None
        try:
            self.chat_session = self.client.aio.chats.create(
                model=self.model_name,
                config=self._build_config(),
                history=current_history,
            )
            console.print(f"[success]{_('cmd.model.switched')}[/success] {self.model_name}")
        except Exception as e:
            console.print(f"[error]{_('cmd.model.failed')}[/error] {e}")

    def _cmd_mode(self, args: List[str]) -> None:
        """Toggles file edit confirmation mode between manual and auto.

        Args:
            args (List[str]): Input target (e.g. ['auto'] or ['manual']).
        """
        if not args or args[0].lower() not in ("auto", "manual"):
            console.print(f"[warning]{_('cmd.mode.current')}[/warning] {self.edit_mode}")
            console.print(f"[dim]{_('cmd.mode.usage')}[/dim]")
            return

        new_mode = args[0].lower()
        self.edit_mode = new_mode
        self.config.settings["edit_mode"] = new_mode
        self.config.save_settings()
        console.print(f"[success]{_('cmd.mode.set')}[/success] {self.edit_mode}")

    async def _ensure_session(self) -> None:
        """Ensures an active chat session is correctly initialized."""
        if self.chat_session is None:
            self.chat_session = self.client.aio.chats.create(
                model=self.model_name,
                config=self._build_config(),
            )

    async def _cmd_clear(self) -> None:
        """Resets the in-memory context window without ending the session (Async)."""
        try:
            self.chat_session = self.client.aio.chats.create(
                model=self.model_name,
                config=self._build_config(),
            )
            console.print(f"[success]{_('cmd.clear.success')}[/success] [dim]{_('cmd.clear.subtitle')}[/dim]")
        except Exception as e:
            console.print(f"[error]{_('cmd.clear.failed')}[/error] {e}")

    async def _cmd_reset(self) -> None:
        """Fully resets the session and clears UI (Async)."""
        await self._cmd_clear()
        self.session_messages = 0
        self.session_tools = 0
        console.print("[bold red]Sesión reiniciada por completo.[/bold red]")

    async def _cmd_history(self, args: List[str]) -> None:
        """Manages saved sessions: list, load, or delete (Async).

        Args:
            args (List[str]): Target history management command flags.
        """
        sub = args[0].lower() if args else "list"

        if sub == "list":
            sessions = self.history.list_sessions()
            if not sessions:
                console.print(f"[dim]{_('cmd.history.none')}[/dim]")
                return
            table = Table(title=_("cmd.history.title"), show_header=True, header_style="google.blue")
            table.add_column("#", style="dim", width=4)
            table.add_column("Session ID", style="google.blue")
            for i, s in enumerate(reversed(sessions), 1):
                table.add_row(str(i), s)
            console.print(table)
            console.print(f"[dim]{_('cmd.history.subtitle')}[/dim]")

        elif sub == "load":
            if len(args) < 2:
                console.print(f"[warning]{_('cmd.history.usage.load')}[/warning]")
                return
            session_id = args[1]
            history_data = self.history.load_session(session_id)
            if history_data is None:
                console.print(f"[error]{_('cmd.history.load.not_found', id=session_id)}[/error]")
                return
            try:
                self.chat_session = self.client.aio.chats.create(
                    model=self.model_name,
                    config=self._build_config(),
                    history=history_data,
                )
                console.print(
                    f"[success]{_('cmd.history.load.success')}[/success] {session_id} "
                    f"[dim]{_('cmd.history.load.sub', count=len(history_data))}[/dim]"
                )
            except Exception as e:
                console.print(f"[error]{_('cmd.history.load.failed')}[/error] {e}")

        elif sub == "delete":
            if len(args) < 2:
                console.print(f"[warning]{_('cmd.history.usage.del')}[/warning]")
                return
            session_id = args[1]
            if self.history.delete_session(session_id):
                console.print(f"[success]{_('cmd.history.del.success')}[/success] {session_id}")
            else:
                console.print(f"[error]{_('cmd.history.del.not_found', id=session_id)}[/error]")

        else:
            console.print(f"[warning]{_('cmd.history.unknown')}[/warning] {sub}")
            console.print(f"[dim]{_('cmd.history.available')}[/dim]")

    def _cmd_usage(self) -> None:
        """Displays current session token usage and estimated cost."""
        console.print(f"\n[google.blue]— {_('cmd.usage.title')} —[/google.blue]")
        console.print(f"  {self.metrics.get_summary()}\n")

    def _cmd_stats(self) -> None:
        """Displays a summary of accomplishments in the current session."""
        from rich.panel import Panel

        stats_content = (
            f"{_('cmd.stats.messages', count=f'[bold]{self.session_messages}[/bold]')}\n"
            f"{_('cmd.stats.tools', count=f'[bold]{self.session_tools}[/bold]')}\n"
            f"{_('cmd.stats.files', count=f'[bold]{self.dispatcher.modified_files_count}[/bold]')}"
        )
        console.print(
            Panel(
                stats_content,
                title=f"[google.blue]{_('cmd.stats.title')}[/google.blue]",
                border_style="google.blue",
                expand=False,
            )
        )

    # ------------------------------------------------------------------ #
    # Main loop                                                            #
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Initializes the client and runs the main interactive CLI loop (Async)."""
        if not await self.setup_api():
            sys.exit(1)

        self.running = True

        try:
            self.chat_session = self.client.aio.chats.create(
                model=self.model_name,
                config=self._build_config(),
            )
        except Exception as e:
            console.print(f"[error][X] API Error:[/error] {e}")
            sys.exit(1)

        while self.running:
            try:
                user_input = Prompt.ask(f"\n[user]{_('engine.you')}[/user]").strip()
                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit", "q"):
                    self.running = False
                    break

                if user_input.startswith("/"):
                    await self._process_slash_command(user_input)
                    continue

                self.session_messages += 1
                console.print("[agent]AskGem:[/agent]")
                await self._stream_response(user_input)

            except (KeyboardInterrupt, EOFError):
                self.running = False
                break

        console.print(f"\n[warning]{_('engine.shutdown')}[/warning]")
