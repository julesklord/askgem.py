import os
import shutil
from pathlib import Path
from rich.table import Table
from ....core.i18n import _
from ....core.paths import get_backups_dir
from ....core.security import ensure_safe_path
from .metadata import COMMAND_METADATA


def cmd_help(agent) -> Table:
    """Returns the help table as a Rich object."""
    table = Table(title=_("cmd.help.title"), show_header=True, header_style="bold #6366f1", box=None)
    table.add_column(_("cmd.help.header.cmd"), style="bold cyan")
    table.add_column(_("cmd.help.header.desc"))
    table.add_column("Example", style="dim")

    current_cat = None
    for cmd, meta in COMMAND_METADATA.items():
        cat = meta.get("category", "General")
        if cat != current_cat:
            table.add_section()
            table.add_row(f"[bold magenta]{cat}[/]", "", "")
            current_cat = cat

        example = meta.get("example", cmd)
        table.add_row(f"  {cmd}", meta["desc"], example)

    # Add global shortcuts
    table.add_section()
    table.add_row("[bold magenta]Global Shortcuts[/]", "", "")
    table.add_row("  [bold]Ctrl+C[/]", "Interrupt generation or exit", "N/A")

    return table


async def cmd_compact(agent) -> str:
    """Compresses conversation history."""
    return await agent.compress_history()


def cmd_undo(agent, args: list[str]) -> str:
    """Restores the last backed-up version of a file."""
    if not args:
        return "[warning]Usage: /undo <file_path>[/warning]"

    target_path = args[0]
    try:
        target_path = ensure_safe_path(target_path)
    except Exception as e:
        return f"[error]Invalid path: {e}[/error]"
    target_file = Path(target_path)
    backup_dir = get_backups_dir()
    try:
        rel_path = os.path.relpath(target_path, os.getcwd())
    except ValueError:
        rel_path = os.path.basename(target_path)
    found_backups = []
    if backup_dir.exists():
        for ts_folder in backup_dir.iterdir():
            if ts_folder.is_dir():
                potential_backup = ts_folder / rel_path
                if potential_backup.exists() and potential_backup.is_file():
                    found_backups.append((ts_folder.name, potential_backup))
    if not found_backups:
        return f"[error]No backups found for {target_file.name}[/error]"
    found_backups.sort(key=lambda x: x[0], reverse=True)
    latest_ts, latest_backup = found_backups[0]
    try:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(latest_backup, target_file)
        return f"[success]Restored {target_file.name} from backup ({latest_ts})[/success]"
    except Exception as e:
        return f"[error]Failed to restore backup: {e}[/error]"
