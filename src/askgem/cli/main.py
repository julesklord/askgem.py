"""
Command Line Interface entry point.

It initializes the interactive dashboard and starts the chat agent event loop.
It does NOT contain the model interaction logic or UI configuration.
"""

import os
import sys


def run_chatbot() -> None:
    """Main entry point for askgem v2.0 CLI.

    Bootstraps the CLI UI, loads configuration via the ChatAgent,
    and hands over execution to the interactive agent loop.
    """
    from rich.align import Align
    from rich.markdown import Markdown
    from rich.panel import Panel

    from .. import __version__
    from ..agent.chat import ChatAgent
    from ..core.i18n import _, get_current_language
    from .console import console

    # Initialize the agent to load settings
    agent = ChatAgent()

    # Render stylized Welcome Panel
    welcome_ascii = (
        "[google.blue]       .       [/google.blue]\n"
        "[google.blue]      / \\      [/google.blue]\n"
        "[google.blue]     /   \\     [/google.blue]\n"
        "[google.blue]    /  [google.yellow]^[google.blue]  \\    [/google.blue]\n"
        "[google.blue]   /  [google.yellow]( )[google.blue]  \\   [/google.blue]\n"
        "[google.blue]  /   [google.yellow]---[google.blue]   \\  [/google.blue]\n"
        "[google.blue] /___________\\ [/google.blue]\n"
    )

    welcome_text = (
        f"{welcome_ascii}\n"
        f"**[google.yellow]{_('startup.welcome', version=__version__)}[/google.yellow]**\n\n"
        f"_{_('startup.init')}_\n\n"
        f"*{_('startup.dashboard', model=agent.model_name, mode=agent.edit_mode, lang=get_current_language())}*\n\n"
        f"{_('cmd.hint_help')}"
    )

    console.print()
    console.print(Panel(
        Align.center(Markdown(welcome_text)),
        border_style="google.blue",
        padding=(1, 2),
        title="[google.yellow]AskGem Identity[/google.yellow]",
        subtitle="[dim]Powered by Google Gemini[/dim]"
    ))
    console.print()

    # Launch CLI
    agent.start()


if __name__ == "__main__":
    # Adjust python path for direct file execution execution
    if __package__ is None:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run_chatbot()
