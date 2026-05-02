"""
cli/gem_renderer.py — Gem CLI-style persistent renderer.

Key differences from CliRenderer:
- transient=False → content persists in terminal scroll
- Incremental buffer commits → thoughts, code blocks committed as they complete
- Auto-flush for long sessions → prevents slow re-renders
"""

from __future__ import annotations

import getpass
import re
import time

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm
from rich.status import Status
from rich.syntax import Syntax
from rich.text import Text

from ..core.i18n import _
from .prompts import PromptEngine
from .themes import get_theme


# Icon system (reuse from renderer.py)
class _Icons:
    def __init__(self):
        self._unicode = True
        try:
            import sys

            if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
                self._unicode = False
        except Exception:
            self._unicode = False

    @property
    def brand(self) -> str:
        return "\u2726" if self._unicode else "*"

    @property
    def tool(self) -> str:
        return "\u26a1" if self._unicode else ">"

    @property
    def ok(self) -> str:
        return "\u2713" if self._unicode else "[OK]"

    @property
    def fail(self) -> str:
        return "\u2717" if self._unicode else "[ERR]"

    @property
    def warn(self) -> str:
        return "\u26a0" if self._unicode else "[!]"

    @property
    def cursor(self) -> str:
        return "\u258d" if self._unicode else "|"

    @property
    def hdash(self) -> str:
        return "\u2500" if self._unicode else "-"

    @property
    def vbar(self) -> str:
        return "\u2502" if self._unicode else "|"

    @property
    def dot(self) -> str:
        return "\u00b7" if self._unicode else "-"


icons = _Icons()


# Segment parser (reuse)
_SEGMENT_RE = re.compile(
    r"(<think(?:ing)?>.*?</think(?:ing)?>)" r"|" r"(```(\w*)\n?(.*?)(?:```|$))",
    re.DOTALL,
)


def _parse_segments(text: str) -> list:
    segments = []
    cursor = 0
    for m in _SEGMENT_RE.finditer(text):
        if m.start() > cursor:
            plain = text[cursor : m.start()]
            if plain.strip():
                segments.append(("text", plain.strip()))
        if m.group(1):
            inner = re.sub(r"</?think(?:ing)?>", "", m.group(1)).strip()
            if inner:
                segments.append(("think", inner))
        else:
            lang = (m.group(3) or "text").strip() or "text"
            body = (m.group(4) or "").rstrip()
            segments.append(("code", lang, body))
        cursor = m.end()
    tail = text[cursor:].strip()
    if tail:
        segments.append(("text", tail))
    return segments


