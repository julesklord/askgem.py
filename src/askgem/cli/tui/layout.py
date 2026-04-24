from rich.console import RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text


class TuiLayoutManager:
    """
    Manages the visual layout of the AskGem TUI.
    """

    def __init__(self):
        self.layout = Layout()
        self._setup_layout()

    def _setup_layout(self):
        # Split into Header, Body (Main + Side), and Footer
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
        # Split Body into Main (Chat) and Side (Stats)
        self.layout["body"].split_row(
            Layout(name="main", ratio=3),
            Layout(name="side", ratio=1),
        )

    def update_header(self, model: str, version: str):
        header_text = Text.from_markup(f" [bold #3b82f6]askgem[/] [dim]v{version}[/] | Model: [bold white]{model}[/]")
        self.layout["header"].update(Panel(header_text, border_style="#1e293b"))

    def update_footer(self, status: str, color: str = "cyan"):
        footer_text = Text.from_markup(f"[{color}]â—ڈ [/{color}] {status}")
        self.layout["footer"].update(Panel(footer_text, border_style="#1e293b"))

    def update_sidebar(self, stats: str, mission: str = "No active mission"):
        side_content = f"[bold #3b82f6]STATISTICS[/]\n{stats}\n\n[bold #3b82f6]MISSION[/]\n{mission}"
        self.layout["side"].update(Panel(side_content, title="[dim]Context[/]", border_style="#1e293b"))

    def update_main(self, content: RenderableType):
        self.layout["main"].update(content)

    def get_renderable(self) -> Layout:
        return self.layout
