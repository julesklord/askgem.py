"""
Command Line Interface entry point.

It initializes the interactive dashboard and starts the chat agent event loop.
It does NOT contain the model interaction logic or UI configuration.
"""

import argparse
import asyncio
import os
import sys

# The Diamond Gem Mascot (Google Brand Identity colors)
ASCII_MASCOT = (
    r"[google.blue]         .         [/google.blue]" + "\n"
    r"[google.blue]        / \        [/google.blue]" + "\n"
    r"[google.blue]       /   \       [/google.blue]" + "\n"
    r"[google.blue]      <  [google.yellow]·[google.blue]  >      [/google.blue]" + "\n"
    r"[google.blue]       \   /       [/google.blue]" + "\n"
    r"[google.blue]        \ /        [/google.blue]" + "\n"
    r"[google.blue]         '         [/google.blue]"
)


def run_chatbot() -> None:
    """Main entry point for askgem CLI.

    Handles argument parsing for legacy mode and initializes the
    appropriate UI (Classic CLI or TUI Dashboard).
    """
    parser = argparse.ArgumentParser(description="AskGem: Autonomous AI Coding Agent")
    parser.add_argument("--legacy", action="store_true", help="Run the classic scrolling CLI instead of the Dashboard")
    from .. import __version__

    parser.add_argument("--version", action="version", version=f"askgem {__version__}")
    args = parser.parse_args()

    from rich.panel import Panel
    from rich.text import Text

    from .. import __version__
    from ..agent.chat import ChatAgent
    from ..core.i18n import _, get_current_language
    from .console import console

    # Initialize the agent
    agent = ChatAgent()

    if args.legacy:
        # Render stylized Welcome Panel (Classic)
        welcome_text = (
            f"{ASCII_MASCOT}\n\n"
            f"[google.yellow][bold]{_('startup.welcome', version=__version__)}[/bold][/google.yellow]\n\n"
            f"[italic]{_('startup.init')}[/italic]\n\n"
            f"[google.blue]Modelo:[/google.blue] {agent.model_name} | [google.blue]Modo:[/google.blue] {agent.edit_mode}\n"
            f"[google.blue]Idioma:[/google.blue] {get_current_language()}\n\n"
            f"— [dim]{_('cmd.hint_help')}[/dim]"
        )

        console.print()
        console.print(
            Panel(
                Text.from_markup(welcome_text, justify="center"),
                border_style="google.blue",
                padding=(1, 2),
                title="[google.yellow] AskGem Identity [/google.yellow]",
                subtitle="[dim] Powered by Google Gemini [/dim]",
            )
        )
        console.print()

        # Launch Classic CLI in async loop
        asyncio.run(agent.start())
    else:
        # Placeholder for Dashboard (Milestone 4.1.3)
        # For now, if dashboard.py doesn't exist, we fallback or just error
        try:
            from .dashboard import AskGemDashboard

            app = AskGemDashboard(agent=agent)
            app.run()
        except ImportError:
            console.print("[warning]Dashboard not implemented yet. Falling back to --legacy...[/warning]")
            asyncio.run(agent.start())


if __name__ == "__main__":
    # Adjust python path for direct file execution execution
    if __package__ is None:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run_chatbot()
