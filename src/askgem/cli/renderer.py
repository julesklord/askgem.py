"""
cli/renderer.py — Rich-based streaming renderer for AskGem.

Design philosophy: Gemini CLI style.
  - Stream raw text live while generating (fast, zero flicker).
  - On completion, re-render the full response with proper structure:
      · <think>/<thinking> blocks  → dim panel
      · ```lang code blocks        → Syntax highlighted with line numbers
      · Remaining markdown         → rich.Markdown
  - Tool calls and status messages get their own styled callouts.
  - Everything scrolls. No layout, no widgets, no overhead.
"""

from __future__ import annotations

import getpass
import re

from rich.console import Console
from rich.control import Control
from rich.live import Live
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text

# ---------------------------------------------------------------------------
# Segment parser
# ---------------------------------------------------------------------------
# Matches (in order of priority):
#   1. <think>...</think> or <thinking>...</thinking>  (Gemini 2.5 think tokens)
#   2. ```lang\n...```  code fences
_SEGMENT_RE = re.compile(
    r"(<think(?:ing)?>.*?</think(?:ing)?>)"  # group 1 — think block
    r"|"
    r"(```(\w*)\n?(.*?)(?:```|$))",  # group 2 — code fence, 3=lang, 4=body
    re.DOTALL,
)


