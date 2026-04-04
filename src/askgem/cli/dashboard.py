"""
TUI Dashboard for AskGem using the Textual framework.

Provides a multi-pane interface with real-time metrics, a mission sidebar,
and a dedicated activity log for autonomous operations.
"""

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static
from rich.table import Table
from rich.markdown import Markdown
from rich.markup import escape

from ..core.i18n import _

# Multi-state Diamond Mascot Frames
MASCOT_FRAMES = {
    "idle": [r"[#4285F4]  / \  [/]\n[#4285F4] < [#FBBC05]. [#4285F4]> [/]\n[#4285F4]  \ /  [/]"],
    "thinking": [
        r"[#4285F4]  / \  [/]\n[#4285F4] < [#FBBC05]o [#4285F4]> [/]\n[#4285F4]  \ /  [/]",
        r"[#4285F4]  / \  [/]\n[#4285F4] < [#FBBC05]O [#4285F4]> [/]\n[#4285F4]  \ /  [/]",
        r"[#4285F4]  / \  [/]\n[#4285F4] < [white]O [/#4285F4]> [/]\n[#4285F4]  \ /  [/]",
    ],
    "working": [
        r"[#4285F4]  / \  [/]\n[#4285F4] < [#FBBC05]+ [#4285F4]> [/]\n[#4285F4]  \ /  [/]",
        r"[#4285F4]  / \  [/]\n[#4285F4] < [#FBBC05]x [#4285F4]> [/]\n[#4285F4]  \ /  [/]",
        r"[#4285F4]  / \  [/]\n[#4285F4] < [#FBBC05]* [#4285F4]> [/]\n[#4285F4]  \ /  [/]",
    ],
    "error": [r"[#EA4335]  / \  [/]\n[#EA4335] <  !  > [/]\n[#EA4335]  \ /  [/]"],
    "success": [r"[#34A853]  / \  [/]\n[#34A853] <  *  > [/]\n[#34A853]  \ /  [/]"],
}


class MascotWidget(Static):
    """Animated multi-state Diamond/Gem mascot."""

    def on_mount(self) -> None:
        self.frame_idx = 0
        self.state = "idle"
        self.update(MASCOT_FRAMES["idle"][0])
        self.set_interval(0.3, self.animate)

    def set_state(self, state: str):
        """Changes the mascot state and resets the animation index."""
        if state in MASCOT_FRAMES:
            self.state = state
            self.frame_idx = 0
            self.update(MASCOT_FRAMES[state][0])

    def animate(self) -> None:
        frames = MASCOT_FRAMES.get(self.state, MASCOT_FRAMES["idle"])
        if len(frames) > 1:
            self.frame_idx = (self.frame_idx + 1) % len(frames)
            self.update(frames[self.frame_idx])
        elif self.state != "idle" and self.frame_idx == 0:
            # For static states like 'error' or 'success', just stay on frame 0
            self.update(frames[0])


class Sidebar(Static):
    """Left sidebar showing session context and active mission."""

    def compose(self) -> ComposeResult:
        yield MascotWidget(id="mascot")
        yield Static(_("dashboard.sidebar.context"), classes="section-title")
        self.context_info = Static("Cargando...", id="context-info")
        yield self.context_info

        yield Static("Misión Actual", classes="section-title")
        self.mission_info = Static("Sin misión activa.", id="mission-info")
        yield self.mission_info

        yield Static(_("dashboard.sidebar.stats"), classes="section-title")
        self.stats_info = Static("Tokens: 0\nCost: $0.00", id="stats-info")
        yield self.stats_info

    def update_stats(self, summary: str):
        self.stats_info.update(summary)

    def update_context(self, model: str, mode: str):
        self.context_info.update(f"Modelo: [bold]{model}[/bold]\nModo: [bold]{mode}[/bold]")

    def update_mission(self, summary: str):
        self.mission_info.update(summary)


