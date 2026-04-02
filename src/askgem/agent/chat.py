"""
Main autonomous agent logic module.

Manages the conversational loop, tool routing, and API interactions with the generative models.
It does NOT manage filesystem paths or raw terminal rendering.
"""

import logging
import os
import platform
import sys
from typing import List, Union

from google import genai
from google.genai import types
from rich.live import Live
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt
from rich.status import Status
from rich.table import Table

from ..cli.console import console
from ..core.config_manager import ConfigManager
from ..core.history_manager import HistoryManager
from ..core.i18n import _
from ..core.paths import get_config_dir
from ..tools.file_tools import edit_file, read_file
from ..tools.system_tools import execute_bash, list_directory

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


class ChatAgent:
    """The central agent session manager handling interaction loops and tools."""

    def __init__(self):
        """Initializes the chat agent, loading defaults and instantiating managers."""
        self.running = False
        self.config = ConfigManager(console)
        self.history = HistoryManager(console)
        self.client = None
        self.chat_session = None

        # Load persisted settings
        self.model_name = self.config.settings.get("model_name", "gemini-2.5-pro")
        self.edit_mode = self.config.settings.get("edit_mode", "manual")

        # Registered autonomous tools
        self._tools = [list_directory, execute_bash, read_file, edit_file]

    # ------------------------------------------------------------------ #
    # Setup                                                                #
    # ------------------------------------------------------------------ #

    def setup_api(self) -> bool:
        """Loads and validates the Google API key, prompting the user if absent.

        Returns:
            bool: True if the client was successfully initialized, False otherwise.
        """
        api_key = self.config.load_api_key()

        if not api_key:
            console.print(f"\n[bold red]{_('api.missing')}[/bold red]")
            api_key = Prompt.ask(f"[bold cyan]{_('api.prompt')}[/bold cyan]").strip()

            if not api_key:
                console.print(f"[red][X] {_('api.fatal')}[/red]")
                return False

            save_choice = Prompt.ask(_('api.save')).strip().lower()
            if save_choice != 'n':
                self.config.save_api_key(api_key)

        self.client = genai.Client(api_key=api_key)
        return True

    def _build_config(self) -> types.GenerateContentConfig:
        """Assembles the model config including live OS context.

        Returns:
            types.GenerateContentConfig: The SDK config payload for generation.
        """
        sys_context = _('sys.context', os=f"{platform.system()} {platform.release()}", cwd=os.getcwd())
        return types.GenerateContentConfig(
            temperature=0.7,
            tools=self._tools,
            system_instruction=sys_context,
        )

    # ------------------------------------------------------------------ #
    # Agentic tool dispatch                                                #
    # ------------------------------------------------------------------ #

    def _execute_tool(self, function_call: types.FunctionCall) -> types.Part:
        """Routes a model-requested function call to the matching local implementation.

        Args:
            function_call (types.FunctionCall): The tool request parsed from the API.

        Returns:
            types.Part: The SDK part response containing the execution result payload.
        """
        tool_name = function_call.name
        args = function_call.args if function_call.args else {}

        console.print()

        # Tool execution UI Wrapper
        with Status(f"[bold cyan]{_('tool.spawning')} {tool_name}[/bold cyan]", spinner="dots", console=console):
            if tool_name == "list_directory":
                path = args.get("path", ".")
                result = list_directory(path)

            elif tool_name == "execute_bash":
                command = args.get("command", "")
                console.print(
                    f"\n[bold yellow]{_('tool.action_req')}[/bold yellow] "
                    f"{_('tool.wants_run')} [bold]'{command}'[/bold]"
                )
                if Confirm.ask(_('tool.confirm.cmd')):
                    result = execute_bash(command)
                else:
                    result = _('tool.denied.cmd')

            elif tool_name == "read_file":
                result = read_file(
                    args.get("path", ""),
                    args.get("start_line", None),
                    args.get("end_line", None),
                )

            elif tool_name == "edit_file":
                path = args.get("path", "")
                find_text = args.get("find_text", "")
                replace_text = args.get("replace_text", "")

                if self.edit_mode == "manual":
                    console.print(
                        f"\n[bold yellow]{_('tool.action_req')}[/bold yellow] "
                        f"{_('tool.wants_edit')} [bold]'{path}'[/bold]"
                    )
                    console.print(
                        f"[dim]--- Replacing ---[/dim]\n{find_text}\n"
                        f"[dim]--- With ---[/dim]\n{replace_text}\n"
                        f"[dim]-----------------[/dim]"
                    )
                    if Confirm.ask(_('tool.confirm.edit')):
                        result = edit_file(path, find_text, replace_text)
                    else:
                        result = _('tool.denied.edit')
                else:
                    console.print(f"[italic green]{_('tool.edit.auto', path=path)}[/italic green]")
                    result = edit_file(path, find_text, replace_text)

            else:
                result = _('tool.unregistered', name=tool_name)

        return types.Part.from_function_response(
            name=tool_name,
            response={"result": result},
        )

    # ------------------------------------------------------------------ #
    # Core response loop                                                   #
    # ------------------------------------------------------------------ #

    def _stream_response(self, user_input: Union[str, List]) -> None:
        """Sends a message to the model and streams the response to the terminal.
        
        # TODO: [refactor] this function has too many responsibilities — split into streaming payload rendering, function execution routing, and SDK fallback/retry handling.

        Args:
            user_input: The user or tool generated message payload.
        """
        import random
        import time

        max_retries = 3
        base_delay = 2.0  # seconds

        for attempt in range(1, max_retries + 1):
            try:
                response_stream = self.chat_session.send_message_stream(user_input)

                full_text = ""
                # Use a set to deduplicate function calls that may appear in both detection paths
                _seen_calls: set = set()
                function_calls_received: List[types.FunctionCall] = []

                with Live(Markdown(""), console=console, refresh_per_second=15) as live:
                    for chunk in response_stream:
                        # Text payload — render progressively
                        if chunk.text:
                            full_text += chunk.text
                            live.update(Markdown(full_text))

                        # --- Primary detection: SDK aggregated helper property ---
                        try:
                            for fc in (chunk.function_calls or []):
                                key = (fc.name, str(sorted(fc.args.items()) if fc.args else []))
                                if key not in _seen_calls:
                                    _seen_calls.add(key)
                                    function_calls_received.append(fc)
                        except Exception as _sdk_err:
                            _logger.debug("SDK function_calls property failed on chunk: %s", _sdk_err)

                        # --- Fallback detection: direct candidate parts traversal ---
                        # Some SDK versions only expose function_calls on the final
                        # accumulated response, not on individual streaming chunks.
                        try:
                            for candidate in (chunk.candidates or []):
                                content = getattr(candidate, "content", None)
                                parts = getattr(content, "parts", []) or []
                                for part in parts:
                                    fc = getattr(part, "function_call", None)
                                    if fc and getattr(fc, "name", None):
                                        key = (fc.name, str(sorted(fc.args.items()) if fc.args else []))
                                        if key not in _seen_calls:
                                            _seen_calls.add(key)
                                            function_calls_received.append(fc)
                        except Exception as _candidate_err:
                            _logger.debug("Candidate parts fallback failed on chunk: %s", _candidate_err)

                console.print("")

                if function_calls_received:
                    # Execute each tool the model requested and collect the results
                    function_responses = [
                        self._execute_tool(fc) for fc in function_calls_received
                    ]
                    # Recursive feedback loop: send tool results back to the model
                    if function_responses:
                        self._stream_response(function_responses)
                elif not full_text:
                    # Model returned neither text nor function calls — surface a diagnostic hint
                    console.print(f"[dim]{_('engine.rate_limit_hint')}[/dim]")

                # Autosave history after every fully resolved model turn
                if self.chat_session:
                    raw_history = getattr(self.chat_session, "history", None)
                    if raw_history:
                        self.history.save_session(raw_history)

                # Success — break out of the retry loop
                return

            except Exception as e:
                error_str = str(e).lower()
                is_retryable = any(keyword in error_str for keyword in [
                    "429", "resource exhausted", "rate limit",
                    "500", "internal", "503", "unavailable",
                    "deadline exceeded", "timeout",
                ])

                if is_retryable and attempt < max_retries:
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    _logger.warning("Retryable API error (attempt %d/%d): %s", attempt, max_retries, e)
                    console.print(
                        f"\n[bold yellow]{_('engine.retry', attempt=attempt, max=max_retries, delay=f'{delay:.1f}')}[/bold yellow]"
                    )
                    with Status(f"[dim]{_('engine.retry_waiting')}[/dim]", spinner="dots", console=console):
                        time.sleep(delay)
                    continue
                else:
                    if is_retryable:
                        _logger.error("All %d retry attempts exhausted: %s", max_retries, e)
                        console.print(f"\n[bold red]{_('engine.retry_exhausted', max=max_retries)}[/bold red]")
                    console.print(f"[bold red]{_('engine.api_error')}[/bold red] {e}")
                    return



    # ------------------------------------------------------------------ #
    # Slash commands                                                       #
    # ------------------------------------------------------------------ #

    def _process_slash_command(self, user_input: str) -> None:
        """Parses and dispatches mid-conversation slash commands.

        Args:
            user_input (str): The raw string command prefixed with '/'.
        """
        parts = user_input.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if command == "/help":
            self._cmd_help()

        elif command == "/model":
            self._cmd_model(args)

        elif command == "/mode":
            self._cmd_mode(args)

        elif command == "/clear":
            self._cmd_clear()

        elif command == "/history":
            self._cmd_history(args)

        else:
            console.print(f"[yellow]{_('cmd.unknown')}[/yellow] {command} {_('cmd.hint_help')}")

    def _cmd_help(self) -> None:
        """Prints a formatted table of all available slash commands."""
        table = Table(title=_('cmd.help.title'), show_header=True, header_style="bold cyan")
        table.add_column(_('cmd.help.header.cmd'), style="bold green", no_wrap=True)
        table.add_column(_('cmd.help.header.desc'))

        table.add_row("/help", _('cmd.desc.help'))
        table.add_row("/model", _('cmd.desc.model_list'))
        table.add_row("/model <name>", _('cmd.desc.model_switch'))
        table.add_row("/mode auto", _('cmd.desc.mode_auto'))
        table.add_row("/mode manual", _('cmd.desc.mode_manual'))
        table.add_row("/clear", _('cmd.desc.clear'))
        table.add_row("/history list", _('cmd.desc.history_list'))
        table.add_row("/history load <id>", _('cmd.desc.history_load'))
        table.add_row("/history delete <id>", _('cmd.desc.history_delete'))
        table.add_row("exit / quit / q", _('cmd.desc.exit'))

        console.print(table)

    def _cmd_model(self, args: List[str]) -> None:
        """Lists available models or switches to the specified one.

        Args:
            args (List[str]): Additional cli split tokens representing the model target.
        """
        if not args:
            console.print(f"[bold yellow]{_('cmd.active_model')}[/bold yellow] {self.model_name}")
            try:
                console.print(f"[dim]{_('cmd.model.fetching')}[/dim]")
                available = []
                for model_obj in self.client.models.list():
                    # Check attribute name defensively — SDK versions differ
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
                        active_marker = " [bold green]← active[/bold green]" if m == self.model_name else ""
                        console.print(f"  • [cyan]{m}[/cyan]{active_marker}")
            except Exception as e:
                console.print(f"[dim]{_('cmd.model.could_not_retrieve', e=e)}[/dim]")

            console.print(f"\n[dim]{_('cmd.model.usage')}[/dim]")
            return

        new_model = args[0]
        self.model_name = new_model
        self.config.settings["model_name"] = new_model
        self.config.save_settings()

        # Preserve history across model switch
        current_history = getattr(self.chat_session, "history", None)
        try:
            self.chat_session = self.client.chats.create(
                model=self.model_name,
                config=self._build_config(),
                history=current_history,
            )
            console.print(f"[bold green]{_('cmd.model.switched')}[/bold green] {self.model_name}")
        except Exception as e:
            console.print(f"[bold red]{_('cmd.model.failed')}[/bold red] {e}")

    def _cmd_mode(self, args: List[str]) -> None:
        """Toggles file edit confirmation mode between manual and auto.

        Args:
            args (List[str]): Input target (e.g. ['auto'] or ['manual']).
        """
        if not args or args[0].lower() not in ("auto", "manual"):
            console.print(f"[bold yellow]{_('cmd.mode.current')}[/bold yellow] {self.edit_mode}")
            console.print(f"[dim]{_('cmd.mode.usage')}[/dim]")
            return

        new_mode = args[0].lower()
        self.edit_mode = new_mode
        self.config.settings["edit_mode"] = new_mode
        self.config.save_settings()
        console.print(f"[bold green]{_('cmd.mode.set')}[/bold green] {self.edit_mode}")

    def _cmd_clear(self) -> None:
        """Resets the in-memory context window without ending the session."""
        try:
            self.chat_session = self.client.chats.create(
                model=self.model_name,
                config=self._build_config(),
            )
            console.print(
                f"[bold green]{_('cmd.clear.success')}[/bold green] "
                f"[dim]{_('cmd.clear.subtitle')}[/dim]"
            )
        except Exception as e:
            console.print(f"[bold red]{_('cmd.clear.failed')}[/bold red] {e}")

    def _cmd_history(self, args: List[str]) -> None:
        """Manages saved sessions: list, load, or delete.

        Args:
            args (List[str]): Target history management command flags.
        """
        sub = args[0].lower() if args else "list"

        if sub == "list":
            sessions = self.history.list_sessions()
            if not sessions:
                console.print(f"[dim]{_('cmd.history.none')}[/dim]")
                return
            table = Table(title=_('cmd.history.title'), show_header=True, header_style="bold cyan")
            table.add_column("#", style="dim", width=4)
            table.add_column("Session ID", style="cyan")
            for i, s in enumerate(reversed(sessions), 1):
                table.add_row(str(i), s)
            console.print(table)
            console.print(f"[dim]{_('cmd.history.subtitle')}[/dim]")

        elif sub == "load":
            if len(args) < 2:
                console.print(f"[yellow]{_('cmd.history.usage.load')}[/yellow]")
                return
            session_id = args[1]
            history_data = self.history.load_session(session_id)
            if history_data is None:
                console.print(f"[red]{_('cmd.history.load.not_found', id=session_id)}[/red]")
                return
            try:
                self.chat_session = self.client.chats.create(
                    model=self.model_name,
                    config=self._build_config(),
                    history=history_data,
                )
                console.print(
                    f"[bold green]{_('cmd.history.load.success')}[/bold green] {session_id} "
                    f"[dim]{_('cmd.history.load.sub', count=len(history_data))}[/dim]"
                )
            except Exception as e:
                console.print(f"[bold red]{_('cmd.history.load.failed')}[/bold red] {e}")

        elif sub == "delete":
            if len(args) < 2:
                console.print(f"[yellow]{_('cmd.history.usage.del')}[/yellow]")
                return
            session_id = args[1]
            if self.history.delete_session(session_id):
                console.print(f"[bold green]{_('cmd.history.del.success')}[/bold green] {session_id}")
            else:
                console.print(f"[red]{_('cmd.history.del.not_found', id=session_id)}[/red]")

        else:
            console.print(f"[yellow]{_('cmd.history.unknown')}[/yellow] {sub}")
            console.print(f"[dim]{_('cmd.history.available')}[/dim]")

    # ------------------------------------------------------------------ #
    # Main loop                                                            #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """Initializes the client and runs the main interactive CLI loop."""
        if not self.setup_api():
            sys.exit(1)

        self.running = True

        try:
            self.chat_session = self.client.chats.create(
                model=self.model_name,
                config=self._build_config(),
            )
        except Exception as e:
            console.print(f"[bold red][X] API Error:[/bold red] {e}")
            sys.exit(1)

        while self.running:
            try:
                user_input = Prompt.ask(f"\n[bold green]{_('engine.you')}[/bold green]").strip()
                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit", "q"):
                    self.running = False
                    break

                if user_input.startswith("/"):
                    self._process_slash_command(user_input)
                    continue

                console.print("[bold blue]AskGem:[/bold blue]")
                self._stream_response(user_input)

            except (KeyboardInterrupt, EOFError):
                self.running = False
                break

        console.print(f"\n[bold yellow]{_('engine.shutdown')}[/bold yellow]")
