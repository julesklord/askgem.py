"""
UI implementations of the ToolUIAdapter.
Handles terminal-specific and TUI-specific rendering and interactive prompts.
"""

import asyncio
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

from ..agent.ui_interface import ToolUIAdapter
from ..core.i18n import _
from .console import console


class RichToolUIAdapter(ToolUIAdapter):
    """Adapts tool interaction requests to the Rich console/terminal."""

    def __init__(self):
        self._live_output = None
        self._output_buffer = ""

    async def confirm_action(self, message: str, detail: str | None = None, severity: str = "info") -> bool:
        """Prompts the user for confirmation using Rich.Prompt."""
        # Ensure any live stream is stopped before prompting
        self._stop_live()
        
        style = {"info": "blue", "warning": "yellow", "error": "red"}.get(severity, "blue")
        console.print(f"\n[bold {style}]SAFE CHECK[/]")
        console.print(f"{message}")
        if detail:
            console.print(detail)
            
        return await asyncio.to_thread(Confirm.ask, "Allow execution?")

    def log_status(self, message: str, level: str = "info") -> None:
        """Logs status updates to the console."""
        # Stop live if a new status comes in (completion or error)
        self._stop_live()
        
        style = {
            "info": "#4285F4",
            "success": "success",
            "warning": "warning",
            "error": "error",
        }.get(level, "dim")
        console.print(f"[{style}]{message}[/{style}]")

    def stream_output(self, text: str) -> None:
        """Sends partial output to a live terminal panel."""
        if not self._live_output:
            self._output_buffer = ""
            self._live_output = Live(
                self._build_panel(""),
                console=console,
                refresh_per_second=10,
                transient=True
            )
            self._live_output.start()

        self._output_buffer += text
        # Keep only the last 15 lines for the live view to avoid scrolling issues
        lines = self._output_buffer.splitlines()[-15:]
        display_text = "\n".join(lines)
        self._live_output.update(self._build_panel(display_text))

    def _build_panel(self, content: str) -> Panel:
        return Panel(
            Text(content, style="dim italic"),
            title="[bold blue]Command Output[/bold blue]",
            border_style="blue",
            subtitle="[dim]Press Ctrl+C to stop (if supported)[/dim]",
            padding=(0, 1)
        )

    def _stop_live(self) -> None:
        if self._live_output:
            self._live_output.stop()
            self._live_output = None
            self._output_buffer = ""


class TUIToolUIAdapter(ToolUIAdapter):
    """Adapts tool interaction requests to the Textual Dashboard UI."""

    def __init__(self, log_callback, confirm_callback):
        """Initializes the TUI adapter with callbacks.
        Args:
            log_callback: Callable[[str, str], None] to log status.
            confirm_callback: Callable[[str, Optional[str]], bool] (async) to prompt for confirmation.
        """
        self._log_cb = log_callback
        self._confirm_cb = confirm_callback

    async def confirm_action(self, message: str, detail: str | None = None, severity: str = "info") -> bool:
        """Prompts for user confirmation via the TUI callback."""
        if self._confirm_cb:
            return await self._confirm_cb(message, detail)
        # Fallback if no callback provided (security: default to deny)
        return False

    def log_status(self, message: str, level: str = "info") -> None:
        """Logs status updates to the TUI activity log."""
        if self._log_cb:
            # Re-map levels to colors if needed, but Dashboard handles it via message prefixes
            self._log_cb(message, level)

    def stream_output(self, text: str) -> None:
        """TUI streaming not yet implemented (Dashbaord is deprecated)."""
        pass
