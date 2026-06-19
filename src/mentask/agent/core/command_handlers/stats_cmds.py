from rich.console import Group
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from ....core.i18n import _
from ....core.compression import ContextSnapper


def cmd_usage(agent, args: list[str]) -> str | Panel:
    """Shows token usage summary."""
    if "--reset" in args or "-r" in args:
        agent.metrics.reset_historical()
        return "[success]Usage metrics and historical logs have been reset.[/success]"

    summary = agent.metrics.get_summary()
    return Panel(summary, title=_("cmd.usage.title"), border_style="#6366f1", expand=False)


def cmd_stats(agent) -> Panel:
    """Displays session stats."""
    table = Table(box=None, show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold #6366f1")
    table.add_column("Value")

    cost = agent.metrics.calculate_cost(
        agent.metrics.total_prompt_tokens, agent.metrics.total_candidate_tokens
    )

    table.add_row("🤖 Model", f"[bold yellow]{agent.model_name}[/bold yellow]")
    table.add_row("💬 Messages", _("cmd.stats.messages", count=agent.session_messages))
    table.add_row("🛠️ Tools", _("cmd.stats.tools", count=agent.session_tools))
    table.add_row("📝 Files", _("cmd.stats.files", count=agent.session_files))

    if agent.session.recent_files:
        recent = ", ".join([f"[cyan]{f}[/]" for f in agent.session.recent_files])
        table.add_row("📂 Recent", recent)

    table.add_section()

    # Token & Context Usage
    snapper = ContextSnapper(agent.model_name)
    total_tokens = agent.metrics.total_prompt_tokens + agent.metrics.total_candidate_tokens
    status = snapper.get_token_status(total_tokens)

    progress = ProgressBar(total=100, completed=status["percentage"], width=30, pulse=False)
    usage_color = "red" if status["is_dangerous"] else "yellow" if status["percentage"] > 50 else "green"

    table.add_row(
        "🪙 Tokens",
        f"[cyan]{total_tokens:,}[/] [dim](In: {agent.metrics.total_prompt_tokens:,} | Out: {agent.metrics.total_candidate_tokens:,})[/dim]",
    )
    table.add_row(
        "🧠 Context",
        Group(
            Text.from_markup(f"[{usage_color}]{status['percentage']}%[/] [dim]of {status['limit'] // 1000}K[/dim]"),
            progress,
        ),
    )
    table.add_row("💳 Est. Cost", f"[bold green]${cost:.5f}[/bold green]")

    return Panel(table, title=_("cmd.stats.title"), border_style="#6366f1", expand=False)


def cmd_artifacts(agent, args: list[str]) -> str | Table | bool:
    """Lists or expands tool artifacts."""
    if not hasattr(agent, "active_renderer"):
        return "[error]No renderer active.[/error]"

    renderer = agent.active_renderer
    if not args:
        if not renderer.artifacts:
            return "[warning]No artifacts stored.[/warning]"
        table = Table(title="Tool Artifacts", box=None)
        table.add_column("#", style="dim", justify="right")
        table.add_column("Tool", style="bold cyan")
        table.add_column("Size", justify="right")
        table.add_column("Preview")
        for i, (tool, content) in enumerate(renderer.artifacts, 1):
            size = f"{len(content):,} chars"
            preview = content[:60].replace("\n", " ")
            if len(content) > 60:
                preview += "..."
            table.add_row(str(i), tool, size, f"[dim]{preview}[/dim]")
        return table
    else:
        try:
            idx = int(args[0]) - 1
            renderer.expand_artifact(idx)
            return True
        except (ValueError, IndexError):
            return f"[error]Invalid artifact index: {args[0]}[/error]"
