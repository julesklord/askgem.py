"""
TUI Dashboard for AskGem using the Textual framework.

Provides a multi-pane interface with real-time metrics, a mission sidebar,
and a dedicated activity log for autonomous operations.
"""


from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from ..cli.main import ASCII_MASCOT
from ..core.i18n import _

# Multi-state Diamond Mascot Frames
MASCOT_FRAMES = {
    "idle": [
        r"[#4285F4]  / \  [/]\n[#4285F4] < [#FBBC05]. [#4285F4]> [/]\n[#4285F4]  \ /  [/]"
    ],
    "thinking": [
        r"[#4285F4]  / \  [/]\n[#4285F4] < [#FBBC05]o [#4285F4]> [/]\n[#4285F4]  \ /  [/]",
        r"[#4285F4]  / \  [/]\n[#4285F4] < [#FBBC05]O [#4285F4]> [/]\n[#4285F4]  \ /  [/]",
        r"[#4285F4]  / \  [/]\n[#4285F4] < [white]O [/#4285F4]> [/]\n[#4285F4]  \ /  [/]"
    ],
    "working": [
        r"[#4285F4]  / \  [/]\n[#4285F4] < [#FBBC05]+ [#4285F4]> [/]\n[#4285F4]  \ /  [/]",
        r"[#4285F4]  / \  [/]\n[#4285F4] < [#FBBC05]x [#4285F4]> [/]\n[#4285F4]  \ /  [/]",
        r"[#4285F4]  / \  [/]\n[#4285F4] < [#FBBC05]* [#4285F4]> [/]\n[#4285F4]  \ /  [/]"
    ],
    "error": [
        r"[#EA4335]  / \  [/]\n[#EA4335] <  !  > [/]\n[#EA4335]  \ /  [/]"
    ],
    "success": [
        r"[#34A853]  / \  [/]\n[#34A853] <  *  > [/]\n[#34A853]  \ /  [/]"
    ]
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

        yield Static(_("dashboard.sidebar.stats"), classes="section-title")
        self.stats_info = Static("Tokens: 0\nCost: $0.00", id="stats-info")
        yield self.stats_info

    def update_stats(self, summary: str):
        self.stats_info.update(summary)

    def update_context(self, model: str, mode: str):
        self.context_info.update(f"Modelo: [bold]{model}[/bold]\nModo: [bold]{mode}[/bold]")


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

    #debug-pane {
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
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+l", "clear", "Clear"),
        ("f12", "toggle_debug", "Debug"),
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
            self.chat_log = RichLog(highlight=True, markup=True)
            yield self.chat_log
            self.debug_log = RichLog(highlight=True, markup=True, id="debug-pane")
            yield self.debug_log
        yield Input(placeholder=_("api.prompt"), id="prompt-input")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        self.title = f"AskGem v2.2.0"
        self.sub_title = _("startup.init")
        self.sidebar.update_context(self.agent.model_name, self.agent.edit_mode)
        
        # Link debug logger
        self.agent.set_status_logger(self.log_debug)
        
        self.chat_log.write(f"\n[#FBBC05][bold]{_('startup.welcome', version='2.3.0')}[/bold][/]")
        self.chat_log.write(_("cmd.hint_help"))
        self._update_metrics()

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

        self.chat_log.write(f"\n[bold][user]Tú:[/user][/bold] {user_text}")
        self.run_agent_turn(user_text)

    @work(exclusive=True)
    async def run_agent_turn(self, user_input: str) -> None:
        """Runs the agent's interaction loop in a background task."""
        mascot = self.query_one(MascotWidget)
        mascot.set_state("thinking")
        
        self.chat_log.write("\n[agent]AskGem:[/agent]")
        self.current_response = ""

        def stream_callback(text):
            self.current_response += text
            self.chat_log.write(text, scroll_end=True)

        try:
            await self.agent._stream_response(user_input, callback=stream_callback)
            self._update_metrics()
            mascot.set_state("success")
        except Exception as e:
            self.chat_log.write(f"\n[error][X] Error:[/error] {e}")
            mascot.set_state("error")
        finally:
            # Revert to idle after a delay
            self.set_timer(3.0, lambda: mascot.set_state("idle"))

    def action_clear(self) -> None:
        """Clears the chat log."""
        self.chat_log.clear()
        self.debug_log.clear()

    def action_toggle_debug(self) -> None:
        """Toggles the debug pane visibility."""
        pane = self.query_one("#debug-pane")
        pane.display = not pane.display

    def log_debug(self, message: str):
        """Helper to write to the debug log."""
        self.debug_log.write(f"[#FBBC05][DEBUG][/] {message}")
        # Switch mascot to working state if a tool is being dispatched
        if "Dispatching" in message or "Ejecutando" in message:
            self.query_one(MascotWidget).set_state("working")
