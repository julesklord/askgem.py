"""
Slash command handling module for AskGem.

Parses and dispatches mid-conversation commands like /help, /model, /mode, etc.
"""

import logging
from typing import Any

from rich.panel import Panel
from rich.table import Table

from ...core.i18n import _

_logger = logging.getLogger("askgem")

# Hidden commands (not shown in /help but available): /speed, /export
COMMAND_METADATA = {
    "/help": {"desc": _("cmd.desc.help"), "example": "/help", "category": "General"},
    "/model": {"desc": _("cmd.desc.model_list"), "example": "/model [name]", "category": "Config"},
    "/mode": {"desc": _("cmd.desc.mode_manual"), "example": "/mode auto/manual", "category": "Config"},
    "/stream": {"desc": "Change streaming mode: continuous (full history) or transient (live updates)", "example": "/stream continuous/transient", "category": "Config"},
    "/clear": {"desc": _("cmd.desc.clear"), "example": "/clear", "category": "Session"},
    "/usage": {"desc": _("cmd.desc.usage"), "example": "/usage", "category": "Stats"},
    "/theme": {"desc": "Change UI theme", "example": "/theme emerald", "category": "Config"},
    "/stats": {"desc": _("cmd.desc.stats"), "example": "/stats", "category": "Stats"},
    "/compact": {"desc": "Compress conversation history to save tokens", "example": "/compact", "category": "Session"},
    "/sessions": {"desc": "List previous chat sessions", "example": "/sessions", "category": "Session"},
    "/load": {"desc": "Load a specific session", "example": "/load [id]", "category": "Session"},
    "/reset": {"desc": "Resets the session and counters", "example": "/reset", "category": "Session"},
    "/auth": {"desc": "Sets the Gemini API Key securely", "example": "/auth [your_key]", "category": "Security"},
    "/trust": {"desc": "Authorizes the current directory for auto-execution", "example": "/trust", "category": "Security"},
    "/untrust": {"desc": "Removes authorization from the current directory.", "example": "/untrust", "category": "Security"},
    "/stop": {"desc": "Interrupts the current generation", "example": "/stop", "category": "Control"},
    "/exit": {"desc": _("cmd.desc.exit"), "example": "/exit", "category": "Control"},
}


