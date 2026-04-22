"""
cli/renderer.py — Rich-based streaming renderer for AskGem.

Design philosophy: Gemini CLI style with professional styling.
  - Stream raw text live while generating (fast, zero flicker).
  - On completion, re-render the full response with proper structure:
      · <think>/<thinking> blocks  → dim panel
      · ```lang code blocks        → Syntax highlighted with line numbers
      · Remaining markdown         → rich.Markdown
  - Tool calls and status messages get their own styled callouts.
  - Everything scrolls. No layout, no widgets, no overhead.
  - CSS-inspired theme system for professional appearance.
"""

from __future__ import annotations

import getpass
import re
import time

from rich.console import Console
from rich.control import Control
from rich.live import Live
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.text import Text

from .themes import ThemeConfig, get_theme

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
    Stateful renderer for one conversation session with professional styling.

    Features:
    - CSS-inspired theme system
    - Streaming with configurable speed
    - Proper type hints throughout
    - Better error handling
    """

    def __init__(
        self,
        console: Console,
        theme_name: str = "indigo",
        stream_mode: str = "continuous",
        stream_delay: float = 0.01,
    ) -> None:
        """Initialize renderer with theme and streaming configuration.

        Args:
            console: Rich console instance
            theme_name: Theme name (indigo, emerald, cyberpunk, etc.)
            stream_mode: "continuous" or "transient"
            stream_delay: Delay in seconds between stream updates (default 0.01 = 10ms)
        """
        self.console: Console = console
        self._live: Live | None = None
        self._streaming: bool = False
        self._last_text: str = ""
        self._stream_delay: float = stream_delay
        self.username: str = getpass.getuser()
        self.stream_mode: str = stream_mode
        self._label_printed: bool = False

        # Load theme
        self.theme: ThemeConfig = get_theme(theme_name)
        self._setup_colors()
        self.artifacts: list[tuple[str, str]] = []  # List of (tool_name, full_content)
        self._status = None

    def reset_turn(self) -> None:
        """Resets flags for a new user turn."""
        self._label_printed = False

    def _setup_colors(self) -> None:
        """Setup color shortcuts from theme."""
        self.C_BRAND: str = self.theme.brand_primary
        self.C_SUCCESS: str = self.theme.success
        self.C_ERROR: str = self.theme.error
        self.C_DIM: str = self.theme.text_dim
        self.C_THINK: str = self.theme.think_color
        self.C_USER: str = self.theme.text_secondary
        self.C_TOOL: str = self.theme.warning

    def apply_theme(self, name: str) -> None:
        """Switch theme by name."""
        self.theme = get_theme(name)
        self._setup_colors()

    # ------------------------------------------------------------------
    # Welcome / session header
    # ------------------------------------------------------------------
    def print_welcome(self, version: str, model: str, mode: str) -> None:
        """Print welcome banner."""
        self.console.print()
        header = Text.from_markup(
            f" [bold {self.C_BRAND}]AskGem[/] [dim]v{version}[/] "
            f" [dim]-[/] [bold #cbd5e1]{model}[/] [dim]-[/] [dim]{mode}[/] "
        )
        self.console.print(header, justify="center")
        self.console.print(
            "  [dim]Type [bold white]/help[/] for commands - [bold white]Ctrl+C[/] to exit[/dim]\n",
            justify="center",
        )

    # ------------------------------------------------------------------
    # User turn header
    # ------------------------------------------------------------------
    def print_user(self, text: str) -> None:
        """Print user input with styling."""
        # Move up 1 line using compatible Rich control
        self.console.control(Control.move(0, -1))
        # Clear the line by printing spaces
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
        self.console.print(f"\n [bold {self.C_BRAND}]* @askgem[/]")

    def start_thinking(self) -> None:
        """Starts a visual spinner indicating the agent is thinking."""
        if not self._status:
            from rich.status import Status

            # We use text_secondary or think_color for the spinner text
            self._status = Status(
                f"[bold {self.C_THINK}]AskGem is thinking...[/]", console=self.console, spinner="dots"
            )
            self._status.start()

    def stop_thinking(self) -> None:
        """Stops the visual spinner."""
        if getattr(self, "_status", None):
            self._status.stop()
            self._status = None

    def print_thought(self, text: str) -> None:
        """Renders the reasoning process in a subtle, minimalist style."""
        if not text.strip():
            return

        # Subtle vertical line style like modern dev tools
        thought_text = Text()
        for line in text.strip().splitlines():
            thought_text.append("  [dim]|[/] ", style=self.C_DIM)
            thought_text.append(line, style=f"italic {self.C_THINK}")
            thought_text.append("\n")

        self.console.print(thought_text)

    # ------------------------------------------------------------------
    # Live streaming (raw text, no parsing — fast, zero flicker)
    # ------------------------------------------------------------------
    def start_stream(self) -> None:
        """Start streaming output.
        Always uses transient=True to avoid doubling output when structured rendering is applied at the end.
        """
        if not self._label_printed:
            self._print_agent_label()
            self._label_printed = True

        self._live = Live(
            Text("▌", style=f"bold {self.C_BRAND}"),
            console=self.console,
            refresh_per_second=12,
            transient=True,
        )
        self._live.start()
        self._streaming = True
        self._last_stream_time: float = time.time()

    def update_stream(self, accumulated: str) -> None:
        """Call with the full accumulated text so far."""
        # Professional pacing (Speed Control)
        now = time.time()
        elapsed = now - self._last_stream_time
        if elapsed < self._stream_delay:
            time.sleep(self._stream_delay - elapsed)

        self._last_text = accumulated
        if self._live and self._streaming:
            preview = Text(accumulated[-2000:] if len(accumulated) > 2000 else accumulated)
            preview.append(" ▌", style=f"bold {self.C_BRAND}")
            self._live.update(preview)

        self._last_stream_time = time.time()

    def end_stream(self, full_text: str | None = None) -> None:
        """Stop Live and render the structured final response.

        Args:
            full_text: Optional full text to render (uses _last_text if None)
        """
        if not self._streaming:
            return

        final_text: str = full_text if full_text is not None else self._last_text

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
        """Render response with proper structure (think blocks, code, markdown).

        Args:
            text: Full response text with optional think/code blocks
        """
        if not text.strip():
            return

        segments: list = _parse_segments(text)

        for seg in segments:
            kind: str = seg[0]

            if kind == "think":
                # Subtle side-line for reasoning blocks
                thought_text: Text = Text()
                for line in seg[1].strip().splitlines():
                    thought_text.append("  [dim]|[/] ", style=self.C_DIM)
                    thought_text.append(line, style=f"italic {self.C_THINK}")
                    thought_text.append("\n")
                self.console.print(thought_text)

            elif kind == "code":
                lang: str = seg[1]
                body: str = seg[2]
                self.console.print(
                    Syntax(
                        body,
                        lang,
                        theme=self.theme.code_theme,
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
    def print_tool_call(self, tool_name: str, args: dict[str, str]) -> None:
        """Visual notification that a tool is being invoked.

        Args:
            tool_name: Name of the tool being executed
            args: Dictionary of arguments
        """
        args_str: str = ", ".join([f"{k}={v}" for k, v in args.items()])
        self.console.print(
            f" [bold {self.C_TOOL}]TOOL EXECUTING:[/] [bold]{tool_name}[/] [dim]({escape(args_str)})[/dim]"
        )

    def print_tool_result(self, ok: bool, content: str, tool_name: str | None = None) -> None:
        """Visual summary of a tool's output.

        Args:
            ok: Whether the tool succeeded
            content: The output content
            tool_name: Optional name of the tool
        """
        # Store full artifact for later expansion
        artifact_id = f"#{len(self.artifacts) + 1}"
        self.artifacts.append((tool_name or "tool", content))

        color: str = self.C_SUCCESS if ok else self.C_ERROR
        icon: str = "[OK]" if ok else "[ERROR]"
        title: str = f"[{color}]{icon} {tool_name or 'tool'} output[/{color}] [dim]({artifact_id})[/dim]"
        preview: str = content[:200] + "..." if len(content) > 200 else content

        self.console.print(
            Panel(
                Text(preview, style="dim"),
                title=title,
                border_style="dim",
                padding=(0, 1),
                subtitle="[dim italic]Press Ctrl+O to expand last artifact[/dim italic]",
            )
        )

    def expand_artifact(self, index: int = -1) -> None:
        """Displays the full content of a stored artifact with enhanced formatting."""
        from rich.markdown import Markdown
        from rich.syntax import Syntax

        if not self.artifacts:
            self.print_warning("No tool artifacts to expand.")
            return

        try:
            actual_idx = index if index >= 0 else len(self.artifacts) + index
            if actual_idx < 0 or actual_idx >= len(self.artifacts):
                self.print_error(f"Artifact {index} not found.")
                return

            name, full_content = self.artifacts[actual_idx]
            artifact_id = f"#{actual_idx + 1}"

            # 1. Prepare renderable based on tool type
            renderable = None

            # Code-heavy tools
            if name in ["read_file", "edit_file", "write_file", "execute_bash", "execute_command"]:
                # Try to guess language for syntax highlighting
                # For bash output, it's mostly text, but Syntax helps with ANSI/structure
                renderable = Syntax(
                    full_content,
                    "bash" if "bash" in name or "command" in name else "python",
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=True,
                )
            # Markdown-like content or content with Rich markup (like LSP diagnostics)
            elif full_content.strip().startswith("#") or "```" in full_content or "[LSP DIAGNOSTICS" in full_content:
                # If it's a tool result with diagnostics, we want to see the markup colors
                renderable = Markdown(full_content) if "#" in full_content else Text.from_markup(full_content)
            # Generic tool output
            else:
                # Use Text object to handle plain strings safely
                renderable = Text(full_content)

            self.console.print()
            self.console.print(
                Panel(
                    renderable,
                    title=f"[bold {self.C_BRAND}]Expanded Artifact {artifact_id} ({name})[/]",
                    border_style=self.C_BRAND,
                    padding=(1, 2),
                    subtitle="[dim italic]End of expanded content (Esc to close pager if active)[/dim italic]",
                )
            )
        except Exception as e:
            self.print_error(f"Error expanding artifact: {e}")

    # ------------------------------------------------------------------
    # Inline metrics (after each turn)
    # ------------------------------------------------------------------
    def print_metrics(self, summary: str) -> None:
        """Store metrics to be displayed by the turn divider.

        Args:
            summary: Metrics summary string
        """
        self._last_metrics: str = summary

    def print_command_output(self, result: str | object | None) -> None:
        """Print output from /slash commands.

        Args:
            result: Output from command (string, Rich renderable, or None)
        """
        if result is None or result is True:
            return
        if isinstance(result, str):
            self.console.print(result)
        else:
            self.console.print(result)

    def print_turn_divider(self) -> None:
        """Print sophisticated divider with integrated metrics."""
        metrics: str = getattr(self, "_last_metrics", "")
        self._last_metrics = ""

        if metrics:
            self.console.print(f"\n[dim]{'-' * 20} {metrics} {'-' * 20}[/dim]\n", justify="center")
        else:
            self.console.print(f"\n[dim]{'-' * 50}[/dim]\n", justify="center")
        self.console.print()

    # ------------------------------------------------------------------
    # Error / warning
    # ------------------------------------------------------------------
    def print_error(self, msg: str) -> None:
        """Print error message with Rich markup support.

        Args:
            msg: Error message (supports Rich markup like [bold], [color], etc)
        """
        self.console.print(f"\n  [bold {self.C_ERROR}]ERROR:[/bold {self.C_ERROR}]  {msg}")

    def print_warning(self, msg: str) -> None:
        """Print warning message with Rich markup support.

        Args:
            msg: Warning message (supports Rich markup like [bold], [color], etc)
        """
        self.console.print(f"\n  [bold {self.C_TOOL}]WARNING:[/bold {self.C_TOOL}]  {msg}")

    async def ask_confirmation(self, tool_name: str, args: dict[str, str], warning: str = "") -> bool:
        """Ask user for permission to execute a tool.

        Args:
            tool_name: Name of the tool
            args: Tool arguments
            warning: Optional security warning message

        Returns:
            True if user approved, False otherwise
        """
        # Close live stream if active to allow clean prompt
        if self._live:
            self._live.stop()
            self._live = None

        if warning:
            self.console.print(
                Panel(
                    f"[bold white]{warning}[/bold white]",
                    title="[bold yellow]! SECURITY WARNING[/bold yellow]",
                    border_style="red",
                )
            )
        else:
            self.console.print(f"\n[bold {self.C_TOOL}]SAFE CHECK[/]")

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
    def print_goodbye(self, msg: str, session_id: str | None = None) -> None:
        """Print goodbye message with session info if provided.

        Args:
            msg: Goodbye message
            session_id: Current session ID to display and resume
        """
        self.console.print()
        self.console.print(f"[dim]{'-' * 50}[/dim]", justify="center")

        if session_id:
            self.console.print(f"  [dim]Session ID:[/dim] [bold {self.C_BRAND}]{session_id}[/]")
            self.console.print(f"  [dim]To resume: [bold white]askgem {session_id}[/][/dim]")

        self.console.print(f"  [dim]{msg}[/dim]\n")
