"""
Slash command handling module for mentask.

Parses and dispatches mid-conversation commands like /help, /model, /mode, etc.
"""

import difflib
import logging
from typing import Any

from rich.console import Group
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

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
    "/sessions": {"desc": "List previous chat sessions", "category": "History"},
    "/load": {"desc": "Load a specific session by ID or index", "example": "/load <id>", "category": "History"},
    # --- Configuration & Discovery ---
    "/model": {
        "desc": "List models or switch (use '/model configure' to test health)",
        "example": "/model [name]",
        "category": "Config",
    },
    "/discover": {"desc": "Search models.dev catalog", "example": "/discover [query]", "category": "Config"},
    "/mode": {
        "desc": "Toggle between auto/manual tool execution",
        "example": "/mode auto/manual",
        "category": "Config",
    },
    "/stream": {
        "desc": "Change streaming mode (continuous/transient)",
        "example": "/stream [mode]",
        "category": "Config",
    },
    "/theme": {"desc": "List or change UI themes", "example": "/theme [name]", "category": "Config"},
    "/thinking": {
        "desc": "Toggle visibility of agent's thought process",
        "example": "/thinking [true|false]",
        "category": "Config",
    },
    "/multiline": {"desc": "Toggle multiline prompt mode", "example": "/multiline [true|false]", "category": "Config"},
    "/init": {"desc": "Initialize local project configuration directory", "example": "/init", "category": "Config"},
    "/prompt": {"desc": "Customize prompt style and icons", "example": "/prompt --theme atomic", "category": "Config"},
    # --- Security ---
    "/auth": {"desc": "Sets API Key for a provider", "example": "/auth <key> [provider]", "category": "Security"},
    "/trust": {"desc": "Trust current directory for auto-execution", "example": "/trust", "category": "Security"},
    "/untrust": {"desc": "Remove trust from current directory", "example": "/untrust", "category": "Security"},
    "/readonly": {
        "desc": "Restrict agent to read-only operations on existing files",
        "example": "/readonly [true|false]",
        "category": "Security",
    },
    # --- Stats & Tools ---
    "/usage": {"desc": "Show historical token usage", "example": "/usage [--reset]", "category": "Stats"},
    "/stats": {"desc": "Show current session statistics", "example": "/stats", "category": "Stats"},
    "/artifacts": {"desc": "List or expand tool outputs", "example": "/artifacts [idx]", "category": "Tools"},
    # --- Control ---
    "/stop": {"desc": "Interrupts the current generation", "example": "/stop", "category": "Control"},
    "/exit": {"desc": _("cmd.desc.exit"), "example": "/exit", "category": "Control"},
}

