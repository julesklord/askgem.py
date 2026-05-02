"""
Prompt engine for mentask, providing Oh-My-Posh style interactive prompts.
"""

import os
from dataclasses import dataclass
from datetime import datetime

from rich.text import Text

from .themes import ThemeConfig


@dataclass
class PromptSegment:
    text: str
    fg: str
    bg: str | None = None
    icon: str = ""
    bold: bool = True


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
        }

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

    def _render_atomic(self, segments: list[PromptSegment]) -> Text:
        """Renders segments in 'Atomic' pill style."""
        res = Text()
        if not segments:
            return res
        res.append(self.L_HALF, style=segments[0].bg or segments[0].fg)
        for i, seg in enumerate(segments):
            content = f"{seg.icon} {seg.text}" if seg.icon else seg.text
            res.append(f" {content} ", style=f"{seg.fg} on {seg.bg}" if seg.bg else seg.fg)
            if i < len(segments) - 1:
                next_bg = segments[i + 1].bg
                res.append(self.R_TRI, style=f"{seg.bg} on {next_bg}" if next_bg else seg.bg)
        res.append(self.R_HALF, style=segments[-1].bg or segments[-1].fg)
        res.append(" ")
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

    def build_user_prompt(self, style_name: str, cwd: str, is_trusted: bool, cost: float) -> Text:
        """Builds the user prompt using the specified style."""
        segments = []
        # 1. Security Status
        if is_trusted:
            segments.append(
                PromptSegment("TRUSTED", "black", self.theme.success, icon="󰒘" if self.use_nerdfonts else "✓")
            )
        else:
            segments.append(
                PromptSegment("UNTRUSTED", "black", self.theme.error, icon="󰚌" if self.use_nerdfonts else "✗")
            )
        # 2. Path
        segments.append(
            PromptSegment(
                os.path.basename(cwd),
                self.theme.text_primary,
                self.theme.border,
                icon="" if self.use_nerdfonts else "",
            )
        )
        # 3. Cost
        segments.append(
            PromptSegment(f"${cost:.3f}", "white", self.theme.border, icon="󰠠" if self.use_nerdfonts else "$")
        )

        renderer = self.STYLES.get(style_name, self._render_atomic)
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
