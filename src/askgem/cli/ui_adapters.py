"""
UI implementations of the ToolUIAdapter.
Handles terminal-specific and TUI-specific rendering and interactive prompts.
"""

import asyncio

from rich.prompt import Confirm

from ..agent.ui_interface import ToolUIAdapter
from ..core.i18n import _
from .console import console


class RichToolUIAdapter(ToolUIAdapter):
    """Adapts tool interaction requests to the Rich console/terminal."""

    async def confirm_action(self, message: str, detail: str | None = None) -> bool:
        """Prompts the user for confirmation using Rich.Prompt."""
        console.print(f"\n[warning]{_('tool.action_req')}[/warning] {message}")
        if detail:
            console.print(detail)
        # Confirm.ask is blocking, so we wrap it in to_thread
        return await asyncio.to_thread(Confirm.ask, _("tool.confirm.edit"))

    def log_status(self, message: str, level: str = "info") -> None:
        """Logs status updates to the console."""
        style = {
            "info": "#4285F4",
            "success": "success",
            "warning": "warning",
            "error": "error",
        }.get(level, "dim")
        console.print(f"[{style}]{message}[/{style}]")


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

    async def confirm_action(self, message: str, detail: str | None = None) -> bool:
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
