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

    # Status Indicators (New)
    git_branch: str = "#818cf8"
    git_dirty: str = "#fbbf24"
    git_clean: str = "#4ade80"
    python_venv: str = "#34d399"
    model_badge: str = "#a78bfa"
    cost_badge: str = "#fbbf24"

    # Text on Status Indicators for premium contrast (New)
    text_on_brand: str = "black"
    text_on_success: str = "black"
    text_on_warning: str = "black"
    text_on_error: str = "black"
    text_on_info: str = "black"
    text_on_git_dirty: str = "black"
    text_on_git_clean: str = "black"
    text_on_venv: str = "black"
    text_on_model: str = "white"
    text_on_cost: str = "black"

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
        text_dim="#64748b",
        border="#334155",
        background="#0f172a",
        think_color="#94a3b8",
        code_theme="monokai",
        git_branch="#818cf8",
        git_dirty="#fbcfe8",
        git_clean="#c7d2fe",
        python_venv="#a5f3fc",
        model_badge="#c084fc",
        cost_badge="#fde047",
        text_on_brand="black",
        text_on_success="black",
        text_on_warning="black",
        text_on_error="black",
        text_on_info="black",
        text_on_git_dirty="black",
        text_on_git_clean="black",
        text_on_venv="black",
        text_on_model="black",
        text_on_cost="black",
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
        text_dim="#9ca3af",
        border="#10b981",
        background="#051f15",
        think_color="#9ca3af",
        code_theme="monokai",
        git_branch="#34d399",
        git_dirty="#f59e0b",
        git_clean="#6ee7b7",
        python_venv="#10b981",
        model_badge="#6366f1",
        cost_badge="#d97706",
        text_on_brand="black",
        text_on_success="white",
        text_on_warning="black",
        text_on_error="white",
        text_on_info="white",
        text_on_git_dirty="black",
        text_on_git_clean="black",
        text_on_venv="white",
        text_on_model="white",
        text_on_cost="white",
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
        text_dim="#475569",
        border="#f0abfc",
        background="#0c0a0e",
        think_color="#8b5cf6",
        code_theme="monokai",
        git_branch="#f0abfc",
        git_dirty="#f59e0b",
        git_clean="#2dd4bf",
        python_venv="#06b6d4",
        model_badge="#d946ef",
        cost_badge="#e11d48",
        text_on_brand="black",
        text_on_success="black",
        text_on_warning="black",
        text_on_error="white",
        text_on_info="black",
        text_on_git_dirty="black",
        text_on_git_clean="black",
        text_on_venv="black",
        text_on_model="white",
        text_on_cost="white",
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
        text_dim="#6272a4",
        border="#bd93f9",
        background="#282a36",
        think_color="#8be9fd",
        code_theme="monokai",
        git_branch="#bd93f9",
        git_dirty="#ffb86c",
        git_clean="#50fa7b",
        python_venv="#8be9fd",
        model_badge="#ff79c6",
        cost_badge="#f1fa8c",
        text_on_brand="black",
        text_on_success="black",
        text_on_warning="black",
        text_on_error="white",
        text_on_info="black",
        text_on_git_dirty="black",
        text_on_git_clean="black",
        text_on_venv="black",
        text_on_model="black",
        text_on_cost="black",
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
        think_color="#81a1c1",
        code_theme="nord",
        git_branch="#88c0d0",
        git_dirty="#ebcb8b",
        git_clean="#a3be8c",
        python_venv="#8fbcbb",
        model_badge="#b48ead",
        cost_badge="#d8dee9",
        text_on_brand="black",
        text_on_success="black",
        text_on_warning="black",
        text_on_error="white",
        text_on_info="white",
        text_on_git_dirty="black",
        text_on_git_clean="black",
        text_on_venv="black",
        text_on_model="white",
        text_on_cost="black",
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
        text_dim="#e11d48",
        border="#fda4af",
        background="#4c0519",
        think_color="#e11d48",
        code_theme="monokai",
        git_branch="#fda4af",
        git_dirty="#fef08a",
        git_clean="#bbf7d0",
        python_venv="#f0abfc",
        model_badge="#fda4af",
        cost_badge="#fecdd3",
        text_on_brand="black",
        text_on_success="black",
        text_on_warning="black",
        text_on_error="black",
        text_on_info="black",
        text_on_git_dirty="black",
        text_on_git_clean="black",
        text_on_venv="black",
        text_on_model="black",
        text_on_cost="black",
    ),
    "neon_pink": ThemeConfig(
        brand_primary="#ff006e",
        brand_secondary="#fb5607",
        success="#00ff00",
        warning="#ffbe0b",
        error="#ff006e",
        info="#00d9ff",
        text_primary="#ffffff",
        text_secondary="#00d9ff",
        text_dim="#888888",
        border="#ff006e",
        background="#0a0e27",
        think_color="#ff5c9f",
        code_theme="monokai",
        git_branch="#ff006e",
        git_dirty="#ff5c00",
        git_clean="#00ff00",
        python_venv="#00ffff",
        model_badge="#b537f2",
        cost_badge="#ffbe0b",
        text_on_brand="white",
        text_on_success="black",
        text_on_warning="black",
        text_on_error="white",
        text_on_info="black",
        text_on_git_dirty="white",
        text_on_git_clean="black",
        text_on_venv="black",
        text_on_model="white",
        text_on_cost="black",
    ),
    "neon_cyan": ThemeConfig(
        brand_primary="#00d9ff",
        brand_secondary="#00ff00",
        success="#00ff00",
        warning="#ffff00",
        error="#ff0080",
        info="#00d9ff",
        text_primary="#ffffff",
        text_secondary="#00ff00",
        text_dim="#888888",
        border="#00d9ff",
        background="#0a0e27",
        think_color="#5ce1ff",
        code_theme="monokai",
        git_branch="#00d9ff",
        git_dirty="#ffff00",
        git_clean="#00ff00",
        python_venv="#ff00ff",
        model_badge="#b537f2",
        cost_badge="#ff006e",
        text_on_brand="black",
        text_on_success="black",
        text_on_warning="black",
        text_on_error="white",
        text_on_info="black",
        text_on_git_dirty="black",
        text_on_git_clean="black",
        text_on_venv="white",
        text_on_model="white",
        text_on_cost="white",
    ),
    "neon_purple": ThemeConfig(
        brand_primary="#b537f2",
        brand_secondary="#ff006e",
        success="#39ff14",
        warning="#ffff00",
        error="#ff006e",
        info="#00d9ff",
        text_primary="#ffffff",
        text_secondary="#b537f2",
        text_dim="#888888",
        border="#b537f2",
        background="#0a0e27",
        think_color="#d279ff",
        code_theme="monokai",
        git_branch="#b537f2",
        git_dirty="#ff006e",
        git_clean="#39ff14",
        python_venv="#00d9ff",
        model_badge="#ff5c00",
        cost_badge="#ffff00",
        text_on_brand="white",
        text_on_success="black",
        text_on_warning="black",
        text_on_error="white",
        text_on_info="black",
        text_on_git_dirty="white",
        text_on_git_clean="black",
        text_on_venv="black",
        text_on_model="white",
        text_on_cost="black",
    ),
    "neon_matrix": ThemeConfig(
        brand_primary="#00ff00",
        brand_secondary="#00aa00",
        success="#00ff00",
        warning="#ffff00",
        error="#ff0000",
        info="#00ffff",
        text_primary="#00ff00",
        text_secondary="#00aa00",
        text_dim="#007700",
        border="#00ff00",
        background="#000000",
        think_color="#00dd00",
        code_theme="monokai",
        git_branch="#00ff00",
        git_dirty="#00aa00",
        git_clean="#00dd00",
        python_venv="#008800",
        model_badge="#00ff00",
        cost_badge="#004400",
        text_on_brand="black",
        text_on_success="black",
        text_on_warning="black",
        text_on_error="white",
        text_on_info="black",
        text_on_git_dirty="white",
        text_on_git_clean="black",
        text_on_venv="white",
        text_on_model="black",
        text_on_cost="white",
    ),
    "neon_ghost": ThemeConfig(
        brand_primary="#ffffff",
        brand_secondary="#94a3b8",
        success="#22c55e",
        warning="#eab308",
        error="#ef4444",
        info="#3b82f6",
        text_primary="#f8fafc",
        text_secondary="#94a3b8",
        text_dim="#64748b",
        border="#ffffff",
        background="#000000",
        think_color="#94a3b8",
        code_theme="monokai",
        git_branch="#ffffff",
        git_dirty="#94a3b8",
        git_clean="#cbd5e1",
        python_venv="#e2e8f0",
        model_badge="#3b82f6",
        cost_badge="#0f172a",
        text_on_brand="black",
        text_on_success="white",
        text_on_warning="black",
        text_on_error="white",
        text_on_info="white",
        text_on_git_dirty="black",
        text_on_git_clean="black",
        text_on_venv="black",
        text_on_model="white",
        text_on_cost="white",
    ),
    "monochrome_pro": ThemeConfig(
        brand_primary="#ffffff",
        brand_secondary="#cccccc",
        success="#ffffff",
        warning="#cccccc",
        error="#666666",
        info="#ffffff",
        text_primary="#ffffff",
        text_secondary="#999999",
        text_dim="#777777",
        border="#333333",
        background="#000000",
        think_color="#aaaaaa",
        code_theme="monokai",
        git_branch="#ffffff",
        git_dirty="#888888",
        git_clean="#cccccc",
        python_venv="#aaaaaa",
        model_badge="#ffffff",
        cost_badge="#333333",
        text_on_brand="black",
        text_on_success="black",
        text_on_warning="black",
        text_on_error="white",
        text_on_info="black",
        text_on_git_dirty="white",
        text_on_git_clean="black",
        text_on_venv="black",
        text_on_model="black",
        text_on_cost="white",
    ),
    "tropical_dark": ThemeConfig(
        brand_primary="#8ab4f8",
        brand_secondary="#c5a9f5",
        success="#81c995",
        warning="#fbbf24",
        error="#f28b82",
        info="#8ab4f8",
        text_primary="#d0d0d0",
        text_secondary="#848484",
        text_dim="#404040",
        border="#404040",
        background="#0a0c0f",
        think_color="#848484",
        code_theme="monokai",
        git_branch="#8ab4f8",
        git_dirty="#fde293",
        git_clean="#a8dab5",
        python_venv="#c5a9f5",
        model_badge="#f28b82",
        cost_badge="#ff8bcb",
        text_on_brand="black",
        text_on_success="black",
        text_on_warning="black",
        text_on_error="black",
        text_on_info="black",
        text_on_git_dirty="black",
        text_on_git_clean="black",
        text_on_venv="black",
        text_on_model="black",
        text_on_cost="black",
    ),
    "tropical_light": ThemeConfig(
        brand_primary="#4285f4",
        brand_secondary="#a855f7",
        success="#34a853",
        warning="#fbbf24",
        error="#ea4335",
        info="#4285f4",
        text_primary="#000000",
        text_secondary="#5f6368",
        text_dim="#9aa0a6",
        border="#dadce0",
        background="#ffffff",
        think_color="#5f6368",
        code_theme="monokai",
        git_branch="#4285f4",
        git_dirty="#f4b400",
        git_clean="#0f9d58",
        python_venv="#ab47bc",
        model_badge="#db4437",
        cost_badge="#e91e63",
        text_on_brand="white",
        text_on_success="white",
        text_on_warning="black",
        text_on_error="white",
        text_on_info="white",
        text_on_git_dirty="white",
        text_on_git_clean="white",
        text_on_venv="white",
        text_on_model="white",
        text_on_cost="white",
    ),
}


def get_theme(name: str) -> ThemeConfig:
    """Get a theme by name, fallback to tropical_dark."""
    return THEMES.get(name, THEMES["tropical_dark"])
