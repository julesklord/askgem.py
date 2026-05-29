"""
Interactive terminal input shell using prompt_toolkit.

Encapsulates advanced terminal features like key bindings, custom autocomplete,
multiline input support, and history, separating UI input loop concerns from the Agent core.
"""

from typing import Any

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.patch_stdout import patch_stdout
    HAS_PT = True
except ImportError:
    HAS_PT = False


class InteractiveShell:
    """Encapsulates the prompt_toolkit input session and terminal interactions."""

    def __init__(self, config=None):
        self.config = config
        self.session = None
        self._completer = None
        self._key_bindings = None

        if HAS_PT:
            self._key_bindings = KeyBindings()
            # Initialize the session with standard key bindings
            self.session = PromptSession(key_bindings=self._key_bindings)

    @property
    def has_interactive_features(self) -> bool:
        """Returns True if prompt_toolkit interactive features are available."""
        return HAS_PT and self.session is not None

    def set_completer(self, completer: Any) -> None:
        """Sets the active autocompleter dynamically."""
        self._completer = completer
        if self.session:
            self.session.completer = completer

    async def prompt_user(self, prompt_msg: Any, is_multiline: bool = False) -> str:
        """Prompts the user for interactive input with active completion."""
        if HAS_PT and self.session:
            try:
                # Use patch_stdout to keep printed output flowing cleanly
                with patch_stdout():
                    user_input = await self.session.prompt_async(prompt_msg, multiline=is_multiline)
                    return user_input.strip()
            except (EOFError, KeyboardInterrupt):
                raise KeyboardInterrupt()
        else:
            # Fallback to standard python input
            try:
                # If prompt_msg is prompt_toolkit's ANSI, it can be printed first
                # In standard fallback, rich prompt is printed by chat.py, so we just do input()
                return input().strip()
            except (EOFError, KeyboardInterrupt):
                raise KeyboardInterrupt()
