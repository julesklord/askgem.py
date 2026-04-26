"""
Theme and styling system for mentask.

Inspired by professional agents like GitHub Copilot, VS Code, and Claude.
Uses a CSS-like approach with composable style definitions.
"""

from dataclasses import dataclass
from typing import TypedDict


class StyleDict(TypedDict):
    """CSS-inspired style dictionary."""

    color: str
    bgcolor: str | None
    bold: bool
    italic: bool
    dim: bool
    underline: bool


@dataclass(frozen=True)
class Style:
    """Immutable style definition with Rich markup support."""

    color: str | None = None
    bgcolor: str | None = None
    bold: bool = False
    italic: bool = False
    dim: bool = False
    underline: bool = False

    def to_rich_markup(self, text: str) -> str:
        """Convert to Rich markup format."""
        tags = []
        if self.bold:
            tags.append("bold")
        if self.italic:
            tags.append("italic")
        if self.dim:
            tags.append("dim")
        if self.underline:
            tags.append("underline")
        if self.color:
            tags.append(self.color)
        if self.bgcolor:
            tags.append(f"on {self.bgcolor}")

        if not tags:
            return text

        tag_str = " ".join(tags)
        return f"[{tag_str}]{text}[/]"


@dataclass(frozen=True)
class ThemeConfig:
    """Complete theme configuration."""

    # Brand colors
    brand_primary: str
    brand_secondary: str

    # Semantic colors
    success: str
    warning: str
    error: str
    info: str

    # Text colors
    text_primary: str
    text_secondary: str
    text_dim: str

    # UI Elements
    border: str
    background: str

    # Specialized
    think_color: str
    code_theme: str

    def get_style(self, element: str) -> Style:
        """Get style for a specific element."""
        styles = {
            # Headers and titles
            "h1": Style(color=self.brand_primary, bold=True),
            "h2": Style(color=self.brand_secondary, bold=True),
            "h3": Style(color=self.brand_secondary),
            # Status messages
            "success": Style(color=self.success, bold=True),
            "warning": Style(color=self.warning, bold=True),
            "error": Style(color=self.error, bold=True),
            "info": Style(color=self.info, dim=False),
            # Code and thinking
            "code": Style(color="cyan"),
            "think": Style(color=self.think_color, dim=True),
            # User/Agent
            "user_label": Style(color=self.text_secondary),
            "agent_label": Style(color=self.brand_primary, bold=True),
            # Utilities
            "dim": Style(dim=True),
            "bold": Style(bold=True),
            "accent": Style(color=self.brand_primary),
        }
        return styles.get(element, Style())


# Theme definitions
THEMES = {
    "indigo": ThemeConfig(
        brand_primary="#818cf8",
        brand_secondary="#a78bfa",
        success="#4ade80",
        warning="#fbbf24",
        error="#f87171",
        info="#60a5fa",
        text_primary="#f1f5f9",
        text_secondary="#94a3b8",
        text_dim="#475569",
        border="#334155",
        background="#0f172a",
        think_color="#64748b",
        code_theme="monokai",
    ),
    "emerald": ThemeConfig(
        brand_primary="#34d399",
        brand_secondary="#6ee7b7",
        success="#10b981",
        warning="#f59e0b",
        error="#f43f5e",
        info="#0ea5e9",
        text_primary="#ecfdf5",
        text_secondary="#a7f3d0",
        text_dim="#6b7280",
        border="#10b981",
        background="#051f15",
        think_color="#4b5563",
        code_theme="monokai",
    ),
    "cyberpunk": ThemeConfig(
        brand_primary="#f0abfc",
        brand_secondary="#d946ef",
        success="#4ade80",
        warning="#fbbf24",
        error="#f43f5e",
        info="#06b6d4",
        text_primary="#fafaf9",
        text_secondary="#2dd4bf",
        text_dim="#1e293b",
        border="#f0abfc",
        background="#0c0a0e",
        think_color="#4c1d95",
        code_theme="monokai",
    ),
    "dracula": ThemeConfig(
        brand_primary="#bd93f9",
        brand_secondary="#ff79c6",
        success="#50fa7b",
        warning="#f1fa8c",
        error="#ff5555",
        info="#8be9fd",
        text_primary="#f8f8f2",
        text_secondary="#6272a4",
        text_dim="#44475a",
        border="#bd93f9",
        background="#282a36",
        think_color="#6272a4",
        code_theme="monokai",
    ),
    "nord": ThemeConfig(
        brand_primary="#88c0d0",
        brand_secondary="#81a1c1",
        success="#a3be8c",
        warning="#ebcb8b",
        error="#bf616a",
        info="#5e81ac",
        text_primary="#eceff4",
        text_secondary="#d8dee9",
        text_dim="#4c566a",
        border="#88c0d0",
        background="#2e3440",
        think_color="#4c566a",
        code_theme="nord",
    ),
    "sakura": ThemeConfig(
        brand_primary="#fda4af",
        brand_secondary="#f0abfc",
        success="#34d399",
        warning="#fbbf24",
        error="#fb7185",
        info="#38bdf8",
        text_primary="#fff1f2",
        text_secondary="#fda4af",
        text_dim="#9f1239",
        border="#fda4af",
        background="#4c0519",
        think_color="#9f1239",
        code_theme="monokai",
    ),
}


def get_theme(name: str) -> ThemeConfig:
    """Get a theme by name, fallback to indigo."""
    return THEMES.get(name, THEMES["indigo"])
