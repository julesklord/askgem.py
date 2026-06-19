"""
Slash command handling module for mentask.

Parses and dispatches mid-conversation commands like /help, /model, /mode, etc.
"""

import difflib
import logging
from typing import Any

from rich.table import Table

from ...core.i18n import _
from . import command_handlers as commands_pkg
from .command_handlers import COMMAND_ALIASES, COMMAND_METADATA

_logger = logging.getLogger("mentask")


class CommandHandler:
    """Dispatches and executes slash commands."""

    def __init__(self, agent):
        self.agent = agent

    def get_all_commands(self) -> list[str]:
        """Returns a list of all available slash commands including aliases."""
        return list(COMMAND_METADATA.keys()) + list(COMMAND_ALIASES.keys())

    async def execute(self, user_input: str) -> Any | None:
        """Parses and dispatches a command."""
        parts = user_input.split()
        if not parts:
            return None

        raw_command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # Resolve alias
        command = COMMAND_ALIASES.get(raw_command, raw_command)

        if command in ("/", "/help"):
            return commands_pkg.cmd_help(self.agent)
        elif command == "/compact":
            return await commands_pkg.cmd_compact(self.agent)
        elif command == "/model":
            return await commands_pkg.cmd_model(self.agent, args)
        elif command == "/mode":
            return commands_pkg.cmd_mode(self.agent, args)
        elif command == "/stream":
            return commands_pkg.cmd_stream(self.agent, args)
        elif command == "/speed":
            return commands_pkg.cmd_speed(self.agent, args)
        elif command == "/clear":
            self.agent.history.reset()
            self.agent.is_new_session = True
            self.agent.session_messages = 0
            await self.agent.session.reset_session(self.agent._build_config())
            return f"[success]{_('cmd.clear.success')}[/success]"
        elif command == "/usage":
            return commands_pkg.cmd_usage(self.agent, args)
        elif command == "/stats":
            return commands_pkg.cmd_stats(self.agent)
        elif command == "/theme":
            return commands_pkg.cmd_theme(self.agent, args)
        elif command == "/thinking":
            return commands_pkg.cmd_thinking(self.agent, args)
        elif command == "/multiline":
            return commands_pkg.cmd_multiline(self.agent, args)
        elif command == "/artifacts":
            return commands_pkg.cmd_artifacts(self.agent, args)
        elif command == "/sessions":
            return commands_pkg.cmd_sessions(self.agent)
        elif command == "/load":
            return await commands_pkg.cmd_load(self.agent, args)
        elif command == "/auth":
            return await commands_pkg.cmd_auth(self.agent, args)
        elif command == "/trust":
            import os

            cwd = os.getcwd()
            await self.agent.orchestrator.trust.add_trust(cwd)
            return f"[success]✓ Directory added to trusted list:[/success] [dim]{cwd}[/dim]\n[dim]Tools will now execute automatically in this folder.[/dim]"
        elif command == "/untrust":
            import os

            cwd = os.getcwd()
            await self.agent.orchestrator.trust.remove_trust(cwd)
            return f"[warning]! Directory removed from trusted list:[/warning] [dim]{cwd}[/dim]\n[dim]Confirmation will be required for all tools.[/dim]"
        elif command == "/readonly":
            return commands_pkg.cmd_readonly(self.agent, args)
        elif command == "/undo":
            return commands_pkg.cmd_undo(self.agent, args)
        elif command == "/exit":
            self.agent.running = False
            return True
        elif command == "/stop":
            self.agent.interrupted = True
            return True
        elif command == "/reset":
            self.agent.history.reset()
            self.agent.is_new_session = True
            await self.agent.session.reset_session(self.agent._build_config())
            self.agent.session_messages = 0
            self.agent.session_tools = 0
            return "[bold red]Session reset.[/]"
        elif command == "/discover":
            return await commands_pkg.cmd_discover(self.agent, args)
        elif command == "/prompt":
            return commands_pkg.cmd_prompt(self.agent, args)
        elif command == "/init":
            return await commands_pkg.cmd_init(self.agent)

        # Handle unknown commands with explanation
        all_cmds = sorted(self.get_all_commands())
        suggestions = difflib.get_close_matches(raw_command, all_cmds, n=1, cutoff=0.6)

        explanation = Table(title=f"Unknown command: [bold red]{raw_command}[/]", box=None, padding=(0, 2))
        explanation.add_column("Available Command", style="bold cyan")
        explanation.add_column("Description", style="dim")

        # Show top relevant or just first few
        to_show = all_cmds[:8]
        if suggestions:
            explanation.caption = f"Did you mean [bold cyan]{suggestions[0]}[/bold cyan]?"

        for cmd in to_show:
            if cmd in COMMAND_METADATA:
                explanation.add_row(cmd, COMMAND_METADATA[cmd]["desc"])

        explanation.add_section()
        explanation.add_row("/help", "Show full command list and usage examples")

        return explanation
