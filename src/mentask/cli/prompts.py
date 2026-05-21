"""
Prompt engine for mentask, providing Oh-My-Posh style interactive prompts.
"""

import os
from dataclasses import dataclass
from datetime import datetime

from rich.text import Text

from .themes import ThemeConfig
from .ui_utils import get_git_info, get_model_info, get_python_info


@dataclass
class PromptSegment:
    text: str
    fg: str
    bg: str | None = None
    icon: str = ""
    bold: bool = True
    separator: str | None = None  # Custom separator for this segment


@dataclass
class PromptContext:
    style_name: str
    cwd: str
    is_trusted: bool
    cost: float
    model_id: str = ""


class PromptEngine:
    """Generates segment-based prompts for the user and agent."""

    def __init__(self, theme: ThemeConfig, use_nerdfonts: bool = True):
        self.theme = theme
        self.use_nerdfonts = use_nerdfonts

        # Modular style registry
        self.STYLES = {
            "atomic": self._render_atomic,
            "simple": self._render_simple,
            "minimal": self._render_minimal,
            "classic": self._render_classic,
            "rainbow": self._render_rainbow,
            "powerline": self._render_powerline,
        }

    # Powerline / Nerd Font characters
    @property
    def L_HALF(self) -> str:
        return "" if self.use_nerdfonts else ""

    @property
    def R_HALF(self) -> str:
        return "" if self.use_nerdfonts else ""

    @property
    def L_TRI(self) -> str:
        return "" if self.use_nerdfonts else "<"

    @property
    def R_TRI(self) -> str:
        return "" if self.use_nerdfonts else ">"

    @property
    def L_ANGLE(self) -> str:
        return "" if self.use_nerdfonts else "("

    @property
    def R_ANGLE(self) -> str:
        return "" if self.use_nerdfonts else ")"

    def _render_atomic(self, segments: list[PromptSegment]) -> Text:
        """Renders segments in 'Atomic' premium two-line style."""
        res = Text()
        if not segments:
            return res

        # Line 1: Metadata segments as pills (The "Status Line")
        res.append("\n ")
        for seg in segments:
            content = f"{seg.icon} {seg.text}" if seg.icon else seg.text
            res.append(self.L_HALF, style=seg.bg or seg.fg)
            res.append(f" {content} ", style=f"{seg.fg} on {seg.bg}" if seg.bg else seg.fg)
            res.append(self.R_HALF, style=seg.bg or seg.fg)
            res.append(" ")

        # Line 2: Contextual prompt (The "Action Line")
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        display_path = cwd.replace(home, "~")

        res.append("\n ")
        if self.use_nerdfonts:
            res.append("", style=self.theme.brand_primary)
            res.append(f" {display_path} ", style=f"black on {self.theme.brand_primary}")
            res.append("", style=self.theme.brand_primary)
            res.append(" ❯ ", style=f"bold {self.theme.brand_primary}")
        else:
            res.append(f"{display_path} ❯ ", style=f"bold {self.theme.brand_primary}")

        return res

    def _render_rainbow(self, segments: list[PromptSegment]) -> Text:
        """Contiguous segments with Powerline separators."""
        res = Text()
        if not segments:
            return res

        for i, seg in enumerate(segments):
            content = f" {seg.icon} {seg.text} " if seg.icon else f" {seg.text} "
            res.append(content, style=f"{seg.fg} on {seg.bg}" if seg.bg else seg.fg)

            if i < len(segments) - 1:
                next_bg = segments[i + 1].bg
                res.append(self.R_TRI, style=f"{seg.bg} on {next_bg}" if next_bg else seg.bg)
            else:
                res.append(self.R_TRI, style=seg.bg or seg.fg)

        res.append(" ")
        return res

    def _render_powerline(self, segments: list[PromptSegment]) -> Text:
        """Sleek powerline style with angle separators."""
        res = Text()
        for i, seg in enumerate(segments):
            content = f"{seg.icon} {seg.text}" if seg.icon else seg.text
            res.append(content, style=seg.fg)
            if i < len(segments) - 1:
                res.append(f" {self.R_ANGLE} ", style="dim")
        res.append(" ❯ ", style=self.theme.brand_primary)
        return res

    def _render_simple(self, segments: list[PromptSegment]) -> Text:
        """Colored text with icons but no background blocks."""
        res = Text()
        for seg in segments:
            content = f"{seg.icon} {seg.text}" if seg.icon else seg.text
            res.append(f"{content} ", style=seg.fg)
        res.append("❯ ", style=self.theme.brand_primary)
        return res

    def _render_minimal(self, segments: list[PromptSegment]) -> Text:
        """Just icons and essential info, very compact."""
        res = Text()
        for seg in segments:
            if seg.icon:
                res.append(f"{seg.icon} ", style=seg.bg or seg.fg)
        res.append("» ", style=self.theme.brand_primary)
        return res

    def _render_classic(self, segments: list[PromptSegment]) -> Text:
        """Traditional [segment] style."""
        res = Text()
        for seg in segments:
            res.append("[", style="dim")
            res.append(seg.text, style=seg.fg)
            res.append("] ", style="dim")
        res.append("> ", style="bold")
        return res

    def build_user_prompt(self, context: PromptContext) -> Text:
        """Builds the user prompt using the specified style."""
        segments = []

        # 1. OS Icon
        os_icon = "󰀵" if os.name == "posix" else "󰖳"
        segments.append(
            PromptSegment("", "black", self.theme.brand_primary, icon=os_icon if self.use_nerdfonts else "")
        )

        # 2. Security Status
        if context.is_trusted:
            segments.append(
                PromptSegment("TRUSTED", "black", self.theme.success, icon="󰒘" if self.use_nerdfonts else "✓")
            )
        else:
            segments.append(
                PromptSegment("UNTRUSTED", "black", self.theme.error, icon="󰚌" if self.use_nerdfonts else "✗")
            )

        # 3. Path
        segments.append(
            PromptSegment(
                os.path.basename(context.cwd),
                self.theme.text_primary,
                self.theme.border,
                icon="" if self.use_nerdfonts else "",
            )
        )

        # 4. Git Info
        git = get_git_info()
        if git["branch"]:
            git_icon = "󰊢" if self.use_nerdfonts else "git:"
            git_color = self.theme.git_dirty if git["is_dirty"] else self.theme.git_clean
            segments.append(PromptSegment(git["branch"], "black", git_color, icon=git_icon))

        # 5. Python Info
        py = get_python_info()
        if py["venv"]:
            py_icon = "" if self.use_nerdfonts else "py:"
            segments.append(PromptSegment(py["venv"], "black", self.theme.python_venv, icon=py_icon))

        # 6. Model Info
        if context.model_id:
            m = get_model_info(context.model_id)
            m_icon = "󰚩" if self.use_nerdfonts else "AI:"
            segments.append(PromptSegment(m["name"], "white", self.theme.model_badge, icon=m_icon))

        # 7. Cost
        cost_str = f"${context.cost:.3f}" if context.cost >= 0.01 else f"${context.cost:.4f}"
        if context.cost == 0:
            cost_str = "$0.000"
        segments.append(
            PromptSegment(cost_str, "black", self.theme.cost_badge, icon="󰠠" if self.use_nerdfonts else "$")
        )

        renderer = self.STYLES.get(context.style_name, self._render_atomic)
        return renderer(segments)

    def build_agent_header(self, style_name: str, tool: str | None = None, is_natural: bool = False) -> Text:
        """Builds the agent response header using the specified style."""
        segments = []
        segments.append(
            PromptSegment("mentask", "black", self.theme.brand_primary, icon="✦" if self.use_nerdfonts else "*")
        )
        now = datetime.now().strftime("%H:%M")
        segments.append(
            PromptSegment(now, self.theme.text_primary, self.theme.border, icon="󱑎" if self.use_nerdfonts else "")
        )

        if tool:
            segments.append(
                PromptSegment(tool, "white", self.theme.brand_secondary, icon="🛠️" if self.use_nerdfonts else ">")
            )
        elif is_natural:
            segments.append(PromptSegment("MESSAGE", "black", "#A855F7", icon="󰭻" if self.use_nerdfonts else "»"))

        renderer = self.STYLES.get(style_name, self._render_atomic)
        return renderer(segments)

    def build_status_bar(self, model_id: str, mode: str, tokens: int, cost: float) -> Text:
        """Builds a professional status bar for the bottom of the screen."""
        res = Text()

        # 1. Brand + Mode
        res.append(f" {self.L_HALF}", style=self.theme.brand_primary)
        brand_icon = "󱚣 " if self.use_nerdfonts else ""
        res.append(f" {brand_icon}{mode.upper()} ", style=f"black on {self.theme.brand_primary}")
        res.append(f"{self.R_HALF}", style=self.theme.brand_primary)
        res.append(" ")

        # 2. Model
        m = get_model_info(model_id)
        res.append(f"{self.L_HALF}", style=self.theme.model_badge)
        m_icon = "󰚩 " if self.use_nerdfonts else ""
        res.append(f" {m_icon}{m['name']} ", style=f"black on {self.theme.model_badge}")
        res.append(f"{self.R_HALF}", style=self.theme.model_badge)
        res.append(" ")

        # 3. Git Info
        git = get_git_info()
        if git["branch"]:
            res.append(f"{self.L_HALF}", style=self.theme.git_branch)
            git_icon = "󰊢 " if self.use_nerdfonts else ""
            res.append(f" {git_icon}{git['branch']} ", style=f"black on {self.theme.git_branch}")
            res.append(f"{self.R_HALF}", style=self.theme.git_branch)
            res.append(" ")

        # 4. Metrics
        cost_str = f"${cost:.3f}"
        res.append(f"{self.L_HALF}", style=self.theme.cost_badge)
        cost_icon = "󰠠 " if self.use_nerdfonts else ""
        res.append(f" {cost_icon}{cost_str} ", style=f"black on {self.theme.cost_badge}")

        token_icon = " 󰮄 " if self.use_nerdfonts else " T:"
        res.append(f"{token_icon}{tokens:,} ", style=f"black on {self.theme.cost_badge}")
        res.append(f"{self.R_HALF}", style=self.theme.cost_badge)

        return res
