"""
Token-level streaming renderer for real-time token-by-token output.

Ponytail: minimal implementation, stdlib only, no new deps.
"""

import asyncio
import time
from typing import Any

from rich.console import Console


class TokenBufferRenderer:
    """
    Renders tokens as they arrive with minimal latency.
    - No buffering: each chunk renders immediately
    - Small fixed delay (8ms) to avoid overwhelming terminal
    - Handles markdown/code-block detection incrementally
    """

    def __init__(
        self,
        console: Console,
        min_delay_ms: float = 8.0,
        theme_brand_color: str = "#6366f1",
    ) -> None:
        self.console = console
        self.min_delay = min_delay_ms / 1000.0
        self.brand_color = theme_brand_color
        self._live: Any = None
        self._buffer = ""
        self._last_flush = 0.0
        self._in_code_block = False
        self._code_lang = ""
        self._code_buffer = ""
        self._flushed_count = 0

    def start(self) -> None:
        """Initialize live rendering."""
        from rich.live import Live
        from rich.text import Text

        self._buffer = ""
        self._last_flush = time.monotonic()
        self._flushed_count = 0

        self._live = Live(
            Text("", style=f"bold {self.brand_color}"),
            console=self.console,
            refresh_per_second=60,
            transient=True,
        )
        self._live.start()

    def push(self, chunk: str) -> None:
        """Push a token chunk - renders immediately if delay elapsed."""
        self._buffer += chunk
        now = time.monotonic()

        # Check for code block boundaries
        if "```" in self._buffer and not self._in_code_block:
            # Find the code block start
            idx = self._buffer.find("```")
            if idx >= 0:
                pre = self._buffer[:idx]
                if pre:
                    self._render_text(pre)
                self._buffer = self._buffer[idx + 3 :]
                # Extract language
                nl = self._buffer.find("\n")
                if nl > 0:
                    self._code_lang = self._buffer[:nl].strip()
                    self._buffer = self._buffer[nl + 1 :]
                else:
                    self._code_lang = "text"
                self._in_code_block = True
                self._code_buffer = ""
                return

        if self._in_code_block and "```" in self._buffer:
            # Code block ended
            idx = self._buffer.find("```")
            self._code_buffer += self._buffer[:idx]
            self._render_code(self._code_buffer, self._code_lang)
            self._buffer = self._buffer[idx + 3 :]
            self._in_code_block = False
            self._code_buffer = ""
            self._code_lang = ""
            return

        if self._in_code_block:
            self._code_buffer += self._buffer
            self._buffer = ""
            # Periodically render code block as it grows
            if now - self._last_flush >= self.min_delay:
                self._render_code(self._code_buffer, self._code_lang)
                self._last_flush = now
            return

        # Regular text - flush on delay
        if now - self._last_flush >= self.min_delay and self._buffer:
            self._render_text(self._buffer)
            self._buffer = ""
            self._last_flush = now

    def flush(self) -> None:
        """Flush remaining buffer."""
        if self._in_code_block and self._code_buffer:
            self._render_code(self._code_buffer, self._code_lang)
        elif self._buffer:
            self._render_text(self._buffer)
        self._buffer = ""
        self._code_buffer = ""

    def stop(self, final_text: str = "") -> None:
        """Stop live rendering, leave final content in terminal."""
        self.flush()
        if self._live:
            self._live.stop()
            self._live = None

    def _render_text(self, text: str) -> None:
        """Render plain/markdown text incrementally."""
        from rich.text import Text

        if self._live and self._live.renderable:
            current = getattr(self._live.renderable, "plain", "") if hasattr(self._live.renderable, "plain") else str(self._live.renderable)
            new_text = Text(current + text, style=f"bold {self.brand_color}")
            self._live.update(new_text)
        else:
            self._live.update(Text(text, style=f"bold {self.brand_color}"))

    def _render_code(self, code: str, lang: str) -> None:
        """Render growing code block."""
        from rich.syntax import Syntax

        syntax = Syntax(code, lang, theme="monokai", line_numbers=True, padding=(0, 1))
        if self._live:
            self._live.update(syntax)