"""
TUI Dashboard for AskGem using the Textual framework.
Optimized for high stability and performance on Windows (Push-Layout Edition).

Bugs fixed vs previous version:
  - Static(..., variant=...) crash: Static has no variant kwarg → removed, use CSS classes
  - recompose() called without await in sync context → replaced with sync Static.update()
  - log_output malformed Rich markup [[bold]{c}] → fixed to [bold {c}]
  - #output-pane had no CSS → starts hidden (display: none), toggled via F12
  - #command-palette had visibility:hidden + display:none → removed visibility:hidden
  - Version hardcoded '2.3.1' in on_mount → now uses __version__
"""

from typing import Optional

from rich.markdown import Markdown
from rich.markup import escape
from rich.table import Table
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Header, Input, RichLog, Static

from .. import __version__
from ..core.i18n import _

# ---------------------------------------------------------------------------
# CSS — Push-Layout. No docking. No overlapping layers.
# ---------------------------------------------------------------------------
GLOBAL_CSS = """
Screen {
    background: #0f172a;
}

#screen-wrapper {
    height: 100%;
    width: 100%;
}

#main-container {
    height: 1fr;
}

Sidebar {
    width: 25;
    background: #0f172a;
    color: #94a3b8;
    padding: 1;
    border-right: solid #1e293b;
}

#brand-title {
    color: #6366f1;
    text-style: bold;
    margin-bottom: 2;
    text-align: center;
}

.section-title {
    background: #312e81;
    color: #e0e7ff;
    padding: 0 1;
    margin-bottom: 0;
    text-style: bold;
}

RichLog {
    background: #0f172a;
    border: none;
    padding: 1;
}

/* Chat area expands to fill all remaining horizontal space */
#chat-area {
    height: 1fr;
    width: 1fr;
}

/* Output pane: hidden by default, toggled with F12 */
#output-pane {
    width: 42;
    background: #080f1d;
    border-left: solid #1e293b;
    display: none;
}

/* Streaming preview: shown only while agent is generating */
#streaming-response {
    height: auto;
    max-height: 10;
    padding: 0 2;
    background: #080f1d;
    color: #cbd5e1;
    border-left: solid #6366f1;
    display: none;
    overflow: hidden auto;
}

/* Command palette: hidden by default, shown when user types "/" */
#command-palette {
    background: #1e293b;
    border-top: solid #6366f1;
    height: auto;
    max-height: 8;
    padding: 0 1;
    display: none;
}

#bottom-bar {
    height: auto;
    background: #1e293b;
    border-top: tall #6366f1;
}

Input {
    border: none;
    background: #1e293b;
    height: 3;
}

Input:focus {
    border: none;
}

#dashboard-footer {
    height: 1;
    background: #0f172a;
    color: #6366f1;
    padding: 0 1;
    text-style: dim;
}

#modal-container {
    width: 60;
    background: #1e293b;
    border: thick #6366f1;
    padding: 1 2;
    align: center middle;
}

#modal-buttons { height: 3; align: center middle; margin-top: 1; }
#modal-buttons Button { margin: 0 1; }
"""


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
class Sidebar(Static):
    """Left sidebar showing session context and statistics."""

    def compose(self) -> ComposeResult:
        yield Static("ASKGEM [dim]PRO[/dim]", id="brand-title")
        yield Static(_("dashboard.sidebar.context"), classes="section-title")
        self.context_info = Static(_("dashboard.sidebar.loading"), id="context-info")
        yield self.context_info

        yield Static(_("dashboard.sidebar.mission"), classes="section-title")
        self.mission_info = Static(_("dashboard.sidebar.no_mission"), id="mission-info")
        yield self.mission_info
        yield Static(_("dashboard.sidebar.stats"), classes="section-title")
        self.stats_info = Static(_("dashboard.sidebar.stats_default"), id="stats-info")
        yield self.stats_info

    def update_stats(self, summary: str) -> None:
        self.stats_info.update(summary)

    def update_context(self, model: str, mode: str) -> None:
        self.context_info.update(
            f"Modelo: [bold]{model}[/bold]\nModo: [bold]{mode}[/bold]"
        )

    def update_mission(self, summary: str) -> None:
        self.mission_info.update(summary)


# ---------------------------------------------------------------------------
# Modal
# ---------------------------------------------------------------------------