class CommandHandler:
    """Dispatches and executes slash commands."""

    def __init__(self, agent):
        self.agent = agent

    async def execute(self, user_input: str) -> Any | None:
        """Parses and dispatches a command.
        Returns:
            Optional[any]: A Rich renderable (Table/Panel) if the command has output,
                          or True if handled silently, or None if unknown.
        """
        parts = user_input.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if command == "/":
            return self._cmd_help()
        
        # Commands that take no arguments usually work better if they match exactly
        if command == "/help":
            return self._cmd_help()
        elif command == "/compact":
            return await self._cmd_compact()
        elif command == "/model":
            return await self._cmd_model(args)
        elif command == "/mode":
            return self._cmd_mode(args)
        elif command == "/stream":
            return self._cmd_stream(args)
        elif command == "/speed":
            return self._cmd_speed(args)
        elif command == "/clear":
            await self.agent.session.reset_session(self.agent._build_config())
            return f"[success]{_('cmd.clear.success')}[/success]"
        elif command == "/usage":
            return self._cmd_usage()
        elif command == "/stats":
            return self._cmd_stats()
        elif command == "/compact":
            return await self._cmd_compact()
        elif command == "/theme":
            return self._cmd_theme(args)
        elif command == "/sessions":
            return self._cmd_sessions()
        elif command == "/load":
            return await self._cmd_load(args)
        elif command == "/auth":
            return await self._cmd_auth(args)
        elif command == "/trust":
            import os
            cwd = os.getcwd()
            self.agent.orchestrator.trust.add_trust(cwd)
            return f"[success]✓ Directory added to trusted list:[/success] [dim]{cwd}[/dim]\n[dim]Tools will now execute automatically in this folder.[/dim]"
        elif command == "/untrust":
            import os
            cwd = os.getcwd()
            self.agent.orchestrator.trust.remove_trust(cwd)
            return f"[warning]! Directory removed from trusted list:[/warning] [dim]{cwd}[/dim]\n[dim]Confirmation will be required for all tools.[/dim]"
        elif command in ("/exit", "/quit", "/q"):
            self.agent.running = False
            return True
        elif command == "/stop":
            self.agent.stream_processor.interrupted = True
            return True
        elif command == "/reset":
            await self.agent.session.reset_session(self.agent._build_config())
            self.agent.session_messages = 0
            self.agent.session_tools = 0
            return "[bold red]Session reset.[/]"
        elif command == "/speed":
            # Hidden command: adjust stream delay
            return self._cmd_speed(args)
        elif command == "/export":
            # Hidden command: export conversation (stub for future implementation)
            return await self._cmd_export(args)
        elif command == "/init":
            # Hidden command: initialize local configuration
            return self._cmd_init()
        return None

    def _cmd_help(self) -> Table:
        """Returns the help table as a Rich object."""
        table = Table(title=_("cmd.help.title"), show_header=True, header_style="bold #6366f1", box=None)
        table.add_column(_("cmd.help.header.cmd"), style="bold cyan")
        table.add_column(_("cmd.help.header.desc"))
        table.add_column("Example", style="dim")

        for cmd, meta in COMMAND_METADATA.items():
            table.add_row(cmd, meta["desc"], meta["example"])
        return table

    async def _cmd_model(self, args: list[str]) -> str | Table:
        """Lists or switches Gemini models."""
        if not args:
            try:
                models_response = await self.agent.session.client.aio.models.list()
                table = Table(title=_("cmd.model.available"), box=None)
                table.add_column("Model", style="#4285F4")
                table.add_column("Status")
                async for m in models_response:
                    if "generateContent" in (m.supported_actions or []):
                        name = m.name.replace("models/", "")
                        status = "[success]Active[/success]" if name == self.agent.model_name else ""
                        table.add_row(name, status)
                return table
            except Exception as e:
                return f"[dim]Error listing models: {e}[/dim]"

        new_model = args[0]
        # Basic validation to avoid common typos (like 2.5)
        valid_prefixes = ("gemini-", "learnlm-", "lyria-", "nano-")
        if not any(new_model.startswith(p) for p in valid_prefixes):
            return f"[warning]Warning:[/] Model '{new_model}' might not be valid. Use [bold]/model[/] without arguments to see the list."

        self.agent.model_name = new_model
        self.agent.session.model_name = new_model

        # Persist the change
        self.agent.config.settings["model_name"] = new_model
        self.agent.config.save_settings()

        await self.agent.session.reset_session(self.agent._build_config())
        return f"[success]{_('cmd.model.switched')}[/success] [bold]{new_model}[/bold]"

    def _cmd_mode(self, args: list[str]) -> str:
        """Toggles edit mode."""
        if not args or args[0].lower() not in ("auto", "manual"):
            return f"[warning]{_('cmd.mode.current')}[/warning] [bold]{self.agent.edit_mode}[/bold]"
        mode = args[0].lower()
        self.agent.edit_mode = mode
        self.agent.config.settings["edit_mode"] = mode
        self.agent.config.save_settings()
        return f"[success]{_('cmd.mode.set')}[/success] [bold]{mode}[/bold]"

    def _cmd_stream(self, args: list[str]) -> str:
        """Changes streaming display mode."""
        if not args or args[0].lower() not in ("continuous", "transient"):
            current = self.agent.config.settings.get("stream_mode", "continuous")
            return f"[warning]Current stream mode:[/warning] [bold]{current}[/bold]\n[dim]Use: /stream continuous (full history) or /stream transient (live updates)[/dim]"
        
        mode = args[0].lower()
        self.agent.config.settings["stream_mode"] = mode
        self.agent.config.save_settings()
        
        # Update the active renderer if available
        if hasattr(self.agent, "active_renderer"):
            self.agent.active_renderer.stream_mode = mode
        
        return f"[success]Stream mode changed to:[/success] [bold]{mode}[/bold]\n[dim]{'Full history visible via scroll' if mode == 'continuous' else 'Live updates with final render'}[/dim]"

    def _cmd_speed(self, args: list[str]) -> str:
        """Adjusts stream delay for output pacing. Hidden command (not in /help)."""
        if not args:
            current = self.agent.config.settings.get("stream_delay", 0.015)
            return f"[warning]Current stream speed:[/warning] [bold]{current}s[/bold] ({int(current*1000)}ms)\n[dim]Usage: /speed 0.005 to 0.1 (lower=faster, higher=slower)[/dim]"
        
        try:
            delay = float(args[0])
            if delay < 0.001 or delay > 0.5:
                return f"[error]Speed must be between 0.001 and 0.5 seconds[/error]"
            
            self.agent.config.settings["stream_delay"] = delay
            self.agent.config.save_settings()
            
            # Update the active renderer if available
            if hasattr(self.agent, "active_renderer"):
                self.agent.active_renderer._stream_delay = delay
            
            return f"[success]Stream speed updated:[/success] [bold]{delay}s[/bold] ({int(delay*1000)}ms)\n[dim]This affects how quickly content appears[/dim]"
        except ValueError:
            return f"[error]Invalid speed value. Use a number like 0.01 or 0.05[/error]"

    def _cmd_usage(self) -> Panel:
        """Displays token usage."""
        summary = self.agent.metrics.get_summary()
        return Panel(summary, title=_("cmd.usage.title"), border_style="#6366f1")

    def _cmd_stats(self) -> Panel:
        """Displays session stats."""
        stats = (
            f"🤖 Model: [bold yellow]{self.agent.model_name}[/bold yellow]\n"
            f"🛠️ Tools Registered: [bold]{len(self.agent.tools.get_all_schemas())}[/bold]\n"
            f"📂 Recent Files: [bold]{len(self.agent.session.recent_files)}[/bold]"
        )
        return Panel(stats, title=_("cmd.stats.title"), border_style="#6366f1", expand=False)

    async def _cmd_compact(self) -> str:
        """Compresses conversation history."""
        return await self.agent.compress_history()

    def _cmd_theme(self, args: list[str]) -> str | Table:
        """Lists or switches UI themes."""
        if not args:
            table = Table(title="Available Themes", box=None)
            table.add_column("Theme", style="bold cyan")
            table.add_column("Status")
            current = self.agent.config.settings.get("theme", "indigo")

            from ...cli.renderer import CliRenderer

            for t_name in CliRenderer.THEMES:
                status = "[success]Active[/success]" if t_name == current else ""
                table.add_row(t_name, status)
            return table

        new_theme = args[0].lower()
        from ...cli.renderer import CliRenderer

        if new_theme not in CliRenderer.THEMES:
            return f"[error]Theme '{new_theme}' not found.[/error]"

        # Apply and persist
        self.agent.config.settings["theme"] = new_theme
        self.agent.config.save_settings()

        # We need to tell the renderer to update (it's held in the agent's start loop, but here we don't have its direct ref easily unless we pass it)
        # However, for the NEXT turn it will be loaded. To apply it NOW we'd need the renderer ref.
        # But ChatAgent.start holds the renderer in a local variable.
        # I'll add a 'renderer' attribute to ChatAgent.
        if hasattr(self.agent, "active_renderer"):
            self.agent.active_renderer.apply_theme(new_theme)

        return f"[success]Theme switched to:[/success] [bold]{new_theme}[/bold]"

    def _cmd_sessions(self) -> Table:
        """Lists all stored session IDs."""
        sessions = self.agent.history.list_sessions()
        if not sessions:
            return "[warning]No sessions found.[/warning]"

        table = Table(title="Conversation History", box=None)
        table.add_column("#", style="dim")
        table.add_column("Session ID", style="bold cyan")

        # Newest first
        for i, s_id in enumerate(reversed(sessions)):
            # Mark the current one
            prefix = "[success]→[/success] " if s_id == self.agent.history.current_session_id else "  "
            table.add_row(str(len(sessions) - i), f"{prefix}{s_id}")

        return table

    async def _cmd_load(self, args: list[str]) -> str:
        """Loads a session by ID or index."""
        if not args:
            return "[warning]Usage: /load [session_id or index][/warning]"

        sessions = self.agent.history.list_sessions()
        target_id = args[0]

        # Handle index
        if target_id.isdigit():
            idx = int(target_id)
            if 1 <= idx <= len(sessions):
                target_id = sessions[idx - 1]
            else:
                return f"[error]Index {idx} out of range (1-{len(sessions)}).[/error]"

        history = self.agent.history.load_session(target_id)
        if history is None:
            return f"[error]Could not load session '{target_id}'.[/error]"

        # Switch session
        self.agent.history.current_session_id = target_id
        await self.agent.session.reset_session(self.agent._build_config())
        await self.agent.session.ensure_session(self.agent._build_config(), history=history)

        return f"[success]Loaded session:[/success] [bold]{target_id}[/bold] ({len(history)} turns restored)"

    async def _cmd_auth(self, args: list[str]) -> str:
        """Sets the API Key securely and reinitializes the engine."""
        if not args:
            return "[warning]Usage: /auth [your_api_key][/warning]\n[dim]The key will be stored securely in your OS Keyring, NOT in this project.[/dim]"

        new_key = args[0].strip()
        success = self.agent.config.save_api_key(new_key)

        if success:
            # Force session reload with the new key
            try:
                import os
                env_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

                # 1. Update the settings instance in case they use settings.json (legacy/debug)
                self.agent.config.settings["google_api_key"] = new_key

                # 2. Re-setup API client
                await self.agent.session.setup_api()

                # 3. Reset the reasoning chat session
                await self.agent.session.reset_session(self.agent._build_config())

                msg = f"[success]API Key saved and engine reloaded![/success]\n[dim]The new key (***{new_key[-4:]}) is now active in memory.[/dim]"

                if env_key:
                    msg += (
                        "\n\n[bold yellow]⚠ ATTENTION:[/] An environment variable [cyan]GOOGLE_API_KEY[/cyan] was detected in your system. "
                        "Environment variables usually take [bold]PRIORITY[/bold] over stored keys. "
                        "If you still see 429 errors, you MUST delete or update the environment variable in your OS settings."
                    )

                return msg
            except Exception as e:
                return f"[error]Key saved but engine reload failed: {e}[/error]"

        return "[error]Failed to save API Key to OS Keyring. Check system permissions.[/error]"

    async def _cmd_export(self, args: list[str]) -> str:
        """Exports conversation in formatted style. Hidden command (stub for future implementation)."""
        format_type = args[0].lower() if args else "md"
        
        if format_type not in ("md", "html", "txt", "json"):
            return f"[warning]Unsupported format:[/warning] {format_type}\n[dim]Supported: md, html, txt, json[/dim]"
        
        return f"[info]Export to {format_type.upper()}:[/info] [dim]Coming soon - will export styled conversation[/dim]"

    def _cmd_init(self) -> str:
        """Initialize local configuration and trust for the current directory.
        
        Creates .askgem/settings.json in the current directory with current configuration
        and marks this directory as trusted.
        """
        import os
        import json
        from pathlib import Path
        
        cwd = Path.cwd()
        local_config_dir = cwd / ".askgem"
        local_config_file = local_config_dir / "settings.json"
        
        # Check if already initialized
        if local_config_file.exists():
            return f"[warning]Local configuration already exists:[/warning] [dim]{local_config_file}[/dim]"
        
        try:
            # Create .askgem directory
            local_config_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy current settings to local config
            local_settings = self.agent.config.settings.copy()
            
            with open(local_config_file, "w", encoding="utf-8") as f:
                json.dump(local_settings, f, indent=4)
            
            # Add directory to trusted list
            self.agent.orchestrator.trust.add_trust(str(cwd))
            
            return (
                f"[success]✓ Local configuration initialized:[/success] [dim]{local_config_file}[/dim]\n"
                f"[success]✓ Directory trusted:[/success] [dim]{cwd}[/dim]\n"
                f"[dim]From now on, AskGem will use local settings in this folder.[/dim]"
            )
        except Exception as e:
            return f"[error]Failed to initialize local config: {e}[/error]"
