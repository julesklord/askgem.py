import logging
import os

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .memory_manager import MemoryManager
from .metrics import TokenTracker
from .paths import get_config_dir, get_history_dir, get_local_knowledge_path, get_memory_path

_logger = logging.getLogger("mentask")


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
        from pathlib import Path

        changelog_path = None
        current = Path(__file__).resolve().parent
        for _ in range(5):
            candidate = current / "CHANGELOG.md"
            if candidate.exists():
                changelog_path = candidate
                break
            current = current.parent

        if not changelog_path and os.path.exists("CHANGELOG.md"):
            changelog_path = Path("CHANGELOG.md")

        md_text = ""
        if changelog_path:
            try:
                content = changelog_path.read_text(encoding="utf-8")
                # Parse the first version section (starts with "## [")
                lines = content.splitlines()
                section_lines = []
                started = False
                for line in lines:
                    if line.startswith("## ["):
                        if started:
                            break
                        started = True
                        section_lines.append(line)
                    elif started:
                        section_lines.append(line)
                if section_lines:
                    md_text = "\n".join(section_lines).strip()
            except Exception:
                _logger.debug("Failed to parse CHANGELOG.md, using hardcoded fallback")

        if not md_text:
            # Fallback to recent hardcoded release notes if CHANGELOG.md is not found or fails to read
            md_text = (
                "# v0.30.0 - Recent Updates\n\n"
                "### Added\n"
                "- **RAG Persistent Cache**: SQLite-backed disk cache for indexed workspaces.\n"
                "- **Git-Cliff Configuration**: Setup automatic generation of CHANGELOG.md.\n"
                "- **Dynamic CLI Changelog**: The `--list changelog` option dynamically parses CHANGELOG.md.\n"
                "- **Developer Guidelines**: Created a comprehensive `CONTRIBUTING.md` guide.\n\n"
                "### Changed\n"
                "- **MCP Resource Management**: Migrated MCP stdio and client sessions to `AsyncExitStack`.\n"
                "- **Strict Docstring Linting**: Integrated Google Style docstring linting (`D` rules) with Ruff."
            )

        from rich.markdown import Markdown
        return Panel(
            Markdown(md_text),
            title="[bold white]Changelog (Recent Changes)[/bold white]",
            border_style="dim",
            expand=False
        )
