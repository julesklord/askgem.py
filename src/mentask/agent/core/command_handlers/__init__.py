"""
Modular commands package for mentask.
Exposes metadata and all sub-module command handler functions.
"""

from .config_cmds import (
    cmd_colorscheme,
    cmd_discover,
    cmd_init,
    cmd_mode,
    cmd_model,
    cmd_model_configure,
    cmd_multiline,
    cmd_speed,
    cmd_stream,
    cmd_theme,
    cmd_thinking,
)
from .dev_cmds import cmd_config, cmd_context, cmd_diff, cmd_export, cmd_git, cmd_retry
from .history_cmds import cmd_load, cmd_sessions
from .metadata import COMMAND_ALIASES, COMMAND_METADATA
from .security_cmds import cmd_auth, cmd_readonly
from .session_cmds import cmd_compact, cmd_help, cmd_undo
from .stats_cmds import cmd_artifacts, cmd_stats, cmd_usage

__all__ = [
    "cmd_colorscheme",
    "cmd_config",
    "cmd_context",
    "cmd_diff",
    "cmd_discover",
    "cmd_export",
    "cmd_git",
    "cmd_init",
    "cmd_mode",
    "cmd_model",
    "cmd_model_configure",
    "cmd_multiline",
    "cmd_retry",
    "cmd_speed",
    "cmd_stream",
    "cmd_theme",
    "cmd_thinking",
    "cmd_load",
    "cmd_sessions",
    "COMMAND_ALIASES",
    "COMMAND_METADATA",
    "cmd_auth",
    "cmd_readonly",
    "cmd_compact",
    "cmd_help",
    "cmd_undo",
    "cmd_artifacts",
    "cmd_stats",
    "cmd_usage",
]

