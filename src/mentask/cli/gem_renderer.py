"""
cli/gem_renderer.py — Gem CLI-style persistent renderer.

Key differences from CliRenderer:
- transient=False → content persists in terminal scroll
- Incremental buffer commits → thoughts, code blocks committed as they complete
- Auto-flush for long sessions → prevents slow re-renders
"""

from __future__ import annotations

import asyncio
import contextlib
import getpass
import logging
import os
import random
import re
import threading
import time
from typing import Any

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm
from rich.status import Status
from rich.syntax import Syntax
from rich.text import Text

from ..agent.schema import Message, Role
from ..core.i18n import _, _list
from .prompts import PromptEngine
from .themes import get_theme

_logger = logging.getLogger(__name__)



# Icon system (updated for Nerd Fonts support)
class _Icons:
    def __init__(self, use_nerdfonts: bool = True):
        self._unicode = True
        self.use_nerdfonts = use_nerdfonts
        try:
            import sys

            if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
                self._unicode = False
        except Exception:
            self._unicode = False

    @property
    def brand(self) -> str:
        if self.use_nerdfonts:
            return "󱚣"
        return "\u2726" if self._unicode else "*"

    @property
    def tool(self) -> str:
        if self.use_nerdfonts:
            return "󰓆"
        return "\u26a1" if self._unicode else ">"

    @property
    def ok(self) -> str:
        if self.use_nerdfonts:
            return "󰄬"
        return "\u2713" if self._unicode else "[OK]"

    @property
    def fail(self) -> str:
        if self.use_nerdfonts:
            return "󰅖"
        return "\u2717" if self._unicode else "[ERR]"

    @property
    def warn(self) -> str:
        if self.use_nerdfonts:
            return "󰀦"
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


# We'll initialize icons later when we have config
icons = _Icons()


# Segment parser (reuse)
_SEGMENT_RE = re.compile(
    r"(<think(?:ing)?>.*?</think(?:ing)?>)" r"|" r"(```(\w*)\n?(.*?)(?:```|$))",
    re.DOTALL,
)


