"""
Modular commands package for mentask.
Exposes metadata and all sub-module command handler functions.
"""

from .config_cmds import (
    cmd_discover,
    cmd_init,
    cmd_mode,
    cmd_model,
    cmd_model_configure,
    cmd_multiline,
    cmd_prompt,
    cmd_speed,
    cmd_stream,
    cmd_theme,
    cmd_thinking,
)
from .history_cmds import cmd_load, cmd_sessions
from .metadata import COMMAND_ALIASES, COMMAND_METADATA
from .security_cmds import cmd_auth, cmd_readonly
from .session_cmds import cmd_compact, cmd_help, cmd_undo
from .stats_cmds import cmd_artifacts, cmd_stats, cmd_usage


# Stub for future implementation
async def cmd_export(agent, args: list[str]) -> str:
    format_type = args[0].lower() if args else "md"
    if format_type not in ("md", "html", "txt", "json"):
        return f"[warning]Unsupported format:[/warning] {format_type}\n[dim]Supported: md, html, txt, json[/dim]"
    return f"[info]Export to {format_type.upper()}:[/info] [dim]Coming soon - will export styled conversation[/dim]"
