"""
dashboard.py — DEPRECATED

The Textual TUI has been removed. The Rich streaming renderer in
cli/renderer.py is now the only UI layer.

This file is kept as a stub to avoid ImportError in any stale
bytecode or third-party references. It will be deleted in v0.9.0.
"""


def AskGemDashboard(*args, **kwargs):
    raise RuntimeError(
        "AskGemDashboard has been removed. Run 'askgem' directly — the Rich renderer is now the default."
    )