def _parse_segments(text: str) -> list:
    """Split response text into typed segments for structured rendering."""
    segments = []
    cursor = 0

    for m in _SEGMENT_RE.finditer(text):
        # Plain text before this match
        if m.start() > cursor:
            plain = text[cursor : m.start()]
            if plain.strip():
                segments.append(("text", plain.strip()))

        if m.group(1):
            # Think block — strip tags, keep inner content
            inner = re.sub(r"</?think(?:ing)?>", "", m.group(1)).strip()
            if inner:
                segments.append(("think", inner))
        else:
            # Code fence
            lang = (m.group(3) or "text").strip() or "text"
            body = (m.group(4) or "").rstrip()
            segments.append(("code", lang, body))

        cursor = m.end()

    # Trailing plain text
    tail = text[cursor:].strip()
    if tail:
        segments.append(("text", tail))

    return segments


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class CliRenderer:
    """
    Stateful renderer for one conversation session.

    Usage:
        renderer = CliRenderer(console)
        renderer.print_welcome(version, model, mode)

        # Per turn:
        renderer.print_user(user_input)
        renderer.start_stream()          # begins Live context
        text_so_far = ""
        def cb(chunk):
            text_so_far += chunk        # accumulate in caller
            renderer.update_stream(text_so_far)
        await agent._stream_response(val, callback=cb)
        renderer.end_stream(full_text)  # stops Live, renders final
        renderer.print_metrics(summary)
    """

    # Integrated Theme System
    THEMES = {
        "indigo": {
            "brand": "#818cf8",
            "user": "#94a3b8",
            "tool": "#fbbf24",
            "success": "#4ade80",
            "error": "#f87171",
            "dim": "#475569",
            "think": "#64748b",
        },
        "emerald": {
            "brand": "#34d399",
            "user": "#94a3b8",
            "tool": "#fbbf24",
            "success": "#10b981",
            "error": "#f43f5e",
            "dim": "#3f4f5f",
            "think": "#4b5563",
        },
        "crimson": {
            "brand": "#fb7185",
            "user": "#94a3b8",
            "tool": "#fbbf24",
            "success": "#10b981",
            "error": "#e11d48",
            "dim": "#4c1d1d",
            "think": "#991b1b",
        },
        "amber": {
            "brand": "#fbbf24",
            "user": "#94a3b8",
            "tool": "#6366f1",
            "success": "#10b981",
            "error": "#ef4444",
            "dim": "#451a03",
            "think": "#78350f",
        },
        "cyberpunk": {
            "brand": "#f0abfc",
            "user": "#2dd4bf",
            "tool": "#fbbf24",
            "success": "#4ade80",
            "error": "#f43f5e",
            "dim": "#1e1b4b",
            "think": "#4c1d95",
        },
    }

    def __init__(self, console: Console, theme_name: str = "indigo") -> None:
        self.console = console
        self._live: Live | None = None
        self._streaming = False
        self._last_text = ""
        self.username = getpass.getuser()
        self.apply_theme(theme_name)

    def apply_theme(self, name: str) -> None:
        """Applies a color palette by name."""
        theme = self.THEMES.get(name, self.THEMES["indigo"])
        self.C_BRAND = theme["brand"]
        self.C_USER = theme["user"]
        self.C_TOOL = theme["tool"]
        self.C_SUCCESS = theme["success"]
        self.C_ERROR = theme["error"]
        self.C_DIM = theme["dim"]
        self.C_THINK = theme["think"]

    # ------------------------------------------------------------------
    # Welcome / session header
    # ------------------------------------------------------------------
    def print_welcome(self, version: str, model: str, mode: str) -> None:
        self.console.print()
        # Header with a modern, centered rule
        header = Text.from_markup(
            f" [bold {self.C_BRAND}]AskGem[/] [dim]v{version}[/] "
            f" [dim]•[/] [bold #cbd5e1]{model}[/] [dim]•[/] [dim]{mode}[/] "
        )
        self.console.print(Rule(header, style=self.C_DIM))
        self.console.print(
            "  [dim]Type [bold white]/help[/] for commands • [bold white]Ctrl+C[/] to exit[/dim]\n", justify="center"
        )

    # ------------------------------------------------------------------
    # User turn header
    # ------------------------------------------------------------------
    def print_user(self, text: str) -> None:
        # Move up 1 line using compatible Rich control
        self.console.control(Control.move(0, -1))
        # Clear the line by printing spaces (most compatible way across Windows terminals)
        self.console.print(" " * (self.console.width - 1), end="\r")

        self.console.print()
        self.console.print(
            Panel(
                Text(text, style=f"italic {self.C_USER}"),
                title=f"[bold {self.C_USER}]@{self.username}[/]",
                title_align="left",
                border_style=self.C_DIM,
                padding=(0, 2),
            )
        )

    # ------------------------------------------------------------------
    # Agent label (printed once before streaming starts)
    # ------------------------------------------------------------------
    def _print_agent_label(self) -> None:
        self.console.print(f"\n [bold {self.C_BRAND}]✨ @askgem[/]")

    def print_thought(self, text: str) -> None:
        """Renders the reasoning process in a subtle, minimalist style."""
        if not text.strip():
            return

        # Subtle vertical line style like modern dev tools
        thought_text = Text()
        for line in text.strip().splitlines():
            thought_text.append("  [dim]│[/] ", style=self.C_DIM)
            thought_text.append(line, style=f"italic {self.C_THINK}")
            thought_text.append("\n")

        self.console.print(thought_text)

    # ------------------------------------------------------------------
    # Live streaming (raw text, no parsing — fast, zero flicker)
    # ------------------------------------------------------------------
    def start_stream(self) -> None:
        self._print_agent_label()
        self._live = Live(
            Text("▌", style=f"bold {self.C_BRAND}"),
            console=self.console,
            refresh_per_second=12,
            transient=True,  # erased after end_stream, replaced by final render
        )
        self._live.start()
        self._streaming = True

    def update_stream(self, accumulated: str) -> None:
        """Call with the full accumulated text so far."""
        self._last_text = accumulated
        if self._live and self._streaming:
            preview = Text(accumulated[-2000:] if len(accumulated) > 2000 else accumulated)
            preview.append(" ▌", style=f"bold {self.C_BRAND}")
            self._live.update(preview)

    def end_stream(self, full_text: str | None = None) -> None:
        """Stop Live and render the structured final response."""
        if not self._streaming:
            return

        final_text = full_text if full_text is not None else self._last_text

        if self._live:
            self._live.stop()
            self._live = None
        self._streaming = False

        if final_text:
            self._render_response(final_text)
            self._last_text = ""

    # ------------------------------------------------------------------
    # Structured response renderer
    # ------------------------------------------------------------------
    def _render_response(self, text: str) -> None:
        if not text.strip():
            return

        segments = _parse_segments(text)

        for seg in segments:
            kind = seg[0]

            if kind == "think":
                # Subtle side-line for reasoning blocks
                thought_text = Text()
                for line in seg[1].strip().splitlines():
                    thought_text.append("  [dim]│[/] ", style=self.C_DIM)
                    thought_text.append(line, style=f"italic {self.C_THINK}")
                    thought_text.append("\n")
                self.console.print(thought_text)

            elif kind == "code":
                lang, body = seg[1], seg[2]
                self.console.print(
                    Syntax(
                        body,
                        lang,
                        theme="monokai",
                        line_numbers=True,
                        word_wrap=True,
                        padding=(0, 1),
                    )
                )

            elif kind == "text":
                # Render as Markdown so *bold*, headers, lists, links all work
                try:
                    self.console.print(Markdown(seg[1]))
                except Exception:
                    self.console.print(seg[1])

    # ------------------------------------------------------------------
    # Tool call notifications
    # ------------------------------------------------------------------
    def print_tool_call(self, tool_name: str, args: dict) -> None:
        """Visual notification that a tool is being invoked."""
        args_str = ", ".join([f"{k}={v}" for k, v in args.items()])
        self.console.print(
            f" [bold {self.C_TOOL}]⚙  EXECUTING:[/] [bold]{tool_name}[/] [dim]({escape(args_str)})[/dim]"
        )

    def print_tool_result(self, ok: bool, content: str) -> None:
        """Visual summary of a tool's output."""
        color = self.C_SUCCESS if ok else self.C_ERROR
        icon = "✓" if ok else "✗"

        # We show a preview if content is long
        preview = content[:200] + "..." if len(content) > 200 else content
        self.console.print(
            Panel(
                Text(preview, style="dim"),
                title=f"[{color}]{icon} tool output[/{color}]",
                border_style="dim",
                padding=(0, 1),
            )
        )

    # ------------------------------------------------------------------
    # Inline metrics (after each turn)
    # ------------------------------------------------------------------
    def print_metrics(self, summary: str) -> None:
        """Stores metrics to be displayed by the turn divider."""
        # This is now a no-op as metrics are integrated into print_turn_divider
        self._last_metrics = summary

    def print_command_output(self, result) -> None:
        """Prints output from /slash commands (Tables, Panels, or Strings)."""
        if result is None or result is True:
            return
        if isinstance(result, str):
            self.console.print(result)
        else:
            self.console.print(result)

    def print_turn_divider(self) -> None:
        """Prints a sophisticated divider with integrated metrics."""
        metrics = getattr(self, "_last_metrics", "")
        self._last_metrics = ""  # reset

        if metrics:
            # Format: ─────── Tokens: 123 | $0.0001 ───────
            self.console.print(Rule(Text.from_markup(f" [dim]{metrics}[/] "), style="#1e293b"))
        else:
            self.console.print(Rule(style="#1e293b"))
        self.console.print()

    # ------------------------------------------------------------------
    # Error / warning
    # ------------------------------------------------------------------
    def print_error(self, msg: str) -> None:
        error_text = Text()
        error_text.append("\n  ✗  Error: ", style=f"bold {self.C_ERROR}")
        error_text.append(msg)
        self.console.print(error_text)

    def print_warning(self, msg: str) -> None:
        warn_text = Text()
        warn_text.append("\n  ⚠  ", style=f"bold {self.C_TOOL}")
        warn_text.append(msg, style=f"bold {self.C_TOOL}")
        self.console.print(warn_text)

    async def ask_confirmation(self, tool_name: str, args: dict, warning: str = "") -> bool:
        """Asks the user for permission to execute a tool (Interactive)."""
        # Close live stream if active to allow clean prompt
        if self._live:
            self._live.stop()
            self._live = None

        if warning:
            self.console.print(Panel(
                f"[bold white]{warning}[/bold white]",
                title="[bold yellow]⚠️ SECURITY WARNING[/bold yellow]",
                border_style="red"
            ))
        else:
            self.console.print(f"\n[bold {self.C_TOOL}]🛡  SECURITY CHECK[/]")

        self.console.print(f"AskGem wants to use [bold]{tool_name}[/] with these parameters:")

        for k, v in args.items():
            # If it looks like code or long text, show it nicely
            val_str = str(v)
            if len(val_str) > 50 or "\n" in val_str:
                self.console.print(f"  [bold]{k}:[/]")
                lang = "python" if tool_name in ("write_file", "edit_file") else "text"
                self.console.print(Panel(Syntax(val_str, lang, theme="monokai"), border_style="dim"))
            else:
                self.console.print(f"  [bold]{k}:[/] [dim]{val_str}[/dim]")

        return Confirm.ask("\n[bold]Allow execution?[/bold]")

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    def print_goodbye(self, msg: str) -> None:
        self.console.print()
        self.console.print(Rule(style=self.C_DIM))
        self.console.print(f"  [dim]{escape(msg)}[/dim]\n")
