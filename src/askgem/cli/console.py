"""Console UI module for AskGem.

This module provides a globally configured rich console instance with the
Google Brand Identity theme (Web 2.0 colors) for standardized logging
and output formatting.
"""

from rich.console import Console
from rich.theme import Theme

# Define Google Identity Theme for AskGem
# Blue = Agent/Global, Yellow = User/Action
askgem_theme = Theme({
    "google.blue": "bold color(33)",
    "google.yellow": "bold color(220)",
    "google.red": "bold color(203)",
    "google.green": "bold color(71)",
    "agent": "bold color(33)",
    "user": "bold color(220)",
    "status": "italic color(33)",
    "warning": "bold color(220)",
    "error": "bold color(210)",
    "success": "bold color(71)",
})

# Global configured console instance to print rich output throughout the app
console = Console(theme=askgem_theme)
