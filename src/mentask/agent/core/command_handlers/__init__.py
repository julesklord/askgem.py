"""
Modular commands package for mentask.
Exposes metadata and all sub-module command handler functions.
"""

from .metadata import COMMAND_METADATA, COMMAND_ALIASES
from .session_cmds import cmd_help, cmd_compact, cmd_undo
from .history_cmds import cmd_sessions, cmd_load
from .config_cmds import (
    cmd_model,
    cmd_model_configure,
    cmd_discover,
    cmd_mode,
    cmd_stream,
    cmd_speed,
    cmd_prompt,
    cmd_theme,
    cmd_thinking,
    cmd_multiline,
    cmd_init,
)
from .security_cmds import cmd_auth, cmd_readonly
from .stats_cmds import cmd_usage, cmd_stats, cmd_artifacts


# Stub for future implementation
async def cmd_export(agent, args: list[str]) -> str:
    format_type = args[0].lower() if args else "md"
    if format_type not in ("md", "html", "txt", "json"):
        return f"[warning]Unsupported format:[/warning] {format_type}\n[dim]Supported: md, html, txt, json[/dim]"
    return f"[info]Export to {format_type.upper()}:[/info] [dim]Coming soon - will export styled conversation[/dim]"