# Mapping of aliases to primary commands
COMMAND_ALIASES = {
    "/q": "/exit",
    "/quit": "/exit",
    "/themes": "/theme",
    "/art": "/artifacts",
    "/cost": "/stats",
    "/speed": "/speed",
}


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

        if command == "/":
            return self._cmd_help()

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
            self.agent.history.reset()
            self.agent.is_new_session = True
            self.agent.session_messages = 0
            await self.agent.session.reset_session(self.agent._build_config())
            return f"[success]{_('cmd.clear.success')}[/success]"
        elif command == "/usage":
            return self._cmd_usage(args)
        elif command == "/stats":
            return self._cmd_stats()
        elif command == "/theme":
            return self._cmd_theme(args)
        elif command == "/thinking":
            return self._cmd_thinking(args)
        elif command == "/multiline":
            return self._cmd_multiline(args)
        elif command == "/artifacts":
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
        elif command == "/readonly":
            return self._cmd_readonly(args)
        elif command == "/undo":
            return self._cmd_undo(args)
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
            return await self._cmd_discover(args)
        elif command == "/prompt":
            return self._cmd_prompt(args)
        elif command == "/init":
            return await self._cmd_init()

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

            example = meta.get("example", cmd)
            table.add_row(f"  {cmd}", meta["desc"], example)

        # Add global shortcuts
        table.add_section()
        table.add_row("[bold magenta]Global Shortcuts[/]", "", "")
        table.add_row("  [bold]Ctrl+C[/]", "Interrupt generation or exit", "N/A")

        return table

    async def _cmd_model(self, args: list[str]) -> str | Table:
        """Lists or switches models for the active provider."""
        from ...core.models_hub import hub

        if args and args[0] == "configure":
            return await self._cmd_model_configure()

        if not args:
            try:
                # Force a sync check
                hub.sync()

                models = await self.agent.session.provider.list_models()
                if not models:
                    return "[warning]No models found for the current provider.[/warning]"

                table = Table(title=_("cmd.model.available"), box=None)
                table.add_column("Model ID", style="bold cyan")
                table.add_column("Context", justify="right")
                table.add_column("Status")

                health_data = getattr(self.agent, "model_health", {})

                for m_id in models:
                    health = health_data.get(m_id, (True, None))
                    is_ok, error = health

                    model_style = "bold #6366f1" if is_ok else "dim"
                    if m_id == self.agent.model_name:
                        model_style = "bold yellow underline"

                    display_name = m_id
                    if not is_ok:
                        display_name = f"{m_id} [red]({error})[/]"

                    status = ""
                    if m_id == self.agent.model_name:
                        status = "[success]● Active[/success]"
                    elif not is_ok:
                        status = "[red]✗ Offline[/red]"

                    # Try to get extra info from hub
                    m_info = hub.get_model(m_id)
                    context_str = ""
                    if m_info:
                        ctx = m_info.get("limit", {}).get("context", 0)
                        if ctx:
                            context_str = f"{ctx // 1000}K"

                    table.add_row(Text.from_markup(f"[{model_style}]{display_name}[/]"), context_str, status)

                table.caption = "[dim]Run [white]/model configure[/white] to verify reachability of all models.[/dim]"
                return table
            except Exception as e:
                return f"[dim]Error listing models: {e}[/dim]"

        new_model = args[0]
        self.agent.model_name = new_model
        await self.agent.session.switch_model(new_model)
        self.agent.config.settings["model_name"] = new_model

        # Check if it's a CLI model and prompt for configuration
        is_cli_model = new_model.startswith("cli:") or new_model in ["gemini-cli", "codex", "opencode"]
        config_key = f"configured_{new_model.replace(':', '_')}"

        if is_cli_model and not self.agent.config.settings.get(config_key, False):
            if hasattr(self.agent, "active_renderer"):
                wants_config = await self.agent.active_renderer.confirm_action(
                    f"¿Desea configurar su entorno para que {new_model} funcione apropiadamente?",
                    detail="Se insertará una instrucción en su configuración global para que funcione correctamente con Mentask.",
                )
                if wants_config:
                    await self._configure_cli_agent(new_model)
            self.agent.config.settings[config_key] = True

        self.agent.config.save_settings()
        await self.agent.session.reset_session(self.agent._build_config())
        return f"[success]{_('cmd.model.switched')}[/success] [bold]{new_model}[/bold]"

    async def _configure_cli_agent(self, model_name: str) -> None:
        """Generates the master instruction file for external CLI agents and updates their config."""
        from pathlib import Path

        import aiofiles

        from ...core.paths import get_global_config_dir

        alias = model_name.removeprefix("cli:")
        sys_dir = get_global_config_dir()

        # MENTASK.md content (optimized for tokens)
        mentask_md_content = """# MENTASK CORE PROTOCOL (Master Instructions)

You are acting as the "Brain" for Mentask. When you see `### MENTASK CORE PROTOCOL` in your prompt:
1. **DO NOT USE NATIVE TOOLS:** Do not use your internal or native tools (like `run_shell_command`, `analyze_codebase`, etc.).
2. **USE MENTASK'S JSON PROTOCOL:** You MUST output exactly this JSON block to delegate actions back to Mentask:
```json
{
  "mentask_tool_call": {
    "name": "<tool_name_from_mentask_schema>",
    "arguments": {"arg1": "value"}
  }
}
```
3. **MENTASK TOOLS:**
   - `execute_bash`: Runs system/shell commands (replaces your native shell tool).
   - `edit_file`: Find & replace. Prefer over writing full files.
   - `read_file`, `list_directory`, `grep_search`, `glob_find`.
4. **WINDOWS NODE-PTY:** Ignore `Error: AttachConsole failed` tracebacks if the stdout is successful.
"""

        if "gemini" in alias:
            # Setup for Gemini CLI
            mentask_md_path = sys_dir / "MENTASK_GEMINI.md"
            agent_config_path = Path.home() / ".gemini" / ".gemini" / "GEMINI.md"
            include_ref = f"\n\n# --- MENTASK INTEGRATION ---\n# CRITICAL: ONLY read and apply the instructions in the following file IF AND ONLY IF your current prompt contains the header `### MENTASK CORE PROTOCOL`.\n# If that header is missing, ignore this integration completely and act as a standard assistant.\n# {mentask_md_path}\n"
        else:
            # Generic/Other CLI
            mentask_md_path = sys_dir / f"MENTASK_{alias.upper()}.md"
            agent_config_path = None  # We don't know where other agents store their global config yet
            include_ref = ""

        # Write the master MENTASK.md file
        async with aiofiles.open(mentask_md_path, mode="w", encoding="utf-8") as f:
            await f.write(mentask_md_content)

        # Update the agent's global configuration file if known
        if agent_config_path:
            agent_config_path.parent.mkdir(parents=True, exist_ok=True)

            content = ""
            if agent_config_path.exists():
                async with aiofiles.open(agent_config_path, encoding="utf-8") as f:
                    content = await f.read()

            if "# --- MENTASK INTEGRATION ---" not in content:
                async with aiofiles.open(agent_config_path, mode="a", encoding="utf-8") as f:
                    await f.write(include_ref)

    async def _cmd_model_configure(self) -> str:
        """Performs a health check on all available models."""
        import asyncio

        from rich.progress import Progress, SpinnerColumn, TextColumn

        models = await self.agent.session.provider.list_models()
        if not models:
            return "[error]No models available to configure.[/error]"

        results = {}
        self.agent.model_health = results  # Store in agent

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.agent.active_renderer.console if hasattr(self.agent, "active_renderer") else None,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Verifying models...", total=len(models))

            # Run checks in batches to avoid overwhelming the API
            batch_size = 5
            for i in range(0, len(models), batch_size):
                batch = models[i : i + batch_size]
                coros = [self.agent.session.provider.check_health(m) for m in batch]
                batch_results = await asyncio.gather(*coros, return_exceptions=True)

                for m_id, res in zip(batch, batch_results, strict=False):
                    if isinstance(res, tuple):
                        results[m_id] = res
                    else:
                        results[m_id] = (False, "ERR")
                    progress.update(task, advance=1, description=f"[cyan]Checked {m_id}")

        # Refresh autocompletion after health check
        if hasattr(self.agent, "_update_completer"):
            await self.agent._update_completer()

        return f"[success]Verification complete.[/success] [bold]{sum(1 for r in results.values() if r[0])}[/bold] models are available."

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

        results.sort(key=lambda x: x.get("cost", {}).get("input", 0))

        for m in results[:20]:
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
        from ...core.compression import ContextSnapper

        table = Table(box=None, show_header=False, padding=(0, 1))
        table.add_column("Key", style="bold #6366f1")
        table.add_column("Value")

        cost = self.agent.metrics.calculate_cost(
            self.agent.metrics.total_prompt_tokens, self.agent.metrics.total_candidate_tokens
        )

        table.add_row("🤖 Model", f"[bold yellow]{self.agent.model_name}[/bold yellow]")
        table.add_row("💬 Messages", _("cmd.stats.messages", count=self.agent.session_messages))
        table.add_row("🛠️ Tools", _("cmd.stats.tools", count=self.agent.session_tools))
        table.add_row("📝 Files", _("cmd.stats.files", count=self.agent.session_files))

        if self.agent.session.recent_files:
            recent = ", ".join([f"[cyan]{f}[/]" for f in self.agent.session.recent_files])
            table.add_row("📂 Recent", recent)

        table.add_section()

        # Token & Context Usage
        snapper = ContextSnapper(self.agent.model_name)
        total_tokens = self.agent.metrics.total_prompt_tokens + self.agent.metrics.total_candidate_tokens
        status = snapper.get_token_status(total_tokens)

        progress = ProgressBar(total=100, completed=status["percentage"], width=30, pulse=False)
        usage_color = "red" if status["is_dangerous"] else "yellow" if status["percentage"] > 50 else "green"

        table.add_row(
            "🪙 Tokens",
            f"[cyan]{total_tokens:,}[/] [dim](In: {self.agent.metrics.total_prompt_tokens:,} | Out: {self.agent.metrics.total_candidate_tokens:,})[/dim]",
        )
        table.add_row(
            "🧠 Context",
            Group(
                Text.from_markup(f"[{usage_color}]{status['percentage']}%[/] [dim]of {status['limit'] // 1000}K[/dim]"),
                progress,
            ),
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
        self.agent.config.settings["theme"] = new_theme
        self.agent.config.save_settings()
        if hasattr(self.agent, "active_renderer"):
            self.agent.active_renderer.apply_theme(new_theme)
        return f"[success]Theme switched to:[/success] [bold]{new_theme}[/bold]"

    def _cmd_thinking(self, args: list[str]) -> str:
        """Toggles visibility of agent's thought process."""
        if not args:
            current = self.agent.config.settings.get("show_thinking", True)
            state = "ON" if current else "OFF"
            return f"[info]Thinking visibility is currently [bold]{state}[/bold][/info]\n[dim]Usage: /thinking true | /thinking false[/dim]"

        val_str = args[0].lower()
        if val_str in ("true", "on", "yes", "1"):
            show = True
        elif val_str in ("false", "off", "no", "0"):
            show = False
        else:
            return "[error]Invalid argument. Use 'true' or 'false'.[/error]"

        self.agent.config.settings["show_thinking"] = show
        self.agent.config.save_settings()

        if hasattr(self.agent, "active_renderer"):
            self.agent.active_renderer.show_thinking_details = show

        state = "ON" if show else "OFF"
        return f"[success]Thinking visibility turned [bold]{state}[/bold][/success]"

    def _cmd_multiline(self, args: list[str]) -> str:
        """Toggles multiline input mode for the prompt."""
        if not args:
            current = self.agent.config.settings.get("multiline_prompt", False)
            state = "ON" if current else "OFF"
            return f"[info]Multiline prompt is currently [bold]{state}[/bold][/info]\n[dim]Usage: /multiline true | /multiline false[/dim]"

        val_str = args[0].lower()
        if val_str in ("true", "on", "yes", "1"):
            is_multiline = True
        elif val_str in ("false", "off", "no", "0"):
            is_multiline = False
        else:
            return "[error]Invalid argument. Use 'true' or 'false'.[/error]"

        self.agent.config.settings["multiline_prompt"] = is_multiline
        self.agent.config.save_settings()

        if hasattr(self.agent, "_update_completer"):
            import asyncio

            asyncio.create_task(self.agent._update_completer())

        state = "ON" if is_multiline else "OFF"
        extra = "\n[dim](Press Esc+Enter or Alt+Enter to submit)[/dim]" if is_multiline else ""
        return f"[success]Multiline prompt turned [bold]{state}[/bold][/success]{extra}"

    def _cmd_readonly(self, args: list[str]) -> str:
        """Toggles read-only mode for the agent."""
        if not args:
            current = self.agent.config.settings.get("readonly_mode", False)
            state = "ON" if current else "OFF"
            return f"[info]Read-only mode is currently [bold]{state}[/bold][/info]\n[dim]Usage: /readonly true | /readonly false[/dim]"

        val_str = args[0].lower()
        if val_str in ("true", "on", "yes", "1"):
            is_readonly = True
        elif val_str in ("false", "off", "no", "0"):
            is_readonly = False
        else:
            return "[error]Invalid argument. Use 'true' or 'false'.[/error]"

        self.agent.config.settings["readonly_mode"] = is_readonly
        self.agent.config.save_settings()
        self.agent._setup_system_prompt()  # Refresh prompt to include/exclude RO instructions

        state = "ON" if is_readonly else "OFF"
        return f"[success]Read-only mode turned [bold]{state}[/bold][/success]"

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

    def _cmd_sessions(self) -> Table | str:
        """Lists all stored session IDs."""
        sessions = self.agent.history.list_sessions()
        if not sessions:
            return "[warning]No sessions found.[/warning]"
        table = Table(title="Conversation History", box=None)
        table.add_column("#", style="dim")
        table.add_column("Session ID", style="bold cyan")
        for i, s_id in enumerate(reversed(sessions)):
            prefix = "[success]→[/success] " if s_id == self.agent.history.current_session_id else "  "
            table.add_row(str(len(sessions) - i), f"{prefix}{s_id}")
        return table

    async def _cmd_load(self, args: list[str]) -> str:
        """Loads a session by ID or index."""
        if not args:
            return "[warning]Usage: /load [session_id or index][/warning]"
        sessions = self.agent.history.list_sessions()
        target_id = args[0]
        if target_id.isdigit():
            idx = int(target_id)
            if 1 <= idx <= len(sessions):
                target_id = sessions[idx - 1]
            else:
                return f"[error]Index {idx} out of range (1-{len(sessions)}).[/error]"
        history = self.agent.history.load_session(target_id)
        if history is None:
            return f"[error]Could not load session '{target_id}'.[/error]"
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
        provider_id = args[1].lower() if len(args) > 1 else self.agent.config.detect_provider(new_key)
        success = self.agent.config.save_api_key(new_key, provider=provider_id)
        if success:
            try:
                provider_obj = self.agent.session.provider
                from .providers.gemini import GeminiProvider

                current_is_google = isinstance(provider_obj, GeminiProvider)
                target_is_google = provider_id == "google"
                if current_is_google != target_is_google:
                    new_model = "gemini-2.0-flash" if target_is_google else "gpt-4o-mini"
                    await self.agent.session.switch_model(new_model)
                    self.agent.model_name = new_model
                    self.agent.config.settings["model_name"] = new_model
                    self.agent.config.save_settings()
                    msg = f"[success]Provider switched to {provider_id.upper()}![/success]\n"
                    msg += f"[info]New default model active:[/info] [bold]{new_model}[/bold]\n"
                else:
                    await self.agent.session.setup_api()
                    msg = f"[success]{provider_id.upper()} API Key updated and active![/success]\n"
                await self.agent.session.reset_session(self.agent._build_config())
                msg += f"[dim]The new key (***{new_key[-4:]}) is now active. Environment variables are now overridden.[/dim]"
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
        """Initialize local configuration and isolation for the current directory."""
        import json
        from pathlib import Path

        cwd = Path.cwd()
        local_dir = cwd / ".mentask"
        local_settings = local_dir / "settings.json"
        local_identity = local_dir / "identity.md"
        if local_settings.exists():
            return f"[warning]Local project already initialized:[/warning] [dim]{local_dir}[/dim]"
        try:
            local_dir.mkdir(parents=True, exist_ok=True)
            settings_data = self.agent.config.settings.copy()
            import asyncio

            def _write_files():
                from mentask.core.paths import ensure_dir

                ensure_dir(local_dir)
                with open(local_settings, "w", encoding="utf-8") as f:
                    json.dump(settings_data, f, indent=4)
                if not local_identity.exists():
                    local_identity.write_text(
                        f"# mentask Project Identity: {cwd.name}\n\n"
                        "Define project-specific rules, personality, or constraints here.\n",
                        encoding="utf-8",
                    )

            await asyncio.to_thread(_write_files)
            await self.agent.orchestrator.trust.add_trust(str(cwd))
            return (
                f"[success]✓ Local project initialized successfully![/success]\n"
                f"  - Folder: [dim]{local_dir}[/dim]\n"
                f"  - Config: [dim]settings.json[/dim]\n"
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
