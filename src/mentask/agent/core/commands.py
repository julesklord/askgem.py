"""
Slash command handling module for mentask.

Parses and dispatches mid-conversation commands like /help, /model, /mode, etc.
"""

import logging
from typing import Any

from rich.panel import Panel
from rich.table import Table

from ...core.i18n import _

_logger = logging.getLogger("mentask")

# Organized by category for coherence in /help
COMMAND_METADATA = {
    # --- Session & Conversation ---
    "/help": {"desc": _("cmd.desc.help"), "example": "/help", "category": "Session"},
    "/clear": {"desc": _("cmd.desc.clear"), "example": "/clear", "category": "Session"},
    "/compact": {"desc": "Compress conversation history to save tokens", "example": "/compact", "category": "Session"},
    "/reset": {"desc": "Resets the session and counters", "example": "/reset", "category": "Session"},
    "/undo": {"desc": "Restore last backed-up version of a file", "example": "/undo <path>", "category": "Session"},
    # --- History Management ---
    "/sessions": {"desc": "List previous chat sessions", "example": "/sessions", "category": "History"},
    "/load": {"desc": "Load a specific session", "example": "/load <id>", "category": "History"},
    # --- Configuration & Discovery ---
    "/model": {"desc": _("cmd.desc.model_list"), "example": "/model [name]", "category": "Config"},
    "/discover": {"desc": _("cmd.desc.discover"), "example": "/discover [query]", "category": "Config"},
    "/mode": {"desc": _("cmd.desc.mode_manual"), "example": "/mode auto/manual", "category": "Config"},
    "/stream": {"desc": "Change streaming display mode", "example": "/stream transient", "category": "Config"},
    "/theme": {"desc": "List or change UI themes", "example": "/theme [name]", "category": "Config"},
    "/init": {"desc": "Initialize local project isolation and configuration", "example": "/init", "category": "Config"},
    # --- Security ---
    "/auth": {"desc": "Sets the Gemini API Key securely", "example": "/auth <key>", "category": "Security"},
    "/trust": {"desc": "Authorizes current directory for auto-execution", "example": "/trust", "category": "Security"},
    "/untrust": {"desc": "Removes authorization from current directory", "example": "/untrust", "category": "Security"},
    # --- Stats & Tools ---
    "/usage": {"desc": "Show current and global token usage", "example": "/usage [--reset]", "category": "Stats"},
    "/stats": {"desc": _("cmd.desc.stats"), "example": "/stats", "category": "Stats"},
    "/prompt": {"desc": "Customize the interactive prompt", "example": "/prompt --theme atomic", "category": "Config"},
    "/artifacts": {"desc": "List or expand tool artifacts", "example": "/artifacts [idx]", "category": "Tools"},
    # --- Control ---
    "/stop": {"desc": "Interrupts the current generation", "example": "/stop", "category": "Control"},
    "/exit": {"desc": _("cmd.desc.exit"), "example": "/exit", "category": "Control"},
}