def _parse_segments(text: str) -> list:
    segments: list[tuple[str, ...]] = []
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

    # Constants for buffer management and throttling
    MAX_COMMITTED_LINES = 100
    MAX_ARTIFACTS = 50
    FLUSH_BATCH_SIZE = 50
    THINKING_MESSAGE_INTERVAL = 5.0  # seconds
    TYPEWRISER_UNTYPE_DELAY = 0.015  # seconds
    TYPEWRISHER_TYPE_DELAY = 0.03  # seconds
    ERROR_RECOVERY_DELAY = 1.0  # seconds
    LIVE_REFRESH_RATE = 12  # per second
    TABLE_PADDING = (0, 1)
    SYNTAX_PADDING = (0, 1)
    TOOL_PREVIEW_LENGTH = 40
    ARTIFACT_PREVIEW_LENGTH = 10000
    TOOL_RESULT_LINES_LIMIT = 30
    CODE_BLOCK_LINES_LIMIT = 100
    CODE_BLOCK_SIZE_LIMIT = 2000

    def __init__(
        self,
        console: Console,
        theme_name: str = "indigo",
        stream_mode: str = "continuous",
        stream_delay: float | None = None,
        use_nerdfonts: bool = True,
    ) -> None:
        self.console = console
        self.committed_buffer: list[Any] = []
        self.live_text = ""
        self._live: Live | None = None
        self._streaming = False
        self._stream_delay = stream_delay if stream_delay is not None else self.TYPEWRISER_UNTYPE_DELAY
        self.username = getpass.getuser()
        self.stream_mode = stream_mode
        self._label_printed = False
        self.show_thinking_details = True  # Toggle for thought blocks

        # Update global icons state
        icons.use_nerdfonts = use_nerdfonts

        self.prompt_engine = PromptEngine(get_theme(theme_name), use_nerdfonts=use_nerdfonts)
        self.prompt_style = "atomic"
        self.apply_theme(theme_name)

        self.artifacts: list[tuple[str, str]] = []
        self._last_metrics = ""
        self.printed_count = 0  # Number of items in committed_buffer already printed definitively
        self._thinking_status: Status | None = None
        self._thinking_task: asyncio.Task | None = None
        self._current_thinking_msg = ""
        self._thinking_lock = threading.Lock()  # Thread safety for thinking status
        self._status_bar_data: dict[str, str | int | float] = {"model": "", "mode": "", "tokens": 0, "cost": 0.0}

    def _setup_colors(self) -> None:
        self.C_BRAND = self.theme.brand_primary
        self.C_SUCCESS = self.theme.success
        self.C_ERROR = self.theme.error
        self.C_DIM = self.theme.text_dim
        # Grayish thinking color, darker than normal text
        self.C_THINK = "italic #6b7280"  # Gray-500, italic
        self.C_USER = self.theme.text_secondary
        self.C_TOOL = self.theme.warning

    def update_status_bar(
        self, model: str | None = None, mode: str | None = None, tokens: int | None = None, cost: float | None = None
    ) -> None:
        """Updates the internal data used for the status bar."""
        if model is not None:
            self._status_bar_data["model"] = model
        if mode is not None:
            self._status_bar_data["mode"] = mode
        if tokens is not None:
            self._status_bar_data["tokens"] = tokens
        if cost is not None:
            self._status_bar_data["cost"] = cost

    def print_status_bar(self) -> None:
        """Prints the current status bar to the console."""
        bar = self.prompt_engine.build_status_bar(
            str(self._status_bar_data["model"]),
            str(self._status_bar_data["mode"]),
            int(self._status_bar_data["tokens"]),  # type: ignore[arg-type]
            float(self._status_bar_data["cost"]),  # type: ignore[arg-type]
        )
        self.console.print(bar)

    def _get_lexer_for_path(self, path: str | None) -> str:
        """Determines the Rich syntax lexer based on file extension."""
        if not path:
            return "text"

        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "jsx",
            ".tsx": "tsx",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".html": "html",
            ".css": "css",
            ".sh": "bash",
            ".bash": "bash",
            ".sql": "sql",
            ".toml": "toml",
            ".ini": "ini",
            ".dockerfile": "docker",
            "dockerfile": "docker",
            ".diff": "diff",
            ".patch": "diff",
            "makefile": "make",
        }

        filename = os.path.basename(path).lower()
        if filename in ext_map:
            return ext_map[filename]

        _, ext = os.path.splitext(filename)
        return ext_map.get(ext, "text")

    def apply_theme(self, name: str) -> None:
        self.theme = get_theme(name)
        self._setup_colors()
        if hasattr(self, "prompt_engine"):
            self.prompt_engine.theme = self.theme

        # Import Theme here to avoid circular dependencies
        from rich.theme import Theme

        # Dynamic console styles matching the theme
        styles = {
            "success": f"bold {self.theme.success}",
            "warning": f"bold {self.theme.warning}",
            "error": f"bold {self.theme.error}",
            "info": f"{self.theme.info}",
            "brand": f"bold {self.theme.brand_primary}",
            "brand_secondary": f"bold {self.theme.brand_secondary}",
            "text_primary": f"{self.theme.text_primary}",
            "text_secondary": f"{self.theme.text_secondary}",
            "text_dim": f"{self.theme.text_dim}",
            "agent": f"bold {self.theme.brand_primary}",
            "user": f"bold {self.theme.brand_secondary}",
        }

        # Pop previous custom theme if it was pushed to avoid accumulation
        if hasattr(self, "_pushed_theme") and self._pushed_theme:
            with contextlib.suppress(Exception):
                self.console.pop_theme()

        self._pushed_theme: Theme | None = Theme(styles)
        self.console.push_theme(self._pushed_theme)

    def reset_turn(self) -> None:
        self._label_printed = False
        self.committed_buffer = []
        self.printed_count = 0
        self.stop_thinking()

    # ─────────────────────────────────────────────────────────────────
    # Core Rendering
    # ─────────────────────────────────────────────────────────────────

    def show_thinking(self) -> None:
        """Display a thinking spinner with a random quirky message and start rotation."""
        if not self.show_thinking_details:
            return

        with self._thinking_lock:
            if self._thinking_status:
                return

            from .ui_utils import get_random_thinking_message

            base_msg = _("dashboard.prompt_thinking") or "Pensando"
            funny_msg = get_random_thinking_message()
            self._current_thinking_msg = funny_msg

            brand_icon = "✦" if not icons.use_nerdfonts else icons.brand
            prefix = f"[{self.C_BRAND}]{brand_icon}[/] [bold]{base_msg}...[/] ─ "
            full_msg = f"{prefix}[dim]{funny_msg}[/]"

            self._thinking_status = self.console.status(
                full_msg,
                spinner="dots",
                spinner_style=f"bold {self.C_BRAND}",
            )
            self._thinking_status.start()

            # Start the typewriter rotation task
            try:
                loop = asyncio.get_running_loop()
                if self._thinking_task and not self._thinking_task.done():
                    self._thinking_task.cancel()
                self._thinking_task = loop.create_task(self._rotate_thinking_messages())
            except RuntimeError:
                pass

    async def _rotate_thinking_messages(self) -> None:
        """Background task to cycle messages with typewriter effect."""
        from .ui_utils import get_random_thinking_message

        base_msg = _("dashboard.prompt_thinking") or "Pensando"
        brand_icon = "✦" if not icons.use_nerdfonts else icons.brand
        prefix = f"[{self.C_BRAND}]{brand_icon}[/] [bold]{base_msg}...[/] ─ "

        # We combine i18n messages with quirky hardcoded ones to ensure it's never empty
        i18n_messages = _list("thinking.messages") or []

        while self._thinking_status:
            try:
                # Wait before changing message
                await asyncio.sleep(self.THINKING_MESSAGE_INTERVAL)
                if not self._thinking_status:
                    break

                # Get a new message, either from i18n or the quirky list
                if i18n_messages and random.random() > 0.3:
                    next_msg = random.choice(i18n_messages)
                else:
                    next_msg = get_random_thinking_message()

                while next_msg == self._current_thinking_msg:
                    if i18n_messages and random.random() > 0.3:
                        next_msg = random.choice(i18n_messages)
                    else:
                        next_msg = get_random_thinking_message()

                # 1. Un-type current message
                for i in range(len(self._current_thinking_msg), -1, -1):
                    if not self._thinking_status:
                        return
                    self._thinking_status.update(f"{prefix}[dim]{self._current_thinking_msg[:i]}[/]")
                    await asyncio.sleep(self.TYPEWRISER_UNTYPE_DELAY)

                # 2. Type next message
                for i in range(len(next_msg) + 1):
                    if not self._thinking_status:
                        return
                    self._thinking_status.update(f"{prefix}[dim]{next_msg[:i]}[/]")
                    await asyncio.sleep(self.TYPEWRISHER_TYPE_DELAY)

                self._current_thinking_msg = next_msg
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(self.ERROR_RECOVERY_DELAY)

    def stop_thinking(self) -> None:
        """Stop the thinking spinner and the rotation task."""
        with self._thinking_lock:
            if self._thinking_task:
                self._thinking_task.cancel()
                self._thinking_task = None

            if self._thinking_status:
                self._thinking_status.stop()
                self._thinking_status = None

    def _build_view(self, show_cursor: bool = True) -> Group:
        """Construct a Group with only the UNPRINTED committed content + live text."""
        items = list(self.committed_buffer[self.printed_count :])

        if self.live_text:
            cursor = f" {icons.brand}" if show_cursor else ""
            # Support markdown in the live stream
            try:
                # Basic markdown for live text might be jittery, but Text is safer
                # We use Text for the live stream part to avoid Markdown jitter
                items.append(Text(self.live_text + cursor, style=f"bold {self.C_BRAND}"))
            except Exception:
                items.append(Text(self.live_text + cursor))
        return Group(*items)

    def _flush_if_needed(self) -> None:
        """If the buffer grows too large, print older lines definitively to the console."""
        if len(self.committed_buffer) > self.MAX_COMMITTED_LINES:
            self.console.print(f"[dim]{icons.hdash * 3} older output {icons.hdash * 3}[/dim]")
            for item in self.committed_buffer[: self.FLUSH_BATCH_SIZE]:
                self.console.print(item)
            self.committed_buffer = self.committed_buffer[self.FLUSH_BATCH_SIZE :]

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
            refresh_per_second=self.LIVE_REFRESH_RATE,
            transient=True,  # ← Reset for definitive print in end_stream
        )
        self._live.start()
        self._streaming = True

    def update_stream(self, chunk: str) -> None:
        # Accumulate delta — provider now sends chunk only, not full accumulated text
        self.live_text += chunk

        # Inline detection of full segments
        if "<think" in self.live_text or "</thinking>" in self.live_text:
            self._maybe_commit_think_block()

        if "```" in self.live_text:
            self._maybe_commit_code_block()

        # No throttle — render every chunk for true token-level streaming
        if self._live:
            self._live.update(self._build_view())

    def _maybe_commit_think_block(self) -> None:
        """If a thought block is complete, commit it to the buffer."""
        match = re.search(r"<think(?:ing)?>(.*?)</think(?:ing)?>", self.live_text, re.DOTALL)
        if match:
            thought = match.group(1).strip()
            pre_text = self.live_text[: match.start()].strip()

            if pre_text:
                self.committed_buffer.append(Text(pre_text))

            if self.show_thinking_details:
                for line in thought.splitlines():
                    self.committed_buffer.append(Text(f"  {icons.vbar} {line}", style=self.C_THINK))

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
                Syntax(code, lang, theme=self.theme.code_theme, line_numbers=True, padding=self.SYNTAX_PADDING)
            )

            self.live_text = self.live_text[match.end() :].strip()
            self._flush_if_needed()

    def end_stream(self, full_text: str | None = None) -> None:
        if self._live:
            self._live.stop()
            self._live = None

        final_text = full_text if full_text is not None else self.live_text
        if final_text:
            segments = _parse_segments(final_text)

            # Separate text segments from code/think segments
            text_parts: list[str] = []
            other_renderables: list[Any] = []
            for seg in segments:
                if seg[0] == "think":
                    if self.show_thinking_details:
                        for line in seg[1].strip().splitlines():
                            other_renderables.append(Text(f"  {icons.vbar} {line}", style=self.C_THINK))
                elif seg[0] == "code":
                    other_renderables.append(
                        Syntax(seg[2], seg[1], theme=self.theme.code_theme, line_numbers=True)
                    )
                elif seg[0] == "text":
                    text_parts.append(seg[1])

            # Commit think/code segments first (before the text panel)
            for r in other_renderables:
                self.committed_buffer.append(r)

            # Wrap agent text response in a Panel for clear visual boundary
            if text_parts:
                agent_text = "\n\n".join(text_parts)
                try:
                    renderable = Markdown(agent_text)
                except Exception:
                    renderable = Text(agent_text)
                self.committed_buffer.append(
                    Panel(
                        renderable,
                        border_style=f"dim {self.C_BRAND}",
                        padding=(0, 1),
                        expand=True,
                    )
                )

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
        args_preview = ", ".join(
            f"{k}={v}" if len(str(v)) <= self.TOOL_PREVIEW_LENGTH else f"{k}=..." for k, v in args.items()
        )
        line = Text()
        line.append(f"  {icons.tool} ", style=f"bold {self.C_TOOL}")
        line.append("Calling ", style="dim")
        line.append(tool_name, style=f"bold {self.C_BRAND}")
        if args_preview:
            line.append(" with ", style="dim")
            line.append(args_preview, style="italic dim")

        # Add spacing before tool call if last item was text/panel (agent response)
        if self.committed_buffer and isinstance(self.committed_buffer[-1], (Text, Markdown, Panel)):
            self.committed_buffer.append(Text(""))

        self.committed_buffer.append(line)

        if self._live:
            self._live.update(self._build_view())
        else:
            self.console.print(line)
            self.printed_count = len(self.committed_buffer)

    def print_tool_result(self, ok: bool, content: str, tool_name: str | None = None) -> None:
        # LRU eviction
        stored = content[: self.ARTIFACT_PREVIEW_LENGTH] if len(content) > self.ARTIFACT_PREVIEW_LENGTH else content
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

        # Add spacing before tool result if last item was text/panel
        if self.committed_buffer and isinstance(self.committed_buffer[-1], (Text, Markdown, Panel)):
            self.committed_buffer.append(Text(""))

        # Expand if it's a list, diff, or short structured content (up to 100 lines)
        # OR if it's an error (always show errors expanded for visibility)
        if (
            ok
            and len(lines) <= self.CODE_BLOCK_LINES_LIMIT
            and (is_list or is_diff or len(content) < self.CODE_BLOCK_SIZE_LIMIT)
        ) or not ok:
            # Render structured output with more prominence
            border_style = self.C_DIM
            subtitle = None

            if not ok:
                # Limit error preview to avoid blowing up the terminal
                error_lines = lines[: self.TOOL_RESULT_LINES_LIMIT]
                error_text = "\n".join(error_lines)
                if len(lines) > self.TOOL_RESULT_LINES_LIMIT:
                    error_text += f"\n... ({len(lines) - self.TOOL_RESULT_LINES_LIMIT} more lines)"
                preview_renderable: Syntax | Text = Text(error_text, style=self.C_ERROR)
                border_style = self.C_ERROR
                subtitle = None
            elif tool_name == "read_file" and len(lines) > 1:
                # Detect filename from the header created in file_tools.py
                path = None
                m = re.search(r"--- Reading '(.*?)'", lines[0])
                if m:
                    path = m.group(1)

                lexer = self._get_lexer_for_path(path)
                # Skip the header in the preview if possible
                body = "\n".join(lines[1:])
                preview_renderable = Syntax(body, lexer, theme="monokai", background_color="default")
                subtitle = None
            elif is_diff:
                preview_renderable = Syntax(content, "diff", theme="monokai", background_color="default")
            else:
                # Use Text for lists/logs to avoid Markdown parsing overhead/memory issues
                preview_renderable = Text(content, style="dim")

            title_color = self.C_BRAND if ok else self.C_ERROR
            title = f"[bold {title_color}] 󰑭 {name_display.upper()} RESULT [/]"
            line: Group | Text = Group(
                Text.from_markup(f"  {icon} [bold {self.C_BRAND}]{name_display}[/] [dim]({artifact_id})[/]"),
                Panel(
                    preview_renderable,
                    title=title,
                    border_style=border_style,
                    padding=(0, 2),
                    expand=False,
                    subtitle=subtitle,
                ),
                Text(""),  # Spacer
            )
        else:
            # Fallback to compact single-line preview for very large outputs
            preview = content[:120].replace("\n", " ")
            if len(content) > 120:
                preview += "..."
            line = Text.from_markup(
                f"  {icon} [bold {self.C_BRAND}]{name_display}[/] [dim]({artifact_id})[/] ─ [dim italic]{escape(preview)}[/]"
            )

        self.committed_buffer.append(line)
        # Add spacing after tool result for separation from next agent text
        self.committed_buffer.append(Text(""))

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
                # Attempt to extract path from common tool output headers
                path_match = re.search(r"--- Reading '([^']+)'", content)
                if not path_match:
                    path_match = re.search(r"Success: (?:Created|Replaced text in) '([^']+)'", content)
                if not path_match:
                    path_match = re.search(r"in '([^']+)'", content)
                if not path_match:
                    path_match = re.search(r"file '([^']+)'", content)

                lexer = "python"
                if path_match:
                    lexer = self._get_lexer_for_path(path_match.group(1))
                elif "bash" in name or "command" in name:
                    lexer = "bash"

                renderable: Syntax | Text = Syntax(
                    content,
                    lexer,
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
                    border_style=self.C_DIM,
                    padding=(1, 2),
                )
            )
        except Exception as e:
            self.print_error(f"Error expanding artifact: {e}")

    def replay_history(self, history: list[Message]) -> None:
        """Re-renders historical messages into the console with proper styling."""
        if not history:
            return

        from rich.markdown import Markdown

        self.console.print(f"\n  [dim]{'─' * 50} session history {'─' * 8}[/dim]\n")

        for msg in history:
            if msg.role == Role.SYSTEM:
                continue

            try:
                if msg.role == Role.USER:
                    content_str = msg.content if isinstance(msg.content, str) else str(msg.content)
                    self.console.print(f"[bold {self.C_USER}] ❯ {content_str}[/]\n")

                elif msg.role == Role.ASSISTANT:
                    # getattr is safe here: only AssistantMessage has tool_calls
                    tool_calls = getattr(msg, "tool_calls", None) or []
                    header = self.prompt_engine.build_agent_header(
                        self.prompt_style, is_natural=not bool(tool_calls)
                    )
                    self.console.print(header)

                    # Thoughts (if enabled and present)
                    thought = getattr(msg, "thought", None)
                    if thought and self.show_thinking_details:
                        for line in thought.strip().splitlines():
                            self.console.print(f"  {icons.vbar} [dim]{line}[/]", style=self.C_THINK)

                    # Body segments — guard against list content (multimodal)
                    raw_content = msg.content if isinstance(msg.content, str) else ""
                    if raw_content:
                        segments = _parse_segments(raw_content)
                        for seg in segments:
                            if seg[0] == "text":
                                try:
                                    self.console.print(Markdown(seg[1]))
                                except Exception:
                                    self.console.print(seg[1])
                            elif seg[0] == "code":
                                self.console.print(
                                    Syntax(
                                        seg[2], seg[1],
                                        theme=self.theme.code_theme,
                                        line_numbers=True,
                                        padding=(0, 1),
                                    )
                                )

                    # Tool calls summary
                    for tc in tool_calls:
                        self.print_tool_call(tc.name, tc.arguments)

                    self.console.print()

                elif msg.role == Role.TOOL:
                    tool_name = (msg.metadata or {}).get("tool_name", "tool")
                    content_str = msg.content if isinstance(msg.content, str) else str(msg.content)
                    self.print_tool_result(ok=True, content=content_str, tool_name=tool_name)

            except Exception as exc:
                _logger.debug(f"replay_history: skipping malformed message — {exc}")
                continue

        self.console.print(f"  [dim]{'─' * 50} resuming {'─' * 16}[/dim]\n")

    # ─────────────────────────────────────────────────────────────────
    # UI Elements
    # ─────────────────────────────────────────────────────────────────
    def print_splash_screen(self) -> None:
        """Prints a wide ASCII banner and welcome message for new sessions."""
        from .ui_utils import get_ascii_banner

        self.console.print(get_ascii_banner(theme=self.theme))
        self.console.print()

    def print_welcome(self, version: str, model: str, mode: str) -> None:
        self.update_status_bar(model=model, mode=mode)
        self.console.print()
        self.console.print(
            f"  [bold {self.C_BRAND}]{icons.brand} mentask[/]  [dim]v{version}[/]  "
            f"[dim]{icons.dot}[/]  [bold white]{model}[/]  [dim]{icons.dot}[/]  [dim]{mode} mode[/]",
        )
        self.console.print(
            f"  [dim]Type [white]/help[/white] for commands {icons.dot} [white]Ctrl+C[/white] to exit[/dim]\n",
        )

        from rich.table import Table

        tips_table = Table.grid(expand=True, padding=(0, 4))
        tips_table.add_column(style="dim")
        tips_table.add_column(style="dim")

        tips_table.add_row(
            "[bold #818cf8]󰘳 /model[/]  ─ Switch LLMs dynamically",
            "[bold #34d399]󰄬 /context[/] ─ Adjust workspace focus"
        )
        tips_table.add_row(
            "[bold #fbbf24]󰋚 /history[/] ─ List or export session files",
            "[bold #a78bfa]󰞋 /help[/]    ─ View all CLI commands"
        )

        self.console.print(
            Panel(
                tips_table,
                title=f"[bold {self.C_BRAND}]󰘳 QUICKSTART GUIDE[/bold {self.C_BRAND}]",
                border_style="dim",
                padding=(1, 2),
                expand=False
            )
        )
        self.console.print()
        self.print_status_bar()
        self.console.print()

    def print_user(self, text: str, prompt_text: Text | None = None) -> None:
        from rich.control import Control

        self.console.control(Control.move(0, -1))
        self.console.print(" " * (self.console.width - 1), end="\r")
        if prompt_text:
            self.console.print(prompt_text, end="")
            self.console.print()
            self.console.print(f"  [{self.C_USER}]@{self.username}[/] [dim]>[/] {text}")

    def _print_agent_label(self, tool: str | None = None, is_natural: bool = False) -> None:
        header = self.prompt_engine.build_agent_header(self.prompt_style, tool=tool, is_natural=is_natural)
        # Separate agent response with a newline
        self.console.print()
        self.console.print(header)
        self._active_header = None

    def print_thought(self, text: str) -> None:
        if not text.strip() or not self.show_thinking_details:
            return
        for line in text.strip().splitlines():
            self.committed_buffer.append(Text(f"  {icons.vbar} {line}", style=self.C_THINK))

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

        # Build a unified status line using the prompt engine's bubbles
        bar = self.prompt_engine.build_status_bar(
            str(self._status_bar_data["model"]),
            str(self._status_bar_data["mode"]),
            int(self._status_bar_data["tokens"]),  # type: ignore[arg-type]
            float(self._status_bar_data["cost"]),  # type: ignore[arg-type]
        )

        # Add timestamp and optional metrics summary
        now_str = time.strftime("%H:%M:%S")
        suffix = f"  {icons.hdash} {metrics} {icons.dot} {now_str}" if metrics else f"  {icons.hdash} {now_str}"

        self.console.print()
        self.console.print(bar, end="")
        self.console.print(f"[dim]{suffix}[/dim]")
        self.console.print()

    def print_command_output(self, result) -> None:
        if result is None or result is True:
            return
        self.console.print(result)

    def print_error(self, msg: str) -> None:
        self.console.print(f"\n  [{self.C_ERROR}]{icons.fail} Error:[/]  {msg}")

    def print_warning(self, msg: str) -> None:
        self.console.print(f"\n  [{self.C_TOOL}]{icons.warn} Warning:[/]  {msg}")

    def print_status(self, msg: str) -> None:
        """Prints a low-priority system status or notification."""
        # Avoid showing noisy turn numbers in persistent mode if they aren't useful
        if "Agent Turn" in msg:
            return

        # If it already has an icon (from CLIProvider beautification), print it clean
        if msg.startswith("󰀦"):
            self.console.print(f"  [dim]{msg}[/]")
        else:
            self.console.print(f"  [dim]{icons.dot} {msg}[/]")

    async def confirm_action(self, message: str, detail: str | None = None, severity: str = "info") -> bool:
        """Requests confirmation for a generic action (ToolUIAdapter protocol)."""
        if self._live:
            self._live.stop()
            self._live = None

        style = {"info": "blue", "warning": "yellow", "error": "red"}.get(severity, "blue")
        icon = {"info": icons.ok, "warning": icons.warn, "error": icons.fail}.get(severity, icons.ok)

        self.console.print(f"\n  [{style}]{icon} ACTION REQUIRED[/{style}]")
        self.console.print(f"  {message}")
        if detail:
            self.console.print(f"  [dim]{detail}[/dim]")

        # Use asyncio.to_thread for Confirm.ask because it's blocking
        return await asyncio.to_thread(Confirm.ask, "\n  [bold]Proceed?[/]")

    def log_status(self, message: str, level: str = "info") -> None:
        """Logs a status update (ToolUIAdapter protocol)."""
        self.print_status(message)

    def stream_output(self, text: str) -> None:
        """Sends partial output to the UI (ToolUIAdapter protocol)."""
        self.update_stream(text)

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

        path_hint = args.get("path") or args.get("filepath") or args.get("destination")

        for k, v in args.items():
            val_str = str(v)
            if len(val_str) > 60 or "\n" in val_str:
                self.console.print(f"    [bold]{k}:[/]")
                if tool_name in ("write_file", "edit_file", "read_file"):
                    lang = self._get_lexer_for_path(path_hint)
                elif "bash" in tool_name or "command" in tool_name:
                    lang = "bash"
                else:
                    lang = "text"
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
