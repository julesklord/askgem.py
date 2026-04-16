"""
Command Line Interface entry point.

Single entry point: the Rich streaming renderer (cli/renderer.py).
The Textual TUI has been removed — see cli/dashboard.py for the deprecation notice.
"""

import asyncio
import os
import sys


def _parse_args():
    import argparse

    from .. import __version__

    parser = argparse.ArgumentParser(
        prog="askgem",
        description="AskGem: Autonomous AI Coding Agent",
    )
    parser.add_argument("--version", action="version", version=f"askgem {__version__}")
    parser.add_argument(
        "--list",
        choices=["db", "home", "sessions", "changelog", "spend", "all"],
        help="Display agent internal information and stats."
    )
    return parser.parse_args()


def run_chatbot() -> None:
    """Main entry point for the askgem CLI."""
    args = _parse_args()

    # Si se pide listado, no arrancamos el chatbot
    if args.list:
        from ..cli.console import console
        from ..core.audit_manager import AuditManager

        audit = AuditManager()
        console.print()

        if args.list in ("db", "all"):
            console.print(audit.list_db())
        if args.list in ("home", "all"):
            console.print(audit.list_home())
        if args.list in ("sessions", "all"):
            console.print(audit.list_sessions())
        if args.list in ("spend", "all"):
            console.print(audit.list_spend())
        if args.list in ("changelog", "all"):
            console.print(audit.list_changelog())

        console.print()
        return

    from ..agent.chat import ChatAgent

    agent = ChatAgent()
    asyncio.run(agent.start())


if __name__ == "__main__":
    if __package__ is None:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run_chatbot()
