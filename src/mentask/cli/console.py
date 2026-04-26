"""Console UI module for mentask.

Provides a globally configured Rich console instance with proper
terminal detection and Unicode support for Windows and POSIX systems.
"""

import sys

from rich.console import Console
from rich.theme import Theme

# Define Google Identity Theme for mentask
mentask_theme = Theme(
    {
        "google.blue": "#4285F4",
        "google.yellow": "#FBBC05",
        "google.red": "#EA4335",
        "google.green": "#34A853",
        "agent": "bold #4285F4",
        "user": "bold #FBBC05",
        "status": "#4285F4",
        "warning": "bold #FBBC05",
        "error": "bold #EA4335",
        "success": "bold #34A853",
    }
)


def _enable_windows_vt100() -> None:
    """Enable VT100 ANSI escape processing on Windows 10+.

    This allows the legacy Windows console (conhost) to render ANSI color
    codes and Unicode characters properly, without breaking prompt_toolkit's
    console buffer detection.
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        # STD_OUTPUT_HANDLE = -11
        handle = kernel32.GetStdHandle(-11)
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


# Enable VT100 on Windows before creating the console
_enable_windows_vt100()

# Global configured console instance
console = Console(theme=mentask_theme)
