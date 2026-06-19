from rich.table import Table


def cmd_sessions(agent) -> Table | str:
    """Lists all stored session IDs."""
    sessions = agent.history.list_sessions()
    if not sessions:
        return "[warning]No sessions found.[/warning]"
    table = Table(title="Conversation History", box=None)
    table.add_column("#", style="dim")
    table.add_column("Session ID", style="bold cyan")
    for i, s_id in enumerate(reversed(sessions)):
        prefix = "[success]→[/success] " if s_id == agent.history.current_session_id else "  "
        table.add_row(str(len(sessions) - i), f"{prefix}{s_id}")
    return table


async def cmd_load(agent, args: list[str]) -> str:
    """Loads a session by ID or index."""
    if not args:
        return "[warning]Usage: /load [session_id or index][/warning]"
    sessions = agent.history.list_sessions()
    target_id = args[0]
    if target_id.isdigit():
        idx = int(target_id)
        if 1 <= idx <= len(sessions):
            target_id = sessions[idx - 1]
        else:
            return f"[error]Index {idx} out of range (1-{len(sessions)}).[/error]"
    history = await agent.history.load_session(target_id)
    if history is None:
        return f"[error]Could not load session '{target_id}'.[/error]"
    agent.history.current_session_id = target_id
    await agent.session.reset_session(agent._build_config())
    await agent.session.ensure_session(agent._build_config(), history=history)
    return f"[success]Loaded session:[/success] [bold]{target_id}[/bold] ({len(history)} turns restored)"
