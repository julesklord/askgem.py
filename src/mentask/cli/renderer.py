"""
cli/renderer.py — Rich-based streaming renderer for mentask.

Design: Inspired by Gem CLI's clean, professional terminal UX.
  - No italic fonts — clean, direct text throughout.
  - Compact tool call indicators with Unicode status icons.
  - Minimal user input display (prefix-based, no heavy panels).
  - Thinking blocks rendered as dim sidebar without decoration.
  - Structured final render: think → code (syntax) → markdown.
  - Subtle metrics line after each turn.
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

from .themes import get_theme


# ---------------------------------------------------------------------------
# Unicode icon system with ASCII fallback
# ---------------------------------------------------------------------------
def _supports_unicode() -> bool:
    """Detect if the current terminal supports extended Unicode."""
    import sys

    try:
        sys.stdout.write("\u2726")
        sys.stdout.write("\b \b")  # Erase the test character
        sys.stdout.flush()
        return True
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False
    except Exception:
        # If stdout is not a real terminal (e.g., piped), assume modern
        return True


class _Icons:
    """Terminal-safe icon set with ASCII fallback."""

    def __init__(self):
        # Default to Unicode; will be downgraded if detection fails
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


# Singleton icon set
icons = _Icons()

# ---------------------------------------------------------------------------
# Segment parser
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class CliRenderer:
    """Stateful renderer for a single conversation session.

    Design philosophy:
    - Clean, professional output inspired by Gemini CLI.
    - No italic fonts anywhere — all text is upright and clear.
    - Compact tool call display with status icons.
    - Subtle thinking blocks via dim sidebar.
    """

    MAX_ARTIFACTS = 50

    def __init__(
        self,
        console: Console,
        theme_name: str = "indigo",
        stream_mode: str = "continuous",
        stream_delay: float = 0.015,
    ) -> None:
        """Initialize renderer with theme and streaming configuration."""
        self.console: Console = console
        self._live: Live | None = None
        self._streaming: bool = False
        self._last_text: str = ""
        self._stream_delay: float = stream_delay
        self.username: str = getpass.getuser()
        self.stream_mode: str = stream_mode
        self._label_printed: bool = False
        self.prompt_style: str = "atomic"

        # New streaming architecture variables
        self.committed_buffer = []
        self.live_text = ""
        self.MAX_COMMITTED_LINES = 100

        self.apply_theme(theme_name)
        self.artifacts: list[tuple[str, str]] = []

        # Prompt Engine
        from .prompts import PromptEngine

        self.prompt_engine = PromptEngine(self.theme, use_nerdfonts=self.console.options.encoding.lower() == "utf-8")

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
        if hasattr(self, "prompt_engine"):
            self.prompt_engine.theme = self.theme

    # ------------------------------------------------------------------
    # Welcome / session header
    # ------------------------------------------------------------------
    def print_welcome(self, version: str, model: str, mode: str) -> None:
        """Print a clean, compact welcome header."""
        self.console.print()

        # Gem CLI style: single centered line with key info
        self.console.print(
            f"  [bold {self.C_BRAND}]{icons.brand} mentask[/]  "
            f"[dim]v{version}[/]  [dim]{icons.dot}[/]  "
            f"[bold white]{model}[/]  [dim]{icons.dot}[/]  "
            f"[dim]{mode} mode[/]",
        )
        self.console.print(
            f"  [dim]Type [white]/help[/white] for commands {icons.dot} [white]Ctrl+C[/white] to exit[/dim]\n",
        )

    # ------------------------------------------------------------------
    # User turn header
    # ------------------------------------------------------------------
    def print_user(self, text: str, prompt_text: Optional[Text] = None) -> None:
        """Print user input — clean prefix style, no heavy panels."""
        # Clear the prompt line (only works in some terminals)
        self.console.control(Control.move(0, -1))
        self.console.print(" " * (self.console.width - 1), end="\r")

        self.console.print()
        if prompt_text:
            self.console.print(prompt_text, end="")
            self.console.print(text)
        else:
            self.console.print(f"  [{self.C_USER}]@{self.username}[/] [dim]>[/] {text}")

    # ------------------------------------------------------------------
    # Agent label (printed once before streaming starts)
    # ------------------------------------------------------------------
    def _print_agent_label(self, tool: Optional[str] = None, is_natural: bool = False) -> None:
        header = self.prompt_engine.build_agent_header(self.prompt_style, tool=tool, is_natural=is_natural)
        if is_natural:
            self.console.print("\n")
        self.console.print(f"\n{header}")

    def print_thought(self, text: str) -> None:
        """Renders the reasoning process — dim sidebar, no italics."""
        if not text.strip():
            return

        for line in text.strip().splitlines():
            self.console.print(f"  [{self.C_DIM}]{icons.vbar}[/] [{self.C_THINK}]{line}[/]")

    # ------------------------------------------------------------------
    # Live streaming
    # ------------------------------------------------------------------
    def _build_view(self):
        """Construye el Group con todo el contenido."""
        from rich.console import Group

        items = []
        for item in self.committed_buffer:
            items.append(item)

        if self.live_text:
            # We parse the live text just like before but only for the uncommitted tail
            segments = _parse_segments(self.live_text)
            for seg in segments:
                kind = seg[0]
                if kind == "think":
                    for line in seg[1].strip().splitlines():
                        items.append(
                            Text.from_markup(f"  [{self.C_DIM}]{icons.vbar}[/] [{self.C_THINK}]{escape(line)}[/]")
                        )
                elif kind == "code":
                    lang = seg[1]
                    body = seg[2]
                    items.append(
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
                    try:
                        items.append(Markdown(seg[1]))
                    except Exception:
                        items.append(Text(seg[1]))

            items.append(Text(icons.cursor, style=f"bold {self.C_BRAND}"))

        return Group(*items)

    def _maybe_commit_code_block(self):
        """Si hay un code block completo en live_text, commitearlo."""
        import re

        match = re.search(r"```(\w*)\n(.*?)```", self.live_text, re.DOTALL)
        if match:
            lang = match.group(1) or "text"
            code = match.group(2)

            # Commitear el texto antes del code block
            pre_text = self.live_text[: match.start()].strip()
            if pre_text:
                try:
                    self.committed_buffer.append(Markdown(pre_text))
                except Exception:
                    self.committed_buffer.append(Text(pre_text))

            # Commitear el code block
            self.committed_buffer.append(
                Syntax(code, lang, theme=self.theme.code_theme, line_numbers=True, padding=(0, 1))
            )

            # Remover del live_text
            self.live_text = self.live_text[match.end() :].lstrip("\n")

    def start_stream(self, is_natural: bool = False) -> None:
        """Inicia streaming SIN transient — el contenido persiste."""
        if not self._label_printed:
            self._print_agent_label(is_natural=is_natural)
            self._label_printed = True

        self.committed_buffer = []
        self.live_text = ""

        self._live = Live(
            self._build_view(),
            console=self.console,
            refresh_per_second=12,
            transient=False,
        )
        self._live.start()
        self._streaming = True
        self._last_stream_time: float = time.time()

    def update_stream(self, chunk: str) -> None:
        """Agrega chunk al live_text y re-renderiza."""
        now = time.time()
        elapsed = now - self._last_stream_time
        if elapsed < self._stream_delay:
            time.sleep(self._stream_delay - elapsed)

        # In this architecture, chunk is actually the full accumulated text?
        # No, wait, if chat.py passes accumulated text, we need to take only the delta.
        # But mentask's ProviderManager yields chunks or the full accumulated text?
        # Actually `update_stream` in CliRenderer expects accumulated.
        # So we should just use accumulated and parse the code blocks.

        self.live_text = chunk
        if "```" in self.live_text:
            self._maybe_commit_code_block()

        self._last_text = chunk
        if self._live and self._streaming:
            self._live.update(self._build_view())

        self._last_stream_time = time.time()

    def end_stream(self, full_text: str | None = None) -> None:
        """Stop live streaming and render the structured final response."""
        if not self._streaming:
            return

        final_text: str = full_text if full_text is not None else self._last_text

        if self._live:
            # We don't want the cursor in the final output
            self.live_text = final_text
            self._maybe_commit_code_block()  # commit any remaining

            # Build the final view without cursor
            from rich.console import Group

            items = list(self.committed_buffer)
            if self.live_text:
                segments = _parse_segments(self.live_text)
                for seg in segments:
                    kind = seg[0]
                    if kind == "think":
                        for line in seg[1].strip().splitlines():
                            items.append(
                                Text.from_markup(f"  [{self.C_DIM}]{icons.vbar}[/] [{self.C_THINK}]{escape(line)}[/]")
                            )
                    elif kind == "code":
                        lang = seg[1]
                        body = seg[2]
                        items.append(
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
                        try:
                            items.append(Markdown(seg[1]))
                        except Exception:
                            items.append(Text(seg[1]))

            self._live.update(Group(*items))
            self._live.stop()
            self._live = None

        self._streaming = False
        self._last_text = ""
        self.committed_buffer = []
        self.live_text = ""

    # ------------------------------------------------------------------
    # Structured response renderer
    # ------------------------------------------------------------------
    def _render_response(self, text: str) -> None:
        """Render response with proper structure (think blocks, code, markdown)."""
        if not text.strip():
            return

        segments: list = _parse_segments(text)

        for seg in segments:
            kind: str = seg[0]

            if kind == "think":
                for line in seg[1].strip().splitlines():
                    self.console.print(f"  [{self.C_DIM}]{icons.vbar}[/] [{self.C_THINK}]{line}[/]")

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
                try:
                    self.console.print(Markdown(seg[1]))
                except Exception:
                    self.console.print(seg[1])

    # ------------------------------------------------------------------
    # Tool call notifications
    # ------------------------------------------------------------------
    def print_tool_call(self, tool_name: str, args: dict[str, str]) -> None:
        """Compact tool call notification with icon."""
        args_preview = ", ".join(f"{k}={v}" if len(str(v)) <= 40 else f"{k}=..." for k, v in args.items())
        self.console.print(f"  [{self.C_TOOL}]{icons.tool}[/] [bold]{tool_name}[/]  [dim]{escape(args_preview)}[/]")

    def print_tool_result(self, ok: bool, content: str, tool_name: str | None = None) -> None:
        """Compact tool result with status icon and collapsible output."""
        stored_content = content[:10000] if len(content) > 10000 else content
        self.artifacts.append((tool_name or "tool", stored_content))

        if len(self.artifacts) > self.MAX_ARTIFACTS:
            self.artifacts.pop(0)

        artifact_id = f"#{len(self.artifacts)}"

        icon = f"[{self.C_SUCCESS}]{icons.ok}[/]" if ok else f"[{self.C_ERROR}]{icons.fail}[/]"
        name_display = tool_name or "tool"

        # Single-line compact result
        preview = content[:120].replace("\n", " ")
        if len(content) > 120:
            preview += "..."

        self.console.print(f"  {icon} [bold]{name_display}[/] [dim]({artifact_id})[/]  [dim]{escape(preview)}[/]")

    def expand_artifact(self, index: int = -1) -> None:
        """Displays the full content of a stored artifact."""
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

            # Select renderable based on tool type
            if name in ["read_file", "edit_file", "write_file", "execute_bash", "execute_command"]:
                renderable = Syntax(
                    full_content,
                    "bash" if "bash" in name or "command" in name else "python",
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=True,
                )
            elif full_content.strip().startswith("#") or "```" in full_content:
                renderable = Markdown(full_content)
            elif "[LSP DIAGNOSTICS" in full_content:
                renderable = Text.from_markup(full_content)
            else:
                renderable = Text(full_content)

            self.console.print()
            self.console.print(
                Panel(
                    renderable,
                    title=f"[bold {self.C_BRAND}]{name} {artifact_id}[/]",
                    border_style=self.C_DIM,
                    padding=(1, 2),
                    subtitle="[dim]Ctrl+O to toggle[/]",
                )
            )
        except Exception as e:
            self.print_error(f"Error expanding artifact: {e}")

    # ------------------------------------------------------------------
    # Inline metrics (after each turn)
    # ------------------------------------------------------------------
    def print_metrics(self, summary: str) -> None:
        """Store metrics to be displayed by the turn divider."""
        self._last_metrics: str = summary

    def print_command_output(self, result: str | object | None) -> None:
        """Print output from /slash commands."""
        if result is None or result is True:
            return
        self.console.print(result)

    def print_turn_divider(self) -> None:
        """Print a subtle divider with integrated metrics."""
        metrics: str = getattr(self, "_last_metrics", "")
        self._last_metrics = ""

        if metrics:
            self.console.print(f"\n  [dim]{icons.hdash * 3} {metrics} {icons.hdash * 3}[/]\n")
        else:
            self.console.print(f"\n  [dim]{icons.hdash * 40}[/]\n")

    # ------------------------------------------------------------------
    # Error / warning / status
    # ------------------------------------------------------------------
    def print_error(self, msg: str) -> None:
        """Print error message."""
        self.console.print(f"\n  [{self.C_ERROR}]{icons.fail} Error:[/]  {msg}")

    def print_warning(self, msg: str) -> None:
        """Print warning message."""
        self.console.print(f"\n  [{self.C_TOOL}]{icons.warn} Warning:[/]  {msg}")

    def print_status(self, msg: str) -> None:
        """Print a subtle status message from the orchestrator."""
        self.console.print(f"  [dim]{icons.dot} {msg}[/]")

    # ------------------------------------------------------------------
    # Confirmation dialog
    # ------------------------------------------------------------------
    async def ask_confirmation(self, tool_name: str, args: dict[str, str], warning: str = "") -> bool:
        """Ask user for permission to execute a tool."""
        # Close live stream if active to allow clean prompt
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

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    def print_goodbye(self, msg: str, session_id: str | None = None) -> None:
        """Print goodbye message with session info."""
        self.console.print()
        self.console.print(f"  [dim]{icons.hdash * 40}[/]")

        if session_id:
            self.console.print(f"  [dim]Session:[/] [bold {self.C_BRAND}]{session_id}[/]")
            self.console.print(f"  [dim]Resume:[/]  [white]mentask {session_id}[/]")

        self.console.print(f"  [dim]{msg}[/]\n")