class ConfirmationModal(ModalScreen[bool]):
    """Confirmation modal for critical actions."""

    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        severity: str = "info",
    ):
        super().__init__()
        self.message = message
        self.detail = detail
        self.severity = severity

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-container"):
            yield Static(f"[bold]{_('tool.action_req')}[/bold]", id="modal-title")
            yield Static(self.message, id="modal-msg")
            if self.detail:
                yield Static(self.detail, id="modal-detail")
            with Horizontal(id="modal-buttons"):
                yield Button(_("common.confirm"), variant="primary", id="confirm")
                yield Button(_("common.cancel"), variant="error", id="cancel")

    def on_mount(self) -> None:
        color = {
            "info": "#6366f1",
            "warning": "#eab308",
            "error": "#ef4444",
        }.get(self.severity, "#6366f1")
        self.query_one("#modal-container").styles.border = ("thick", color)

    @on(Button.Pressed, "#confirm")
    def confirm(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(False)


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
class DashboardFooter(Static):
    """Dynamic status bar rendered at the bottom of the screen."""

    def __init__(self) -> None:
        super().__init__(id="dashboard-footer")
        self._stats = "In: 0 | Out: 0"
        self._model = "N/A"
        self._mode = "manual"

    def update_info(self, stats: str, model: str, mode: str) -> None:
        self._stats, self._model, self._mode = stats, model, mode
        self.refresh()

    def render(self) -> str:
        return (
            f"🤖 [bold]{self._model}[/bold]"
            f" | ⚙️  {self._mode}"
            f" | 📊 {self._stats}"
            f" | [dim]{_('dashboard.footer.help_tip')}[/dim]"
        )


# ---------------------------------------------------------------------------
# Command Palette
# ---------------------------------------------------------------------------
class CommandPalette(Static):
    """
    Autocomplete suggestions that push the layout upward.

    Implemented as a single Static widget updated via .update() (sync) to
    avoid the async recompose() pitfall when called from sync event handlers.
    """

    def __init__(self, commands_meta: dict) -> None:
        super().__init__("", id="command-palette")
        self.commands_meta = commands_meta
        self.selected_index: int = 0
        self.filtered_cmds: list = []

    # ------------------------------------------------------------------
    # Internal render helper (sync — no recompose needed)
    # ------------------------------------------------------------------
    def _refresh_content(self) -> None:
        lines = []
        for i, (cmd, meta) in enumerate(self.filtered_cmds):
            if i == self.selected_index:
                lines.append(
                    f"[bold #e0e7ff on #312e81] ▶ {cmd}[/]"
                    f"  [dim]{meta['desc']}[/dim]"
                )
            else:
                lines.append(
                    f"[#475569]   {cmd}[/]"
                    f"  [dim]{meta['desc']}[/dim]"
                )
        self.update("\n".join(lines))

    def update_filter(self, text: str) -> None:
        if not text.startswith("/"):
            self.display = False
            self.filtered_cmds = []
            return

        search = text.lower()
        self.filtered_cmds = [
            (cmd, meta)
            for cmd, meta in self.commands_meta.items()
            if cmd.startswith(search)
        ]

        if not self.filtered_cmds:
            self.display = False
        else:
            self.selected_index = 0
            self._refresh_content()
            self.display = True

    def move_selection(self, up: bool = True) -> None:
        if not self.filtered_cmds:
            return
        n = len(self.filtered_cmds)
        self.selected_index = (self.selected_index + (-1 if up else 1)) % n
        self._refresh_content()

    def get_selected(self) -> Optional[str]:
        if self.filtered_cmds and 0 <= self.selected_index < len(self.filtered_cmds):
            return self.filtered_cmds[self.selected_index][0]
        return None


# ---------------------------------------------------------------------------
# Main Dashboard App
# ---------------------------------------------------------------------------
class AskGemDashboard(App):
    """AskGem TUI — Push-Layout, stable on Windows."""

    CSS = GLOBAL_CSS
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+l", "clear", "Clear"),
        ("f12", "toggle_output", "Toggle Output"),
        ("up", "palette_up", "Prev Cmd"),
        ("down", "palette_down", "Next Cmd"),
    ]

    def __init__(self, agent) -> None:
        super().__init__()
        self.agent = agent
        self.title = f"AskGem v{__version__}"

        from .ui_adapters import TUIToolUIAdapter

        self.agent.ui_adapter = TUIToolUIAdapter(
            log_callback=self.log_output,
            confirm_callback=self.request_confirmation,
        )
        self.agent.dispatcher.ui = self.agent.ui_adapter

        from ..agent.core.commands import COMMAND_METADATA

        self.commands_meta = COMMAND_METADATA
        self.current_response: str = ""

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="screen-wrapper"):
            with Horizontal(id="main-container"):
                self.sidebar = Sidebar()
                yield self.sidebar

                with Vertical(id="chat-area"):
                    self.chat_log = RichLog(
                        highlight=True, markup=True, id="chat-history"
                    )
                    yield self.chat_log
                    self.streaming_response = Static("", id="streaming-response")
                    yield self.streaming_response

                # Output pane: hidden by default, toggled with F12
                self.output_log = RichLog(
                    highlight=True, markup=True, id="output-pane"
                )
                yield self.output_log

            self.palette = CommandPalette(self.commands_meta)
            yield self.palette

            with Vertical(id="bottom-bar"):
                yield Input(
                    placeholder=_("dashboard.prompt_placeholder"),
                    tooltip=_("dashboard.prompt_tooltip"),
                    id="prompt-input",
                )
                self.dashboard_footer = DashboardFooter()
                yield self.dashboard_footer

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------
    def on_mount(self) -> None:
        self.agent.set_status_logger(self.log_output)
        self.chat_log.write(
            f"\n[bold #FBBC05]{_('startup.welcome', version=__version__)}[/]"
        )
        self._update_metrics()
        self.set_interval(5.0, self._update_mission_display)
        self.init_api()

    @work(exclusive=True)
    async def init_api(self) -> None:
        """Initializes the Gemini API in the background and restores last session."""
        p_in = self.query_one("#prompt-input", Input)
        p_in.disabled = True
        p_in.placeholder = _("dashboard.prompt_thinking")
        self.sidebar.update_context(self.agent.model_name, _("dashboard.sidebar.init"))

        try:
            if await self.agent.setup_api(interactive=False):
                sessions = self.agent.history.list_sessions()
                if sessions:
                    last = sessions[-1]
                    hist = self.agent.history.load_session(last)
                    if hist:
                        try:
                            # Restoration logic updated for the new session refactor
                            self.agent.session.chat_session = self.agent.session.client.aio.chats.create(
                                model=self.agent.model_name,
                                config=self.agent._build_config(),
                                history=hist,
                            )
                            self.chat_log.write(
                                f"\n[bold #6366f1]{_('startup.resuming_session', session=last)}[/]"
                            )
                            # Populate UI with historic messages
                            for msg in hist:
                                role = _("engine.you") if msg.role == "user" else "AskGem"
                                txt = "\n".join(p.text for p in msg.parts if p.text)
                                if txt:
                                    self.chat_log.write(self.render_message(role, txt))
                        except Exception as chat_err:
                            self.log_output(f"[bold red]WARNING:[/] Failed to resume session: {chat_err}")

                self.sidebar.update_context(
                    self.agent.model_name, self.agent.edit_mode
                )
                self._update_mission_display()
                self.chat_log.write(
                    f"\n[bold #34A853][OK] {_('startup.connected')}[/]"
                )
            else:
                # If setup_api fails, it means the API key is missing or invalid
                self.chat_log.write(f"\n[error][X] {_('error.api_setup_failed')}[/error]")
                self.sidebar.update_context(self.agent.model_name, _("dashboard.sidebar.auth_error"))
        except Exception as e:
            error_msg = f"API initialization error: {str(e)}"
            self.chat_log.write(f"\n[error][X] {error_msg}.[/error]")
            self.log_output(f"[bold red]CRITICAL:[/] {error_msg}")
            self.sidebar.update_context("N/A", _("dashboard.sidebar.error"))
        finally:
            p_in.placeholder = _("dashboard.prompt_placeholder")
            p_in.disabled = False
            p_in.focus()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _update_mission_display(self) -> None:
        try:
            # Using refactored agent.context for mission access
            m = self.agent.context.mission.read_missions()
            if not m:
                self.sidebar.update_mission(_("dashboard.sidebar.no_mission"))
                return

            # Extract just the tasks part for the sidebar if it's too long
            if "## Tasks" in m:
                parts = m.split("## Tasks")
                m = parts[1].strip() if len(parts) > 1 else parts[0].strip()

            self.sidebar.update_mission(m)
        except FileNotFoundError:
            self.sidebar.update_mission(_("dashboard.sidebar.mission_not_found"))
        except Exception as e:
            self.log_output(f"[bold red]ERROR:[/] Mission read failure: {str(e)}")
            self.sidebar.update_mission(_("dashboard.sidebar.mission_error"))

    def render_message(self, author: str, content: str) -> Table:
        """Creates a 2-column table for hanging-indent style chat messages."""
        table = Table.grid(expand=True)
        table.add_column(width=12)  # Author column
        table.add_column()  # Body column

        tag = (
            f"[bold #6366f1]{author}[/bold #6366f1]"
            if author == "AskGem"
            else f"[bold #94a3b8]{author}[/bold #94a3b8]"
        )
        table.add_row(tag, Markdown(content))
        return table

    def _update_metrics(self) -> None:
        self.sidebar.update_stats(self.agent.metrics.get_summary())
        self.dashboard_footer.update_info(
            stats=(
                f"In: {self.agent.metrics.total_prompt_tokens}"
                f" | Out: {self.agent.metrics.total_candidate_tokens}"
            ),
            model=self.agent.model_name,
            mode=self.agent.edit_mode,
        )

    # ------------------------------------------------------------------
    # Input events
    # ------------------------------------------------------------------
    @on(Input.Changed, "#prompt-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        self.palette.update_filter(event.value)

    def action_palette_up(self) -> None:
        if self.palette.display:
            self.palette.move_selection(up=True)

    def action_palette_down(self) -> None:
        if self.palette.display:
            self.palette.move_selection(up=False)

    @on(Input.Submitted, "#prompt-input")
    async def handle_prompt(self, event: Input.Submitted) -> None:
        val = event.value.strip()

        # Palette autocomplete takes priority
        if self.palette.display:
            sel = self.palette.get_selected()
            if sel:
                event.input.value = sel
                self.palette.display = False
                return

        if not val:
            return

        event.input.value = ""
        self.palette.display = False

        if val.lower() in ("exit", "quit", "q"):
            self.exit()
            return

        self.chat_log.write(self.render_message(_("engine.you"), val))

        if val.startswith("/"):
            event.input.disabled = True
            try:
                res = await self.agent.commands.execute(val)
                if res:
                    if isinstance(res, str):
                        self.chat_log.write(self.render_message("AskGem", res))
                    else:
                        self.chat_log.write(res)
                if val.lower() == "/clear":
                    self.action_clear()
                self._update_metrics()
            finally:
                event.input.disabled = False
                event.input.focus()
            return

        self.run_agent_turn(val)

    # ------------------------------------------------------------------
    # Agent turn (streaming)
    # ------------------------------------------------------------------
    @work(exclusive=True)
    async def run_agent_turn(self, val: str) -> None:
        p_in = self.query_one("#prompt-input", Input)
        p_in.disabled = True
        p_in.placeholder = _("dashboard.prompt_thinking")
        self.current_response = ""
        self.streaming_response.display = True

        def cb(chunk: str) -> None:
            self.current_response += chunk
            self.streaming_response.update(self.current_response)

        try:
            await self.agent._stream_response(val, callback=cb)
            self._update_metrics()
            self.chat_log.write(
                self.render_message("AskGem", self.current_response)
            )
        except Exception as exc:
            self.chat_log.write(
                f"\n[bold red]Error:[/bold red] {escape(str(exc))}"
            )
        finally:
            self.streaming_response.display = False
            self.streaming_response.update("")
            p_in.placeholder = _("dashboard.prompt_placeholder")
            p_in.disabled = False
            p_in.focus()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_clear(self) -> None:
        self.chat_log.clear()
        self.output_log.clear()
        self.notify(_("cmd.clear.subtitle"), title=_("cmd.clear.success"), severity="information")

    def action_toggle_output(self) -> None:
        pane = self.query_one("#output-pane")
        pane.display = not pane.display

    # ------------------------------------------------------------------
    # Callbacks wired from TUIToolUIAdapter
    # ------------------------------------------------------------------
    def log_output(self, msg: str, level: str = "info") -> None:
        if not hasattr(self, "output_log"):
            return
        color = {
            "info": "#6366f1",
            "success": "#22c55e",
            "warning": "#eab308",
            "error": "#ef4444",
        }.get(level, "#94a3b8")
        self.output_log.write(f"[bold {color}]OP[/bold] {escape(msg)}")

    async def request_confirmation(
        self,
        msg: str,
        detail: Optional[str] = None,
        severity: str = "info",
    ) -> bool:
        return bool(
            await self.push_screen_wait(ConfirmationModal(msg, detail, severity))
        )
