"""Development utility commands: /export, /git, /diff, /context, /retry, /config."""

import contextlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from ....agent.schema import AssistantMessage, Role


def _run_git(args: list[str]) -> tuple[int, str]:
    """Run a git command and return (returncode, output)."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return result.returncode, result.stdout.strip() or result.stderr.strip()
    except FileNotFoundError:
        return 1, "git not found in PATH"
    except subprocess.TimeoutExpired:
        return 1, "git command timed out"


# ── /export ───────────────────────────────────────────────────────────────────


def cmd_export(agent: Any, args: list[str]) -> str:
    """Exports the current conversation to a file."""
    fmt = args[0].lower() if args else "md"
    if fmt not in ("md", "html", "txt", "json"):
        return f"[warning]Unsupported format:[/warning] {fmt}\n[dim]Supported: md, html, txt, json[/dim]"

    messages = agent.messages
    if not messages:
        return "[warning]No messages to export.[/warning]"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path.cwd() / "mentask_exports"
    out_dir.mkdir(exist_ok=True)

    if fmt == "json":
        data = []
        for m in messages:
            entry: dict[str, Any] = {"role": m.role.value, "content": m.content}
            if m.thought:
                entry["thought"] = m.thought
            if isinstance(m, AssistantMessage):
                entry["model"] = m.model
                if m.tool_calls:
                    entry["tool_calls"] = [
                        {"name": tc.name, "arguments": tc.arguments} for tc in m.tool_calls
                    ]
            data.append(entry)
        path = out_dir / f"conversation_{ts}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    elif fmt == "md":
        lines = [f"# Mentask Conversation — {ts}\n"]
        for m in messages:
            if m.role == Role.USER:
                content = m.content if isinstance(m.content, str) else str(m.content)
                lines.append(f"## User\n\n{content}\n")
            elif m.role == Role.ASSISTANT:
                content = m.content if isinstance(m.content, str) else str(m.content)
                lines.append(f"## Assistant\n\n{content}\n")
        path = out_dir / f"conversation_{ts}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
    elif fmt == "txt":
        lines = []
        for m in messages:
            content = m.content if isinstance(m.content, str) else str(m.content)
            lines.append(f"[{m.role.value.upper()}] {content}\n")
        path = out_dir / f"conversation_{ts}.txt"
        path.write_text("\n".join(lines), encoding="utf-8")
    elif fmt == "html":
        parts = [f"<h1>Mentask Conversation — {ts}</h1>"]
        for m in messages:
            content = m.content if isinstance(m.content, str) else str(m.content)
            tag = "div"
            parts.append(f'<{tag} class="{m.role.value}"><strong>{m.role.value.title()}</strong><p>{content}</p></{tag}>')
        path = out_dir / f"conversation_{ts}.html"
        path.write_text("\n".join(parts), encoding="utf-8")

    return f"[success]Conversation exported:[/success] [dim]{path}[/dim]"


# ── /git ──────────────────────────────────────────────────────────────────────


def cmd_git(agent: Any, args: list[str]) -> str | Table:
    """Shows git status, diff summary, or recent log."""
    sub = args[0] if args else "status"

    if sub == "status":
        code, out = _run_git(["status", "--short"])
        if code != 0:
            return f"[error]{out}[/error]"
        if not out:
            return "[success]Working tree clean.[/success]"
        table = Table(title="Git Status", box=None)
        table.add_column("File", style="bold cyan")
        table.add_column("Status", style="dim")
        for line in out.splitlines():
            if len(line) >= 3:
                table.add_row(line[3:], line[:2].strip())
            else:
                table.add_row(line, "")
        return table

    elif sub == "diff":
        ref = args[1] if len(args) > 1 else "HEAD"
        code, out = _run_git(["diff", "--stat", ref])
        if code != 0:
            return f"[error]{out}[/error]"
        if not out:
            return "[success]No changes.[/success]"
        return Panel(Syntax(out, "diff", theme="monokai", background_color="default"),
                     title=f"Git Diff ({ref})", border_style="dim cyan")

    elif sub == "log":
        count = 10
        if len(args) > 1:
            with contextlib.suppress(ValueError):
                count = int(args[1])
        code, out = _run_git(["log", f"-{count}", "--oneline", "--graph", "--decorate"])
        if code != 0:
            return f"[error]{out}[/error]"
        return Panel(Syntax(out, "git", theme="monokai", background_color="default"),
                     title=f"Last {count} Commits", border_style="dim cyan")

    return "[warning]Usage: /git [status|diff|log] [args][/warning]"


# ── /diff ─────────────────────────────────────────────────────────────────────


def cmd_diff(agent: Any, args: list[str]) -> str | Panel:
    """Shows uncommitted changes (staged + unstaged)."""
    if args:
        # Diff a specific file
        file_path = args[0]
        code, out = _run_git(["diff", "--", file_path])
        if code != 0:
            return f"[error]{out}[/error]"
        if not out:
            # Try staged
            code, out = _run_git(["diff", "--cached", "--", file_path])
            if code != 0:
                return f"[error]{out}[/error]"
            if not out:
                return f"[dim]No changes in {file_path}[/dim]"
        return Panel(Syntax(out, "diff", theme="monokai", background_color="default"),
                     title=f"Diff: {file_path}", border_style="dim cyan")

    # General diff
    code, out = _run_git(["diff"])
    if code != 0:
        return f"[error]{out}[/error]"

    code2, out2 = _run_git(["diff", "--cached"])
    combined = ""
    if out2:
        combined = f"--- Staged ---\n{out2}\n\n"
    if out:
        combined += f"--- Unstaged ---\n{out}"

    if not combined:
        return "[success]No uncommitted changes.[/success]"

    return Panel(Syntax(combined, "diff", theme="monokai", background_color="default"),
                 title="Uncommitted Changes", border_style="dim cyan")


# ── /context ──────────────────────────────────────────────────────────────────


def cmd_context(agent: Any, args: list[str]) -> Panel:
    """Shows current context token usage and limits."""
    from ....core.compression import ContextSnapper

    snapper = ContextSnapper(agent.model_name)
    current_tokens = sum(
        getattr(m, "usage", type("", (), {"input_tokens": 0, "output_tokens": 0})()).input_tokens
        + getattr(m, "usage", type("", (), {"input_tokens": 0, "output_tokens": 0})()).output_tokens
        for m in agent.messages
        if hasattr(m, "usage")
    )

    status = snapper.get_token_status(current_tokens)
    pct = status.get("percentage", 0)
    limit = status.get("limit", 0)
    is_danger = status.get("is_dangerous", False)

    bar_len = 30
    filled = int(bar_len * min(pct, 1.0))
    bar = "█" * filled + "░" * (bar_len - filled)
    bar_color = "red" if is_danger else ("yellow" if pct > 0.5 else "green")

    table = Table(box=None)
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Model", agent.model_name)
    table.add_row("Messages", str(len(agent.messages)))
    table.add_row("Tokens Used", f"{current_tokens:,}")
    table.add_row("Token Limit", f"{limit:,}")
    table.add_row("Usage", Text(f"{bar} {pct:.1%}", style=bar_color))
    table.add_row("Threshold", f"{snapper.threshold_pct:.0%}")
    table.add_row("Status", "[red]⚠ Near limit[/red]" if is_danger else "[green]OK[/green]")

    return Panel(table, title="Context Status", border_style="dim cyan")


# ── /retry ────────────────────────────────────────────────────────────────────


def cmd_retry(agent: Any, args: list[str]) -> str:
    """Re-sends the last user message to re-trigger a response."""
    if not agent.messages:
        return "[warning]No messages in history to retry.[/warning]"

    # Find the last user message
    last_user_msg = None
    for msg in reversed(agent.messages):
        if msg.role == Role.USER:
            last_user_msg = msg
            break

    if not last_user_msg:
        return "[warning]No user message found to retry.[/warning]"

    content = last_user_msg.content if isinstance(last_user_msg.content, str) else str(last_user_msg.content)
    return f"[info]Retrying:[/info] {content[:200]}"


# ── /config ───────────────────────────────────────────────────────────────────


def cmd_config(agent: Any, args: list[str]) -> Panel:
    """Shows current configuration settings."""
    settings = agent.config.settings

    # Mask sensitive keys
    sensitive = {
        "google_api_key", "openai_api_key", "deepseek_api_key",
        "anthropic_api_key", "mistral_api_key", "groq_api_key",
        "together_api_key", "perplexity_api_key",
        "google_search_api_key", "google_cx_id",
    }

    table = Table(box=None)
    table.add_column("Setting", style="bold cyan")
    table.add_column("Value")

    # Show important settings first
    important = ["model_name", "edit_mode", "theme", "prompt_style", "stream_mode",
                 "stream_delay", "temperature", "multiline_prompt", "readonly_mode",
                 "nerdfonts_enabled", "show_thinking"]
    shown: set[str] = set()

    for key in important:
        if key in settings:
            val = settings[key]
            if key in sensitive:
                val = f"{str(val)[:4]}..." if val else "(not set)"
            table.add_row(key, str(val))
            shown.add(key)

    # Then remaining
    for key in sorted(settings):
        if key not in shown:
            val = settings[key]
            if key in sensitive:
                val = f"{str(val)[:4]}..." if val else "(not set)"
            table.add_row(key, str(val))

    return Panel(table, title="Configuration", border_style="dim cyan")
