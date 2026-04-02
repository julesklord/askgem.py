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
    welcome_text = (
        f"**{_('startup.welcome', version=__version__)}**\n\n"
        f"_{_('startup.init')}_\n\n"
        f"*{_('startup.dashboard', model=agent.model_name, mode=agent.edit_mode, lang=get_current_language())}*\n\n"
        f"{_('cmd.hint_help')}"
    )

    console.print()
    console.print(Panel(
        Align.center(Markdown(welcome_text)),
        border_style="bold cyan",
        padding=(1, 2)
    ))
    console.print()

    # Launch CLI
    agent.start()


if __name__ == "__main__":
    # Adjust python path for direct file execution execution
    if __package__ is None:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run_chatbot()
