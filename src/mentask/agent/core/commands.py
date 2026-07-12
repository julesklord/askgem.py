"""
Slash command handling module for mentask.

Parses and dispatches mid-conversation commands using a registry pattern.
"""

import difflib
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

from rich.table import Table

from ...core.i18n import _
from . import command_handlers as commands_pkg
from .command_handlers import COMMAND_ALIASES, COMMAND_METADATA

_logger = logging.getLogger("mentask.agent.commands")

# Type alias for command handlers: (agent, args) -> result
CommandHandlerFn = Callable[..., Any]
AsyncCommandHandlerFn = Callable[..., Awaitable[Any]]


def _build_command_registry() -> dict[str, AsyncCommandHandlerFn]:
    """Builds the command registry mapping command names to handler functions.

    Returns:
        Dict mapping command name (e.g. '/help') to an async handler.
    """

    async def _cmd_help(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_help(agent)

    async def _cmd_compact(agent: Any, args: list[str]) -> Any:
        return await commands_pkg.cmd_compact(agent)

    async def _cmd_model(agent: Any, args: list[str]) -> Any:
        return await commands_pkg.cmd_model(agent, args)

    async def _cmd_mode(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_mode(agent, args)

    async def _cmd_stream(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_stream(agent, args)

    async def _cmd_speed(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_speed(agent, args)

    async def _cmd_clear(agent: Any, args: list[str]) -> Any:
        agent.history.reset()
        agent.is_new_session = True
        agent.session_messages = 0
        await agent.session.reset_session(agent._build_config())
        return f"[success]{_('cmd.clear.success')}[/success]"

    async def _cmd_usage(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_usage(agent, args)

    async def _cmd_stats(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_stats(agent)

    async def _cmd_colorscheme(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_colorscheme(agent, args)

    async def _cmd_thinking(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_thinking(agent, args)

    async def _cmd_multiline(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_multiline(agent, args)

    async def _cmd_artifacts(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_artifacts(agent, args)

    async def _cmd_sessions(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_sessions(agent)

    async def _cmd_load(agent: Any, args: list[str]) -> Any:
        return await commands_pkg.cmd_load(agent, args)

    async def _cmd_auth(agent: Any, args: list[str]) -> Any:
        return await commands_pkg.cmd_auth(agent, args)

    async def _cmd_trust(agent: Any, args: list[str]) -> Any:
        cwd = os.getcwd()
        await agent.orchestrator.trust.add_trust(cwd)
        return f"[success]✓ Directory added to trusted list:[/success] [dim]{cwd}[/dim]\n[dim]Tools will now execute automatically in this folder.[/dim]"

    async def _cmd_untrust(agent: Any, args: list[str]) -> Any:
        cwd = os.getcwd()
        await agent.orchestrator.trust.remove_trust(cwd)
        return f"[warning]! Directory removed from trusted list:[/warning] [dim]{cwd}[/dim]\n[dim]Confirmation will be required for all tools.[/dim]"

    async def _cmd_readonly(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_readonly(agent, args)

    async def _cmd_undo(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_undo(agent, args)

    async def _cmd_exit(agent: Any, args: list[str]) -> Any:
        agent.running = False
        return True

    async def _cmd_stop(agent: Any, args: list[str]) -> Any:
        agent.interrupted = True
        return True

    async def _cmd_reset(agent: Any, args: list[str]) -> Any:
        agent.history.reset()
        agent.is_new_session = True
        await agent.session.reset_session(agent._build_config())
        agent.session_messages = 0
        agent.session_tools = 0
        return "[bold red]Session reset.[/]"

    async def _cmd_discover(agent: Any, args: list[str]) -> Any:
        return await commands_pkg.cmd_discover(agent, args)

    async def _cmd_theme(agent: Any, args: list[str]) -> Any:
        return commands_pkg.cmd_theme(agent, args)

    async def _cmd_init(agent: Any, args: list[str]) -> Any:
        return await commands_pkg.cmd_init(agent)

    return {
        "/help": _cmd_help,
        "/": _cmd_help,
        "/compact": _cmd_compact,
        "/model": _cmd_model,
        "/mode": _cmd_mode,
        "/stream": _cmd_stream,
        "/speed": _cmd_speed,
        "/clear": _cmd_clear,
        "/usage": _cmd_usage,
        "/stats": _cmd_stats,
        "/colorscheme": _cmd_colorscheme,
        "/thinking": _cmd_thinking,
        "/multiline": _cmd_multiline,
        "/artifacts": _cmd_artifacts,
        "/sessions": _cmd_sessions,
        "/load": _cmd_load,
        "/auth": _cmd_auth,
        "/trust": _cmd_trust,
        "/untrust": _cmd_untrust,
        "/readonly": _cmd_readonly,
        "/undo": _cmd_undo,
        "/exit": _cmd_exit,
        "/stop": _cmd_stop,
        "/reset": _cmd_reset,
        "/discover": _cmd_discover,
        "/theme": _cmd_theme,
        "/init": _cmd_init,
    }


class CommandHandler:
    """Dispatches and executes slash commands via a registry lookup."""

    def __init__(self, agent):
        self.agent = agent
        self._registry = _build_command_registry()

    def get_all_commands(self) -> list[str]:
        """Returns a list of all available slash commands including aliases."""
        return list(COMMAND_METADATA.keys()) + list(COMMAND_ALIASES.keys())

    async def execute(self, user_input: str) -> Any | None:
        """Parses and dispatches a command via registry lookup."""
        parts = user_input.split()
        if not parts:
            return None

        raw_command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # Resolve alias
        command = COMMAND_ALIASES.get(raw_command, raw_command)

        # Registry lookup — O(1) instead of O(n) if/elif chain
        handler = self._registry.get(command)
        if handler is not None:
            return await handler(self.agent, args)

        # Handle unknown commands with explanation
        return self._unknown_command_response(raw_command)

    def _unknown_command_response(self, raw_command: str) -> Table:
        """Builds a helpful response for unknown commands."""
        all_cmds = sorted(self.get_all_commands())
        suggestions = difflib.get_close_matches(raw_command, all_cmds, n=1, cutoff=0.6)

        explanation = Table(title=f"Unknown command: [bold red]{raw_command}[/]", box=None, padding=(0, 2))
        explanation.add_column("Available Command", style="bold cyan")
        explanation.add_column("Description", style="dim")

        to_show = all_cmds[:8]
        if suggestions:
            explanation.caption = f"Did you mean [bold cyan]{suggestions[0]}[/bold cyan]?"

        for cmd in to_show:
            if cmd in COMMAND_METADATA:
                explanation.add_row(cmd, COMMAND_METADATA[cmd]["desc"])

        explanation.add_section()
        explanation.add_row("/help", "Show full command list and usage examples")

        return explanation
