import os

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .memory_manager import MemoryManager
from .metrics import TokenTracker
from .paths import get_config_dir, get_history_dir, get_local_knowledge_path, get_memory_path


class AuditManager:
    """Consolidates system data for the --list CLI flag."""

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.memory = MemoryManager()
        self.metrics = TokenTracker(model_name=model_name)
        self.history_dir = get_history_dir()

    def list_db(self) -> Table:
        """Returns a table with the contents of global and local memory."""
        table = Table(title="[bold blue]mentask Knowledge DB[/bold blue]", box=None)
        table.add_column("Scope", style="cyan")
        table.add_column("Category", style="green")
        table.add_column("Fact", style="white")

        # Read both scopes
        for scope in ["global", "local"]:
            content = self.memory.read_memory(scope=scope)
            current_category = "General"
            for line in content.splitlines():
                if line.startswith("## "):
                    current_category = line.replace("## ", "").strip()
                elif line.startswith("- "):
                    table.add_row(scope.upper(), current_category, line.replace("- ", "").strip())

        return table

    def list_home(self) -> Table:
        """Returns a table with key application paths."""
        table = Table(title="[bold magenta]mentask Home Directories[/bold magenta]", box=None)
        table.add_column("Resource", style="cyan")
        table.add_column("Path", style="dim")

        table.add_row("Config Root", str(get_config_dir()))
        table.add_row("Global Memory", get_memory_path())
        table.add_row("Local Knowledge", get_local_knowledge_path())
        table.add_row("Sessions History", self.history_dir)

        return table

    def list_sessions(self) -> Table:
        """Lists saved sessions with metadata."""
        table = Table(title="[bold yellow]Saved Sessions[/bold yellow]", box=None)
        table.add_column("ID", style="cyan")
        table.add_column("Size", style="dim")

        if os.path.exists(self.history_dir):
            for f in os.listdir(self.history_dir):
                if f.endswith(".json"):
                    size = os.path.getsize(os.path.join(self.history_dir, f))
                    table.add_row(f.replace(".json", ""), f"{size / 1024:.1f} KB")

        return table

    def list_spend(self) -> Panel:
        """Returns a beautiful panel with historical spending and savings."""
        report = self.metrics.get_historical_report()

        stats = Text()
        stats.append("\n  💰 Total Investment: ", style="bold white")
        stats.append(f"${report['cost']:.4f}", style="bold green")
        stats.append(f"\n  📊 Total Tokens: {report['total']:,}", style="dim")
        stats.append(f" (In: {report['prompt']:,} | Out: {report['candidate']:,})", style="dim")

        stats.append("\n\n  🛡️  Efficiency (Compaction):", style="bold cyan")
        stats.append(f"\n  ✨ Tokens Avoided: {report['saved_tokens']:,}", style="bold green")
        stats.append("\n  🎁 Money Saved: ", style="dim")
        stats.append(f"${report['saved_cost']:.4f}", style="bold green")

        return Panel(
            stats, title="[bold green]Budget & Savings Report[/bold green]", border_style="green", expand=False
        )

    def list_changelog(self) -> Panel:
        """Returns the recent changes in mentask."""
        # For now, hardcoded from current release notes
        changes = (
            "[bold white]v0.10.0 - The Autonomous Engineer[/bold white]\n"
            "- [green]Added[/] Persistent Memory (Global/Local)\n"
            "- [green]Added[/] Context Auto-Compaction (Summarizer)\n"
            "- [green]Added[/] AI Resilience (Exponential Backoff)\n"
            "- [green]Added[/] Audit System (--list flags)\n"
            "- [green]Fixed[/] UI redundancy and redundant user input"
        )
        return Panel(changes, title="[bold white]Changelog[/bold white]", border_style="dim", expand=False)
