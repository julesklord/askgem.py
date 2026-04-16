"""
UI and Interaction interfaces for the agent.
Allows tools to request confirmations without being coupled to a specific TUI/CLI library.
"""

from typing import Protocol


class ToolUIAdapter(Protocol):
    """Protocol defining how the ToolDispatcher interacts with the user interface."""

    async def confirm_action(self, message: str, detail: str | None = None, severity: str = "info") -> bool:
        """Requests confirmation from the user for a potentially dangerous action.
        Args:
            message: The primary question/action to confirm.
            detail: Optional extra information (e.g. diff or content preview).
        Returns:
            bool: True if confirmed, False otherwise.
        """
        ...

    def log_status(self, message: str, level: str = "info") -> None:
        """Logs a status update or tool execution detail to the UI.
        Args:
            message: The content to display.
            level: The severity/type of the message (info, success, warning, error).
        """
        ...
