import asyncio
import json
from pathlib import Path

import aiofiles
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from ....cli import themes
from ....core.i18n import _
from ....core.models_hub import hub
from ....core.paths import get_global_config_dir


async def cmd_model(agent, args: list[str]) -> str | Table:
    """Lists or switches models for the active provider."""
    if args and args[0] == "configure":
        return await cmd_model_configure(agent)

    if not args:
        try:
            # Force a sync check
            hub.sync()

            models = await agent.session.provider.list_models()
            if not models:
                return "[warning]No models found for the current provider.[/warning]"

            table = Table(title=_("cmd.model.available"), box=None)
            table.add_column("Model ID", style="bold cyan")
            table.add_column("Context", justify="right")
            table.add_column("Status")

            health_data = getattr(agent, "model_health", {})

            for m_id in models:
                health = health_data.get(m_id, (True, None))
                is_ok, error = health

                model_style = "bold #6366f1" if is_ok else "dim"
                if m_id == agent.model_name:
                    model_style = "bold yellow underline"

                display_name = m_id
                if not is_ok:
                    display_name = f"{m_id} [red]({error})[/]"

                status = ""
                if m_id == agent.model_name:
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
    agent.model_name = new_model
    await agent.session.switch_model(new_model)
    agent.config.settings["model_name"] = new_model

    # Check if it's a CLI model and prompt for configuration
    is_cli_model = new_model.startswith("cli:") or new_model in ["gemini-cli", "codex", "opencode"]
    config_key = f"configured_{new_model.replace(':', '_')}"

    if is_cli_model and not agent.config.settings.get(config_key, False):
        if hasattr(agent, "active_renderer"):
            wants_config = await agent.active_renderer.confirm_action(
                f"¿Desea configurar su entorno para que {new_model} funcione apropiadamente?",
                detail="Se insertará una instrucción en su configuración global para que funcione correctamente con Mentask.",
            )
            if wants_config:
                await configure_cli_agent(agent, new_model)
        agent.config.settings[config_key] = True

    agent.config.save_settings()
    await agent.session.reset_session(agent._build_config())
    return f"[success]{_('cmd.model.switched')}[/success] [bold]{new_model}[/bold]"


async def configure_cli_agent(agent, model_name: str) -> None:
    """Generates the master instruction file for external CLI agents and updates their config."""
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


async def cmd_model_configure(agent) -> str:
    """Performs a health check on all available models."""
    models = await agent.session.provider.list_models()
    if not models:
        return "[error]No models available to configure.[/error]"

    results: dict[str, tuple[bool, str]] = {}
    agent.model_health = results  # Store in agent

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=agent.active_renderer.console if hasattr(agent, "active_renderer") else None,
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]Verifying models...", total=len(models))

        # Run checks in batches to avoid overwhelming the API
        batch_size = 5
        for i in range(0, len(models), batch_size):
            batch = models[i : i + batch_size]
            coros = [agent.session.provider.check_health(m) for m in batch]
            batch_results = await asyncio.gather(*coros, return_exceptions=True)

            for m_id, res in zip(batch, batch_results, strict=False):
                if isinstance(res, tuple):
                    results[m_id] = res
                else:
                    results[m_id] = (False, "ERR")
                progress.update(task, advance=1, description=f"[cyan]Checked {m_id}")

    # Refresh autocompletion after health check
    if hasattr(agent, "_update_completer"):
        await agent._update_completer()

    return f"[success]Verification complete.[/success] [bold]{sum(1 for r in results.values() if r[0])}[/bold] models are available."


async def cmd_discover(agent, args: list[str]) -> Table | str:
    """Searches and displays models from models.dev Hub."""
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


def cmd_mode(agent, args: list[str]) -> str:
    """Toggles edit mode."""
    if not args or args[0].lower() not in ("auto", "manual"):
        return f"[warning]{_('cmd.mode.current')}[/warning] [bold]{agent.edit_mode}[/bold]"
    mode = args[0].lower()
    agent.edit_mode = mode
    agent.config.settings["edit_mode"] = mode
    agent.config.save_settings()
    return f"[success]{_('cmd.mode.set')}[/success] [bold]{mode}[/bold]"


def cmd_stream(agent, args: list[str]) -> str:
    """Changes streaming display mode."""
    if not args or args[0].lower() not in ("continuous", "transient"):
        current = agent.config.settings.get("stream_mode", "continuous")
        return f"[warning]Current stream mode:[/warning] [bold]{current}[/bold]\n[dim]Use: /stream continuous (full history) or /stream transient (live updates)[/dim]"

    mode = args[0].lower()
    agent.config.settings["stream_mode"] = mode
    agent.config.save_settings()

    if hasattr(agent, "active_renderer"):
        agent.active_renderer.stream_mode = mode

    return f"[success]Stream mode changed to:[/success] [bold]{mode}[/bold]\n[dim]{'Full history visible via scroll' if mode == 'continuous' else 'Live updates with final render'}[/dim]"


def cmd_speed(agent, args: list[str]) -> str:
    """Adjusts stream delay for output pacing. Hidden command (not in /help)."""
    if not args:
        current = agent.config.settings.get("stream_delay", 0.015)
        return f"[warning]Current stream speed:[/warning] [bold]{current}s[/bold] ({int(current * 1000)}ms)\n[dim]Usage: /speed 0.005 to 0.1 (lower=faster, higher=slower)[/dim]"

    try:
        delay = float(args[0])
        if delay < 0.001 or delay > 0.5:
            return "[error]Speed must be between 0.001 and 0.5 seconds[/error]"
        agent.config.settings["stream_delay"] = delay
        agent.config.save_settings()
        if hasattr(agent, "active_renderer"):
            agent.active_renderer._stream_delay = delay
        return f"[success]Stream speed updated:[/success] [bold]{delay}s[/bold] ({int(delay * 1000)}ms)\n[dim]This affects how quickly content appears[/dim]"
    except ValueError:
        return "[error]Invalid speed value. Use a number like 0.01 or 0.05[/error]"