class AskGemDashboard(App):
    """The main AskGem TUI Application."""

    CSS = """
    Screen {
        background: $background;
    }

    #main-container {
        height: 1fr;
    }

    Sidebar {
        width: 30;
        background: $surface;
        color: $text;
        padding: 1;
        border-right: tall #4285F4;
    }

    .section-title {
        background: #4285F4;
        color: white;
        padding: 0 1;
        margin-bottom: 1;
        text-style: bold;
    }

    RichLog {
        background: $background;
        border: none;
        padding: 1;
    }

    Input {
        dock: bottom;
        margin: 1 0 0 0;
        border: tall #4285F4;
    }

    Input:focus {
        border: tall #FBBC05;
    }

    #mascot {
        height: 4;
        content-align: center middle;
        margin-bottom: 0;
    }

    #output-pane {
        width: 40;
        background: $surface;
        border-left: tall #FBBC05;
        display: none;
    }

    #context-info, #stats-info {
        margin-bottom: 2;
        padding: 0 1;
        color: $text-muted;
    }

    #chat-area {
        height: 1fr;
        width: 1fr;
    }

    #chat-history {
        height: 1fr;
    }

    #streaming-response {
        height: auto;
        padding: 1;
        background: $surface;
        color: $text;
        display: none;
        border-top: tall #4285F4;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+l", "clear", "Clear"),
        ("f12", "toggle_output", "Output"),
    ]

    def __init__(self, agent):
        super().__init__()
        self.agent = agent

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        with Horizontal(id="main-container"):
            self.sidebar = Sidebar()
            yield self.sidebar
            with Vertical(id="chat-area"):
                self.chat_log = RichLog(highlight=True, markup=True, id="chat-history")
                yield self.chat_log
                self.streaming_response = Static("", id="streaming-response")
                yield self.streaming_response
            self.output_log = RichLog(highlight=True, markup=True, id="output-pane")
            yield self.output_log
        yield Input(placeholder=_("api.prompt"), id="prompt-input")
        yield Footer()

    @work(exclusive=True)
    async def init_api(self) -> None:
        """Initializes the Gemini API in the background and restores last session."""
        self.sidebar.update_context(self.agent.model_name, "Iniciando...")
        try:
            # We pass interactive=False because we are in a TUI, we handle keys via config
            if await self.agent.setup_api(interactive=False):
                # Milestone 4.3: Auto-Resume last session
                sessions = self.agent.history.list_sessions()
                if sessions:
                    last_session = sessions[-1]
                    history_data = self.agent.history.load_session(last_session)
                    if history_data:
                        try:
                            self.agent.chat_session = self.agent.client.chats.create(
                                model=self.agent.model_name,
                                config=self.agent._build_config(),
                                history=history_data
                            )
                            self.chat_log.write(f"\n[bold sky_blue]Resumiendo sesión anterior: [dim]{last_session}[/dim][/bold sky_blue]")
                            # Populate UI with historic messages
                            for msg in history_data:
                                role = "Tú" if msg.role == "user" else "AskGem"
                                text_parts = [p.text for p in msg.parts if p.text]
                                if text_parts:
                                    self.chat_log.write(self.render_message(role, "\n".join(text_parts)))
                        except Exception as chat_err:
                            self.log_output(f"[bold red]WARNING:[/] No se pudo reanudar la sesión: {chat_err}")
                            # Fallback to empty session
                            self.agent.chat_session = self.agent.client.chats.create(
                                model=self.agent.model_name,
                                config=self.agent._build_config()
                            )

                self.sidebar.update_context(self.agent.model_name, self.agent.edit_mode)
                self._update_mission_display()
                self.query_one("#prompt-input", Input).placeholder = "Escribe tu mensaje..."
                self.chat_log.write(f"\n[success][OK] Conexión establecida con [bold]{self.agent.model_name}[/bold][/success]")
            else:
                # If setup_api fails, it means the API key is missing or invalid
                error_msg = "API Key no configurada o inválida"
                self.chat_log.write(f"\n[error][X] {error_msg}.[/error]")
                self.chat_log.write("\n[bold yellow]TIP:[/] Configura tu API Key en el archivo [italic]settings.json[/italic] o mediante variables de entorno.")
                self.query_one(MascotWidget).set_state("error")
                self.sidebar.update_context(self.agent.model_name, "Error de Auth")
        except Exception as e:
            error_msg = f"Error al inicializar la API: {str(e)}"
            self.chat_log.write(f"\n[error][X] {error_msg}. Revisa tu configuración.[/error]")
            self.log_output(f"[bold red]CRITICAL:[/] {error_msg}")
            self.query_one(MascotWidget).set_state("error")
            self.sidebar.update_context("N/A", "Error")

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        self.title = "AskGem v2.3.1"
        self.sub_title = "Habilitando Memoria Cognitiva..."
        
        # Link output logger
        self.agent.set_status_logger(self.log_output)

        self.chat_log.write(f"\n[#FBBC05][bold]{_('startup.welcome', version='2.3.1')}[/bold][/]")
        self.chat_log.write(_("cmd.hint_help"))
        self._update_metrics()

        # Periodically refresh Mission Sidebar
        self.set_interval(5.0, self._update_mission_display)

        # Start background initialization
        self.init_api()

    def _update_mission_display(self) -> None:
        """Reads heartbeat.md and updates the sidebar."""
        try:
            mission_text = self.agent.mission.read_missions()
            if not mission_text:
                self.sidebar.update_mission("Sin misiones activas.")
                return

            # Extract just the tasks part for the sidebar if it's too long
            if "## Tasks" in mission_text:
                parts = mission_text.split("## Tasks")
                mission_text = parts[1].strip() if len(parts) > 1 else parts[0].strip()
            
            self.sidebar.update_mission(mission_text)
        except FileNotFoundError:
            self.sidebar.update_mission("Misiones: Archivo no encontrado.")
        except Exception as e:
            self.log_output(f"[bold red]ERROR:[/] Fallo al leer misiones: {str(e)}")
            self.sidebar.update_mission("Error al leer misiones.")

    def render_message(self, author: str, content: str, is_markdown: bool = True) -> Table:
        """Creates a 2-column table for hanging-indent style chat messages."""
        table = Table.grid(expand=True)
        table.add_column(width=12)  # Author column
        table.add_column()          # Body column

        author_tag = f"[bold][agent]{author}[/agent][/bold]" if author == "AskGem" else f"[bold][user]{author}:[/user][/bold]"
        
        body = Markdown(content) if is_markdown else escape(content)
        table.add_row(author_tag, body)
        return table

    def _update_metrics(self):
        """Refreshes the sidebar metrics from the agent."""
        summary = self.agent.metrics.get_summary()
        self.sidebar.update_stats(summary)

    @on(Input.Submitted, "#prompt-input")
    async def handle_prompt(self, event: Input.Submitted) -> None:
        """Handles user input submission."""
        user_text = event.value.strip()
        if not user_text:
            return

        event.input.value = ""

        if user_text.lower() in ("exit", "quit", "q"):
            self.exit()
            return

        # Render user message to history
        self.chat_log.write(self.render_message(_("engine.you"), user_text, is_markdown=False))

        # Intercept slash commands for local processing
        if user_text.startswith("/"):
            await self.agent._process_slash_command(user_text)
            if user_text.lower() == "/clear":
                self.action_clear()
            elif user_text.lower() == "/usage":
                self._update_metrics()
            return

        self.run_agent_turn(user_text)

    @work(exclusive=True)
    async def run_agent_turn(self, user_input: str) -> None:
        """Runs the agent's interaction loop in a background task."""
        mascot = self.query_one(MascotWidget)
        mascot.set_state("thinking")

        self.current_response = ""
        self.streaming_response.display = True

        def stream_callback(text):
            self.current_response += text
            self.streaming_response.update(self.render_message("AskGem", self.current_response))

        try:
            await self.agent._stream_response(user_input, callback=stream_callback)
            self._update_metrics()

            # "Commit" to permanent history
            self.chat_log.write(self.render_message("AskGem", self.current_response))

            mascot.set_state("success")
        except Exception as e:
            self.chat_log.write(f"\n[error][X] Error:[/error] {escape(str(e))}")
            mascot.set_state("error")
        finally:
            self.streaming_response.display = False
            self.streaming_response.update("")
            # Revert to idle after a delay
            self.set_timer(3.0, lambda: mascot.set_state("idle"))

    def action_clear(self) -> None:
        """Clears the chat log."""
        self.chat_log.clear()
        self.output_log.clear()

    def action_toggle_output(self) -> None:
        """Toggles the visibility of the output log pane."""
        pane = self.query_one("#output-pane")
        pane.display = not pane.display

    def log_output(self, message: str) -> None:
        """Appends a message to the output activity log."""
        if hasattr(self, "output_log"):
            # We trust the message markup here, caller should escape if needed
            self.output_log.write(f"[#FBBC05][OUTPUT][/] {message}")
        # Switch mascot to working state if a tool is being dispatched
        if "Dispatching" in message or "Ejecutando" in message:
            self.query_one(MascotWidget).set_state("working")