class CommandHandler:
    """Dispatches and executes slash commands."""

    def __init__(self, agent):
        self.agent = agent

    def get_all_commands(self) -> list[str]:
        """Returns a list of all available slash commands."""
        return list(COMMAND_METADATA.keys())

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
            return self._cmd_usage(args)
        elif command == "/stats":
            return self._cmd_stats()
        elif command in ("/themes", "/theme"):
            return self._cmd_theme(args)
        elif command in ("/artifacts", "/art"):
            return self._cmd_artifacts(args)
        elif command == "/sessions":
            return self._cmd_sessions()
        elif command == "/load":
            return await self._cmd_load(args)
        elif command == "/auth":
            return await self._cmd_auth(args)
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
        elif command == "/undo":
            return self._cmd_undo(args)
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
        elif command == "/discover":
            return await self._cmd_discover(args)
        elif command == "/prompt":
            return self._cmd_prompt(args)
        elif command == "/init":
            return await self._cmd_init()

        return f"[error]{_('cmd.unknown')} {command}[/error] {_('cmd.hint_help')}"

    def _cmd_help(self) -> Table:
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

            table.add_row(f"  {cmd}", meta["desc"], meta["example"])

        # Add global shortcuts
        table.add_section()
        table.add_row("[bold magenta]Global Shortcuts[/]", "", "")
        table.add_row("  [bold]Ctrl+O[/]", "Expand last tool artifact", "N/A")
        table.add_row("  [bold]Ctrl+C[/]", "Interrupt generation or exit", "N/A")

        return table

    async def _cmd_model(self, args: list[str]) -> str | Table:
        """Lists or switches models for the active provider."""
        if not args:
            try:
                models = await self.agent.session.provider.list_models()
                if not models:
                    return "[warning]No models found for the current provider.[/warning]"

                table = Table(title=_("cmd.model.available"), box=None)
                table.add_column("Model", style="#4285F4")
                table.add_column("Status")

                for name in models:
                    status = "[success]Active[/success]" if name == self.agent.model_name else ""
                    table.add_row(name, status)
                return table
            except Exception as e:
                return f"[dim]Error listing models: {e}[/dim]"

        new_model = args[0]
        self.agent.model_name = new_model

        # Swapping provider if necessary
        await self.agent.session.switch_model(new_model)

        # Persist the change
        self.agent.config.settings["model_name"] = new_model
        self.agent.config.save_settings()

        await self.agent.session.reset_session(self.agent._build_config())
        return f"[success]{_('cmd.model.switched')}[/success] [bold]{new_model}[/bold]"

    async def _cmd_discover(self, args: list[str]) -> Table | str:
        """Searches and displays models from models.dev Hub."""
        from ...core.models_hub import hub

        query = args[0] if args else ""

        hub.sync()  # Ensure it's synced

        capability = ""
        if query in ("vision", "tools", "reasoning"):
            capability = query
            query = ""

        results = hub.search(query=query, capability=capability)

        if not results:
            return (
                f"[warning]No models found matching '[bold]{query or capability}[/bold]' in models.dev Hub.[/warning]"
            )

        table = Table(title=f"Models.dev Catalog ({len(results)} matches)", box=None)
        table.add_column("ID", style="bold cyan")
        table.add_column("Provider", style="dim")
        table.add_column("Price (1M)", justify="right")
        table.add_column("Context", justify="right")
        table.add_column("Features")

        # Sort by price (input)
        results.sort(key=lambda x: x.get("cost", {}).get("input", 0))

        for m in results[:20]:  # Limit to top 20
            cost = m.get("cost", {})
            pricing = f"[green]${cost.get('input', 0):.2f}[/] / [blue]${cost.get('output', 0):.2f}[/]"

            context = f"{m.get('limit', {}).get('context', 0) // 1000}K"

            features = []
            if m.get("attachment"):
                features.append("👁️")
            if m.get("tool_call"):
                features.append("🛠️")
            if m.get("reasoning"):
                features.append("🧠")

            table.add_row(m.get("id"), m.get("_provider_name", ""), pricing, context, " ".join(features))

        if len(results) > 20:
            table.caption = f"[dim]... and {len(results) - 20} more. Refine your query to see others.[/dim]"

        return table

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
            return f"[warning]Current stream speed:[/warning] [bold]{current}s[/bold] ({int(current * 1000)}ms)\n[dim]Usage: /speed 0.005 to 0.1 (lower=faster, higher=slower)[/dim]"

        try:
            delay = float(args[0])
            if delay < 0.001 or delay > 0.5:
                return "[error]Speed must be between 0.001 and 0.5 seconds[/error]"

            self.agent.config.settings["stream_delay"] = delay
            self.agent.config.save_settings()

            # Update the active renderer if available
            if hasattr(self.agent, "active_renderer"):
                self.agent.active_renderer._stream_delay = delay

            return f"[success]Stream speed updated:[/success] [bold]{delay}s[/bold] ({int(delay * 1000)}ms)\n[dim]This affects how quickly content appears[/dim]"
        except ValueError:
            return "[error]Invalid speed value. Use a number like 0.01 or 0.05[/error]"

    def _cmd_usage(self, args: list[str]) -> str | Panel:
        """Shows token usage summary."""
        if "--reset" in args or "-r" in args:
            self.agent.metrics.reset_historical()
            return "[success]Usage metrics and historical logs have been reset.[/success]"

        summary = self.agent.metrics.get_summary()
        return Panel(summary, title=_("cmd.usage.title"), border_style="#6366f1", expand=False)

    def _cmd_prompt(self, args: list[str]) -> str:
        """Handles prompt customization."""
        if not hasattr(self.agent, "active_renderer"):
            return "[error]No active renderer to configure prompt.[/error]"

        engine = self.agent.active_renderer.prompt_engine
        available_styles = list(engine.STYLES.keys())

        if not args:
            style = self.agent.config.settings.get("prompt_style", "atomic")
            nf = self.agent.config.settings.get("nerdfonts_enabled", True)
            return (
                f"🎨 [bold]Prompt Settings[/bold]\n"
                f"  Style: [cyan]{style}[/cyan]\n"
                f"  Nerdfonts: [{'green' if nf else 'red'}]{'Enabled' if nf else 'Disabled'}[/]\n\n"
                f"Available Styles: [dim]{', '.join(available_styles)}[/dim]\n"
                f"[dim]Usage: /prompt --theme <style>\n"
                f"       /prompt --nerdfonts on|off[/dim]"
            )

        if "--theme" in args:
            idx = args.index("--theme")
            if idx + 1 < len(args):
                theme = args[idx + 1].lower()
                if theme not in available_styles:
                    return f"[error]Style '{theme}' not found. Available: {', '.join(available_styles)}[/error]"

                self.agent.config.settings["prompt_style"] = theme
                self.agent.config.save_settings()
                if hasattr(self.agent, "active_renderer"):
                    self.agent.active_renderer.prompt_style = theme
                return f"[success]Prompt style changed to [bold]{theme}[/bold][/success]"

        if "--nerdfonts" in args:
            idx = args.index("--nerdfonts")
            if idx + 1 < len(args):
                val = args[idx + 1].lower() in ("on", "true", "yes", "1")
                self.agent.config.settings["nerdfonts_enabled"] = val
                self.agent.config.save_settings()
                if hasattr(self.agent, "active_renderer"):
                    self.agent.active_renderer.prompt_engine.use_nerdfonts = val
                return f"[success]Nerdfonts {'enabled' if val else 'disabled'}.[/success]"

        return "[error]Invalid /prompt arguments.[/error]"

    def _cmd_stats(self) -> Panel:
        """Displays session stats."""
        table = Table(box=None, show_header=False, padding=(0, 1))
        table.add_column("Key", style="bold #6366f1")
        table.add_column("Value")

        cost = self.agent.metrics.calculate_cost(
            self.agent.metrics.total_prompt_tokens, self.agent.metrics.total_candidate_tokens
        )

        table.add_row("🤖 Model", f"[bold yellow]{self.agent.model_name}[/bold yellow]")
        table.add_row("💬 Messages", _("cmd.stats.messages", count=self.agent.session_messages))
        table.add_row("🛠️ Tools", _("cmd.stats.tools", count=self.agent.session_tools))
        table.add_row("📂 Recent Files", f"[bold]{len(self.agent.session.recent_files)}[/bold]")
        table.add_section()
        table.add_row(
            "🪙 Tokens",
            f"[cyan]{self.agent.metrics.total_prompt_tokens + self.agent.metrics.total_candidate_tokens:,}[/] [dim](In: {self.agent.metrics.total_prompt_tokens:,} | Out: {self.agent.metrics.total_candidate_tokens:,})[/dim]",
        )
        table.add_row("💳 Est. Cost", f"[bold green]${cost:.5f}[/bold green]")

        return Panel(table, title=_("cmd.stats.title"), border_style="#6366f1", expand=False)

    async def _cmd_compact(self) -> str:
        """Compresses conversation history."""
        return await self.agent.compress_history()

    def _cmd_theme(self, args: list[str]) -> str | Table:
        """Lists or switches UI themes."""
        from ...cli import themes

        if not args:
            table = Table(title="Available Themes", box=None)
            table.add_column("Theme", style="bold cyan")
            table.add_column("Status")
            current = self.agent.config.settings.get("theme", "indigo")

            for t_name in themes.THEMES:
                status = "[success]Active[/success]" if t_name == current else ""
                table.add_row(t_name, status)
            return table

        new_theme = args[0].lower()
        if new_theme not in themes.THEMES:
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

    def _cmd_artifacts(self, args: list[str]) -> str | Table | bool:
        """Lists or expands tool artifacts."""
        if not hasattr(self.agent, "active_renderer"):
            return "[error]No renderer active.[/error]"

        renderer = self.agent.active_renderer

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
            return (
                "[warning]Usage: /auth <your_api_key> [provider][/warning]\n"
                "[dim]Example: /auth AIza... google\n"
                "         /auth sk-... openai\n\n"
                "The key will be stored securely in your OS Keyring.[/dim]"
            )

        new_key = args[0].strip()

        # Determine default provider
        provider_class = self.agent.session.provider.__class__.__name__.replace("Provider", "")
        default_provider = "google" if provider_class == "Gemini" else "openai"
        if provider_class == "OpenAI" and ":" in self.agent.model_name:
            default_provider = self.agent.model_name.split(":")[0].lower()

        provider_id = args[1].lower() if len(args) > 1 else default_provider

        success = self.agent.config.save_api_key(new_key, provider=provider_id)

        if success:
            # Force session reload with the new key
            try:
                # Re-setup API client (it will load the newly saved key)
                await self.agent.session.setup_api()

                # Reset the reasoning chat session
                await self.agent.session.reset_session(self.agent._build_config())

                msg = f"[success]{provider_id.upper()} API Key saved and engine reloaded![/success]\n[dim]The new key (***{new_key[-4:]}) is now active in memory.[/dim]"
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

    async def _cmd_init(self) -> str:
        """Initialize local configuration and isolation for the current directory.

        Creates .mentask/ directory with settings, sessions, and identity placeholders.
        """
        import json
        from pathlib import Path

        cwd = Path.cwd()
        local_dir = cwd / ".mentask"
        local_settings = local_dir / "settings.json"
        local_sessions = local_dir / "sessions"
        local_identity = local_dir / "identity.md"

        if local_settings.exists():
            return f"[warning]Local project already initialized:[/warning] [dim]{local_dir}[/dim]"

        try:
            # 1. Create structure
            local_dir.mkdir(parents=True, exist_ok=True)
            local_sessions.mkdir(exist_ok=True)

            # 2. Persist current settings
            settings_data = self.agent.config.settings.copy()
            # Remove keys we don't want to leak into project-level JSON if possible
            # (though keyring handles the sensitive ones usually)
            with open(local_settings, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, indent=4)

            # 3. Create identity placeholder
            if not local_identity.exists():
                local_identity.write_text(
                    f"# mentask Project Identity: {cwd.name}\n\n"
                    "Define project-specific rules, personality, or constraints here.\n",
                    encoding="utf-8",
                )

            # 4. Add directory to trusted list
            await self.agent.orchestrator.trust.add_trust(str(cwd))

            return (
                f"[success]✓ Local project initialized successfully![/success]\n"
                f"  - Folder: [dim]{local_dir}[/dim]\n"
                f"  - Config: [dim]settings.json[/dim]\n"
                f"  - Storage: [dim]sessions/[/dim]\n"
                f"  - Identity: [dim]identity.md[/dim]\n\n"
                f"[info]mentask is now isolated to this project. All sessions and local knowledge will stay here.[/info]"
            )
        except Exception as e:
            return f"[error]Failed to initialize local project: {e}[/error]"

    def _cmd_undo(self, args: list[str]) -> str:
        """Restores the last backed-up version of a file."""
        if not args:
            return "[warning]Usage: /undo <file_path>[/warning]"

        import os
        import shutil
        from pathlib import Path

        from ...core.paths import get_backups_dir

        target_path = args[0]
        try:
            from ...core.security import ensure_safe_path

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