def cmd_prompt(agent, args: list[str]) -> str:
    """Handles prompt customization."""
    if not hasattr(agent, "active_renderer"):
        return "[error]No active renderer to configure prompt.[/error]"

    engine = agent.active_renderer.prompt_engine
    available_styles = list(engine.STYLES.keys())

    if not args:
        style = agent.config.settings.get("prompt_style", "atomic")
        nf = agent.config.settings.get("nerdfonts_enabled", True)
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
            agent.config.settings["prompt_style"] = theme
            agent.config.save_settings()
            if hasattr(agent, "active_renderer"):
                agent.active_renderer.prompt_style = theme
            return f"[success]Prompt style changed to [bold]{theme}[/bold][/success]"

    if "--nerdfonts" in args:
        idx = args.index("--nerdfonts")
        if idx + 1 < len(args):
            val = args[idx + 1].lower() in ("on", "true", "yes", "1")
            agent.config.settings["nerdfonts_enabled"] = val
            agent.config.save_settings()
            if hasattr(agent, "active_renderer"):
                agent.active_renderer.prompt_engine.use_nerdfonts = val
            return f"[success]Nerdfonts {'enabled' if val else 'disabled'}.[/success]"

    return "[error]Invalid /prompt arguments.[/error]"


def cmd_theme(agent, args: list[str]) -> str | Table:
    """Lists or switches UI themes."""
    if not args:
        table = Table(title="Available Themes", box=None)
        table.add_column("Theme", style="bold cyan")
        table.add_column("Status")
        current = agent.config.settings.get("theme", "indigo")
        for t_name in themes.THEMES:
            status = "[success]Active[/success]" if t_name == current else ""
            table.add_row(t_name, status)
        return table

    new_theme = args[0].lower()
    if new_theme not in themes.THEMES:
        return f"[error]Theme '{new_theme}' not found.[/error]"
    agent.config.settings["theme"] = new_theme
    agent.config.save_settings()
    if hasattr(agent, "active_renderer"):
        agent.active_renderer.apply_theme(new_theme)
    return f"[success]Theme switched to:[/success] [bold]{new_theme}[/bold]"


def cmd_thinking(agent, args: list[str]) -> str:
    """Toggles visibility of agent's thought process."""
    if not args:
        current = agent.config.settings.get("show_thinking", True)
        state = "ON" if current else "OFF"
        return f"[info]Thinking visibility is currently [bold]{state}[/bold][/info]\n[dim]Usage: /thinking true | /thinking false[/dim]"

    val_str = args[0].lower()
    if val_str in ("true", "on", "yes", "1"):
        show = True
    elif val_str in ("false", "off", "no", "0"):
        show = False
    else:
        return "[error]Invalid argument. Use 'true' or 'false'.[/error]"

    agent.config.settings["show_thinking"] = show
    agent.config.save_settings()

    if hasattr(agent, "active_renderer"):
        agent.active_renderer.show_thinking_details = show

    state = "ON" if show else "OFF"
    return f"[success]Thinking visibility turned [bold]{state}[/bold][/success]"


def cmd_multiline(agent, args: list[str]) -> str:
    """Toggles multiline input mode for the prompt."""
    if not args:
        current = agent.config.settings.get("multiline_prompt", False)
        state = "ON" if current else "OFF"
        return f"[info]Multiline prompt is currently [bold]{state}[/bold][/info]\n[dim]Usage: /multiline true | /multiline false[/dim]"

    val_str = args[0].lower()
    if val_str in ("true", "on", "yes", "1"):
        is_multiline = True
    elif val_str in ("false", "off", "no", "0"):
        is_multiline = False
    else:
        return "[error]Invalid argument. Use 'true' or 'false'.[/error]"

    agent.config.settings["multiline_prompt"] = is_multiline
    agent.config.save_settings()

    if hasattr(agent, "_update_completer"):
        asyncio.create_task(agent._update_completer())

    state = "ON" if is_multiline else "OFF"
    extra = "\n[dim](Press Esc+Enter or Alt+Enter to submit)[/dim]" if is_multiline else ""
    return f"[success]Multiline prompt turned [bold]{state}[/bold][/success]{extra}"


async def cmd_init(agent) -> str:
    """Initialize local configuration and isolation for the current directory."""
    cwd = Path.cwd()
    local_dir = cwd / ".mentask"
    local_settings = local_dir / "settings.json"
    local_identity = local_dir / "identity.md"
    if local_settings.exists():
        return f"[warning]Local project already initialized:[/warning] [dim]{local_dir}[/dim]"
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
        settings_data = agent.config.settings.copy()

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
        await agent.orchestrator.trust.add_trust(str(cwd))
        return (
            f"[success]✓ Local project initialized successfully![/success]\n"
            f"  - Folder: [dim]{local_dir}[/dim]\n"
            f"  - Config: [dim]settings.json[/dim]\n"
            f"  - Identity: [dim]identity.md[/dim]\n\n"
            f"[info]mentask is now isolated to this project. All sessions and local knowledge will stay here.[/info]"
        )
    except Exception as e:
        return f"[error]Failed to initialize local project: {e}[/error]"