class GemStyleRenderer:
    """Gem CLI-style renderer with persistent scroll buffer."""

    MAX_COMMITTED_LINES = 100
    MAX_ARTIFACTS = 50

    def __init__(
        self,
        console: Console,
        theme_name: str = "indigo",
        stream_mode: str = "continuous",
        stream_delay: float = 0.015,
    ) -> None:
        self.console = console
        self.committed_buffer = []
        self.live_text = ""
        self._live: Live | None = None
        self._streaming = False
        self._stream_delay = stream_delay
        self.username = getpass.getuser()
        self.stream_mode = stream_mode
        self._label_printed = False

        self.theme = get_theme(theme_name)
        self._setup_colors()

        self.prompt_engine = PromptEngine(self.theme)
        self.prompt_style = "atomic"

        self.artifacts = []
        self._last_metrics = ""
        self._last_stream_time = time.time()
        self.printed_count = 0  # Number of items in committed_buffer already printed definitively
        self._thinking_status: Status | None = None

    def _setup_colors(self) -> None:
        self.C_BRAND = self.theme.brand_primary
        self.C_SUCCESS = self.theme.success
        self.C_ERROR = self.theme.error
        self.C_DIM = self.theme.text_dim
        self.C_THINK = self.theme.think_color
        self.C_USER = self.theme.text_secondary
        self.C_TOOL = self.theme.warning

    def apply_theme(self, name: str) -> None:
        self.theme = get_theme(name)
        self._setup_colors()
        if hasattr(self, "prompt_engine"):
            self.prompt_engine.theme = self.theme

    def reset_turn(self) -> None:
        self._label_printed = False
        self.committed_buffer = []
        self.printed_count = 0
        self.stop_thinking()

    # ─────────────────────────────────────────────────────────────────
    # Core Rendering
    # ─────────────────────────────────────────────────────────────────

    def show_thinking(self) -> None:
        """Display a thinking spinner."""
        if self._thinking_status:
            return

        self._thinking_status = self.console.status(
            _("dashboard.prompt_thinking"),
            spinner="dots",
            spinner_style=f"bold {self.C_THINK}",
        )
        self._thinking_status.start()

    def stop_thinking(self) -> None:
        """Stop the thinking spinner."""
        if self._thinking_status:
            self._thinking_status.stop()
            self._thinking_status = None

    def _build_view(self, show_cursor: bool = True) -> Group:
        """Construct a Group with only the UNPRINTED committed content + live text."""
        items = list(self.committed_buffer[self.printed_count :])
        if self.live_text:
            cursor = f" {icons.brand}" if show_cursor else ""
            items.append(Text(self.live_text + cursor, style=f"bold {self.C_BRAND}"))
        return Group(*items)

    def _flush_if_needed(self) -> None:
        """If the buffer grows too large, print older lines definitively to the console."""
        if len(self.committed_buffer) > self.MAX_COMMITTED_LINES:
            self.console.print(f"[dim]{icons.hdash * 3} older output {icons.hdash * 3}[/dim]")
            for item in self.committed_buffer[:50]:
                self.console.print(item)
            self.committed_buffer = self.committed_buffer[50:]

    # ─────────────────────────────────────────────────────────────────
    # Streaming
    # ─────────────────────────────────────────────────────────────────

    def start_stream(self, is_natural: bool = False) -> None:
        """Initialize streaming WITHOUT transient mode — content persists in terminal."""
        if not self._label_printed:
            self._print_agent_label(is_natural=is_natural)
            self._label_printed = True

        # Do not clear committed_buffer here, only in reset_turn
        self.live_text = ""

        self._live = Live(
            self._build_view(),
            console=self.console,
            refresh_per_second=12,
            transient=True,  # ← Reset for definitive print in end_stream
        )
        self._live.start()
        self._streaming = True
        self._last_stream_time = time.time()

    def update_stream(self, chunk: str) -> None:
        now = time.time()
        elapsed = now - self._last_stream_time
        if elapsed < self._stream_delay:
            time.sleep(self._stream_delay - elapsed)

        # We expect accumulated text from ChatAgent
        self.live_text = chunk

        # Detección inline de segmentos completos
        if "</think>" in self.live_text or "</thinking>" in self.live_text:
            self._maybe_commit_think_block()

        if "```" in self.live_text:
            self._maybe_commit_code_block()

        if self._live:
            self._live.update(self._build_view())

        self._last_stream_time = time.time()

    def _maybe_commit_think_block(self) -> None:
        """If a thought block is complete, commit it to the buffer."""
        match = re.search(r"<think(?:ing)?>(.*?)</think(?:ing)?>", self.live_text, re.DOTALL)
        if match:
            thought = match.group(1).strip()
            pre_text = self.live_text[: match.start()].strip()

            if pre_text:
                self.committed_buffer.append(Text(pre_text))

            for line in thought.splitlines():
                self.committed_buffer.append(Text(f"  {icons.vbar} {line}", style=f"dim {self.C_THINK}"))

            self.live_text = self.live_text[match.end() :].strip()
            self._flush_if_needed()

    def _maybe_commit_code_block(self) -> None:
        """If a code block is complete, commit it to the buffer."""
        match = re.search(r"```(\w*)\n(.*?)```", self.live_text, re.DOTALL)
        if match:
            lang = match.group(1) or "text"
            code = match.group(2)
            pre_text = self.live_text[: match.start()].strip()

            if pre_text:
                self.committed_buffer.append(Markdown(pre_text))

            self.committed_buffer.append(
                Syntax(code, lang, theme=self.theme.code_theme, line_numbers=True, padding=(0, 1))
            )

            self.live_text = self.live_text[match.end() :].strip()
            self._flush_if_needed()

    def end_stream(self, full_text: str | None = None) -> None:
        if self._live:
            self._live.stop()
            self._live = None

        final_text = full_text if full_text is not None else self.live_text
        if final_text:
            # Commit the final text to the buffer
            segments = _parse_segments(final_text)
            for seg in segments:
                if seg[0] == "think":
                    for line in seg[1].strip().splitlines():
                        self.committed_buffer.append(Text(f"  {icons.vbar} {line}", style=f"dim {self.C_THINK}"))
                elif seg[0] == "code":
                    self.committed_buffer.append(Syntax(seg[2], seg[1], theme=self.theme.code_theme, line_numbers=True))
                elif seg[0] == "text":
                    try:
                        self.committed_buffer.append(Markdown(seg[1]))
                    except Exception:
                        self.committed_buffer.append(Text(seg[1]))

        self.live_text = ""
        # Print only the delta (what wasn't definitively printed yet)
        view = self._build_view(show_cursor=False)
        if view.renderables:
            self.console.print(view)

        self.printed_count = len(self.committed_buffer)
        self._streaming = False

    # ─────────────────────────────────────────────────────────────────
    # Tool Calls
    # ─────────────────────────────────────────────────────────────────

    def print_tool_call(self, tool_name: str, args: dict) -> None:
        args_preview = ", ".join(f"{k}={v}" if len(str(v)) <= 40 else f"{k}=..." for k, v in args.items())
        line = Text()
        line.append(f"  {icons.tool} ", style=self.C_TOOL)
        line.append(tool_name, style="bold")
        line.append(f"  {escape(args_preview)}", style="dim")
        self.committed_buffer.append(line)

        if self._live:
            self._live.update(self._build_view())
        else:
            self.console.print(line)
            self.printed_count = len(self.committed_buffer)

    def print_tool_result(self, ok: bool, content: str, tool_name: str | None = None) -> None:
        # LRU eviction
        stored = content[:10000] if len(content) > 10000 else content
        self.artifacts.append((tool_name or "tool", stored))
        if len(self.artifacts) > self.MAX_ARTIFACTS:
            self.artifacts.pop(0)

        artifact_id = f"#{len(self.artifacts)}"
        icon = f"[{self.C_SUCCESS}]{icons.ok}[/]" if ok else f"[{self.C_ERROR}]{icons.fail}[/]"
        name_display = tool_name or "tool"

        # Design decision: Show more lines for tool results to avoid "collapsed" feel
        lines = content.strip().splitlines()
        is_list = any(line.strip().startswith(("-", "*", "1.", " •", "Directory:")) for line in lines[:10])
        is_diff = content.strip().startswith(("---", "+++", "@@"))

        # Expand if it's a list, diff, or short structured content (up to 100 lines)
        # OR if it's an error (always show errors expanded for visibility)
        if (ok and len(lines) <= 100 and (is_list or is_diff or len(content) < 2000)) or not ok:
            # Render structured output with more prominence
            border_style = self.C_DIM
            if not ok:
                # Limit error preview to avoid blowing up the terminal
                error_lines = lines[:30]
                error_text = "\n".join(error_lines)
                if len(lines) > 30:
                    error_text += f"\n... ({len(lines) - 30} more lines)"
                preview_renderable = Text(error_text, style=self.C_ERROR)
                border_style = self.C_ERROR
            elif is_diff:
                preview_renderable = Syntax(content, "diff", theme="monokai", background_color="default")
            else:
                # Use Text for lists/logs to avoid Markdown parsing overhead/memory issues
                preview_renderable = Text(content, style="dim")

            line = Group(
                Text.from_markup(f"  {icon} [bold]{name_display}[/] [dim]({artifact_id})[/]"),
                Panel(preview_renderable, border_style=border_style, padding=(0, 2), expand=False),
                Text(""),  # Spacer
            )
        else:
            # Fallback to compact single-line preview for very large outputs
            preview = content[:120].replace("\n", " ")
            if len(content) > 120:
                preview += "..."
            line = Text.from_markup(
                f"  {icon} [bold]{name_display}[/] [dim]({artifact_id})[/]  [dim]{escape(preview)}[/] [dim](Ctrl+O to expand)[/]"
            )

        self.committed_buffer.append(line)

        if self._live:
            self._live.update(self._build_view())
        else:
            self.console.print(line)
            self.printed_count = len(self.committed_buffer)

    def expand_artifact(self, index: int = -1) -> None:
        if not self.artifacts:
            self.print_warning("No artifacts to expand.")
            return

        try:
            actual = index if index >= 0 else len(self.artifacts) + index
            if actual < 0 or actual >= len(self.artifacts):
                self.print_error(f"Artifact {index} not found.")
                return

            name, content = self.artifacts[actual]
            artifact_id = f"#{actual + 1}"

            if name in ["read_file", "edit_file", "write_file", "execute_bash", "execute_command", "read_url"]:
                renderable = Syntax(
                    content,
                    "bash" if "bash" in name or "command" in name else "python",
                    theme="monokai",
                    line_numbers=True,
                )
            elif "[LSP DIAGNOSTICS" in content or "Error:" in content:
                renderable = Text.from_markup(content)
            else:
                renderable = Text(content)

            self.console.print()
            self.console.print(
                Panel(
                    renderable,
                    title=f"[bold {self.C_BRAND}]{name} {artifact_id}[/]",
                    subtitle="[dim]Ctrl+O to toggle[/]",
                    border_style=self.C_DIM,
                    padding=(1, 2),
                )
            )
        except Exception as e:
            self.print_error(f"Error expanding artifact: {e}")

    # ─────────────────────────────────────────────────────────────────
    # UI Elements
    # ─────────────────────────────────────────────────────────────────

    def print_welcome(self, version: str, model: str, mode: str) -> None:
        self.console.print()
        self.console.print(
            f"  [bold {self.C_BRAND}]{icons.brand} mentask[/]  [dim]v{version}[/]  "
            f"[dim]{icons.dot}[/]  [bold white]{model}[/]  [dim]{icons.dot}[/]  [dim]{mode} mode[/]",
        )
        self.console.print(
            f"  [dim]Type [white]/help[/white] for commands {icons.dot} [white]Ctrl+O[/white] to expand last result {icons.dot} [white]Ctrl+C[/white] to exit[/dim]\n",
        )

    def print_user(self, text: str, prompt_text: Text | None = None) -> None:
        from rich.control import Control

        self.console.control(Control.move(0, -1))
        self.console.print(" " * (self.console.width - 1), end="\r")
        if prompt_text:
            self.console.print(prompt_text, end="")
            self.console.print(text)
        else:
            self.console.print()
            self.console.print(f"  [{self.C_USER}]@{self.username}[/] [dim]>[/] {text}")

    def _print_agent_label(self, tool: str | None = None, is_natural: bool = False) -> None:
        header = self.prompt_engine.build_agent_header(self.prompt_style, tool=tool, is_natural=is_natural)
        # Extra spacing for natural messages to separate from previous tool activity
        if is_natural:
            self.console.print("\n")
        else:
            self.console.print()
        self.console.print(header)

    def print_thought(self, text: str) -> None:
        if not text.strip():
            return
        for line in text.strip().splitlines():
            self.committed_buffer.append(Text(f"  {icons.vbar} {line}", style=f"dim {self.C_THINK}"))

        if self._live:
            self._live.update(self._build_view())
        else:
            # If not live, print the new thoughts immediately
            view = self._build_view(show_cursor=False)
            if view.renderables:
                self.console.print(view)
                self.printed_count = len(self.committed_buffer)

    def print_metrics(self, summary: str) -> None:
        self._last_metrics = summary

    def print_turn_divider(self, model: str = "") -> None:
        metrics = self._last_metrics
        self._last_metrics = ""
        now = time.strftime("%H:%M:%S")

        if metrics:
            # Minimalist one-liner divider
            self.console.print(
                f"  [dim]{icons.hdash * 2} {model} {icons.dot} {metrics} {icons.dot} {now} {icons.hdash * 2}[/dim]\n"
            )
        else:
            self.console.print(f"\n  [dim]{icons.hdash * 20}[/dim]\n")

    def print_command_output(self, result) -> None:
        if result is None or result is True:
            return
        self.console.print(result)

    def print_error(self, msg: str) -> None:
        self.console.print(f"\n  [{self.C_ERROR}]{icons.fail} Error:[/]  {msg}")

    def print_warning(self, msg: str) -> None:
        self.console.print(f"\n  [{self.C_TOOL}]{icons.warn} Warning:[/]  {msg}")

    def print_status(self, msg: str) -> None:
        # Avoid showing noisy turn numbers in persistent mode if they aren't useful
        if "Agent Turn" in msg:
            return
        self.console.print(f"  [dim]{icons.dot} {msg}[/]")

    async def ask_confirmation(self, tool_name: str, args: dict[str, str], warning: str = "") -> bool:
        if self._live:
            self._live.stop()
            self._live = None

        if warning:
            self.console.print(
                Panel(
                    f"[bold white]{warning}[/bold white]",
                    title=f"[bold {self.C_ERROR}]{icons.warn} SECURITY WARNING[/]",
                    border_style=self.C_ERROR,
                    padding=(0, 1),
                )
            )
        else:
            self.console.print(f"\n  [{self.C_TOOL}]{icons.tool} Permission Required[/]")

        self.console.print(f"  [bold]{tool_name}[/] wants to execute with:")

        for k, v in args.items():
            val_str = str(v)
            if len(val_str) > 60 or "\n" in val_str:
                self.console.print(f"    [bold]{k}:[/]")
                lang = "python" if tool_name in ("write_file", "edit_file") else "text"
                self.console.print(Panel(Syntax(val_str, lang, theme="monokai"), border_style="dim", padding=(0, 1)))
            else:
                self.console.print(f"    [bold]{k}:[/]  [dim]{val_str}[/]")

        return Confirm.ask("\n  [bold]Allow?[/]")

    def print_goodbye(self, msg: str, session_id: str | None = None) -> None:
        self.console.print()
        self.console.print(f"  [dim]{icons.hdash * 40}[/]")
        if session_id:
            self.console.print(f"  [dim]Session:[/] [bold {self.C_BRAND}]{session_id}[/]")
            self.console.print(f"  [dim]Resume:[/]  [white]mentask {session_id}[/]")
        self.console.print(f"  [dim]{msg}[/]\n")
