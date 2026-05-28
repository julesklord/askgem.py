"""
Command Line Interface entry point.

Single entry point: the Rich streaming renderer (cli/gem_renderer.py).
The Textual TUI has been removed — see cli/dashboard.py for the deprecation notice.
"""

import asyncio
import logging
import os
import signal
import sys


class GracefulShutdown:
    def __init__(self, agent):
        self.agent = agent
        self.interrupted = False
        signal.signal(signal.SIGINT, self._handle_interrupt)

        if sys.platform != "win32":
            signal.signal(signal.SIGTSTP, self._handle_suspend)

    def _handle_interrupt(self, signum, frame):
        logger = logging.getLogger("mentask")
        logger.warning("\nSIGINT received - stopping gracefully...")
        self.interrupted = True

        if (
            hasattr(self.agent, "orchestrator")
            and hasattr(self.agent.orchestrator, "executor")
            and hasattr(self.agent.orchestrator.executor, "operation_mgr")
        ):
            ops = self.agent.orchestrator.executor.operation_mgr.active_operations
            for op_id in list(ops.keys()):
                logger.info(f"Canceling operation: {op_id}")

        if hasattr(self.agent, "save_checkpoint"):
            self.agent.save_checkpoint()

        sys.exit(130)

    def _handle_suspend(self, signum, frame):
        logger = logging.getLogger("mentask")
        logger.info("\nSIGTSTP received - suspending agent...")
        if hasattr(self.agent, "pause"):
            self.agent.pause()
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGTSTP)


def _parse_args():
    import argparse

    from .. import __version__

    parser = argparse.ArgumentParser(
        prog="mentask",
        description="mentask (MentAsk): Universal AI Coding Agent",
    )
    parser.add_argument("--version", action="version", version=f"mentask {__version__}")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run in local-only mode (optimizes for Ollama, disables cloud APIs).",
    )
    parser.add_argument(
        "--list",
        choices=["db", "home", "sessions", "changelog", "spend", "all"],
        help="Display agent internal information and stats.",
    )
    parser.add_argument(
        "session_id",
        nargs="?",
        default=None,
        help="Resume a previous session using its ID (e.g., mentask 2025-01-15_10-30-45_abc123). Omit to start a new session.",
    )
    return parser.parse_args()


async def _run_async_chatbot(args):
    """Encapsulated async run for better cleanup."""
    from ..agent.chat import ChatAgent

    agent = ChatAgent(session_id=args.session_id, local_mode=args.local)
    _shutdown = GracefulShutdown(agent)
    loop = asyncio.get_running_loop()
    try:
        await agent.start()
    finally:
        # Final cleanup of all pending tasks to prevent "closed pipe" on Windows
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        # Shutdown async generators and executor explicitly
        await loop.shutdown_asyncgens()
        # On some Python versions shutdown_default_executor is not available or handled by run()
        if hasattr(loop, "shutdown_default_executor"):
            await loop.shutdown_default_executor()

        # Final breath for Windows Proactor transports
        if sys.platform == "win32":
            await asyncio.sleep(0.1)


def run_chatbot() -> None:
    """Main entry point for the mentask CLI."""
    args = _parse_args()

    # If listing is requested, do not start the chatbot
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

    try:
        # Avoid noisy 'ValueError: I/O operation on closed pipe' during exit on Windows
        if sys.platform == "win32":
            import logging

            logging.getLogger("asyncio").setLevel(logging.CRITICAL)

        asyncio.run(_run_async_chatbot(args))
    except KeyboardInterrupt:
        pass
    finally:
        # Give a moment for background transports to close on Windows
        if sys.platform == "win32":
            import time

            time.sleep(0.1)


if __name__ == "__main__":
    if __package__ is None:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run_chatbot()
