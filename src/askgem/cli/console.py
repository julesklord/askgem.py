"""
Console UI module.

Provides a globally configured rich console instance for standardized logging
and output formatting across the application. It does NOT handle business logic.
"""

from rich.console import Console

# Global configured console instance to print rich output throughout the app
console = Console()
