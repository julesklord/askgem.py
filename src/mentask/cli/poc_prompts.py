import os
import time
from datetime import datetime

from rich.console import Console
from rich.text import Text

console = Console()


class PoshPrompt:
    """PoC for Oh-My-Posh style prompts in mentask."""

    def __init__(self, theme_color="#818cf8"):
        self.theme_color = theme_color
        self.bg_color = "#1e293b"
        self.user_color = "#34d399"
        self.agent_color = "#818cf8"
        self.warn_color = "#fbbf24"
        self.error_color = "#f87171"

    def _segment(self, text, fg, bg, bold=True):
        return Text(f" {text} ", style=f"{fg} on {bg}" if bg else fg)

    def render_user_prompt(self, cwd, untrust=True, cost=0.05):
        """Renders the interactive user prompt."""
        p = Text()

        # 1. Untrust Segment
        if untrust:
            p.append("", style=self.error_color)
            p.append(" 󰚌 UNTRUST ", style=f"black on {self.error_color}")
            p.append("", style=f"{self.error_color} on {self.bg_color}")
        else:
            p.append("", style=self.user_color)
            p.append(" 󰒘 TRUSTED ", style=f"black on {self.user_color}")
            p.append("", style=f"{self.user_color} on {self.bg_color}")

        # 2. Path Segment
        p.append(f"  {os.path.basename(cwd)} ", style=f"white on {self.bg_color}")
        p.append("", style=f"{self.bg_color} on #334155")

        # 3. Cost Segment
        p.append(f" 󰠠 ${cost:.3f} ", style="white on #334155")
        p.append("", style="#334155")

        p.append(" ")
        return p

    def render_agent_header(self, tool=None, status="ok"):
        """Renders the agent's response header."""
        p = Text()
        now = datetime.now().strftime("%H:%M:%S")

        # 1. Brand Segment
        p.append("", style=self.agent_color)
        p.append(" ✦ mentask ", style=f"black on {self.agent_color}")
        p.append("", style=f"{self.agent_color} on {self.bg_color}")

        # 2. Time Segment
        p.append(f" 󱑎 {now} ", style=f"white on {self.bg_color}")
        p.append("", style=f"{self.bg_color} on #334155")

        # 3. Tool/Status Segment
        if tool:
            p.append(f" 🛠️ {tool} ", style="white on #334155")
            p.append("", style="#334155 on #475569")
            p.append(" 󰄬 ", style="green on #475569")
            p.append("", style="#475569")
        else:
            p.append(" 🚀 READY ", style="white on #334155")
            p.append("", style="#334155")

        return p


def run_poc():
    prompt = PoshPrompt()

    console.clear()
    console.print("\n[bold cyan]Proof of Concept: Atomic Multi-Prompt UI[/bold cyan]\n")

    # Simulate User Input
    user_p = prompt.render_user_prompt(os.getcwd(), untrust=True, cost=0.012)
    console.print(user_p, end="")
    console.print("¿Cómo está el clima hoy y qué archivos hay aquí?")

    time.sleep(0.5)

    # Simulate Agent Response
    agent_h = prompt.render_agent_header(tool="list_dir")
    console.print(f"\n{agent_h}")
    console.print("  [dim]│[/] Analizando el directorio actual...")
    console.print("  [dim]│[/] He encontrado 5 archivos de configuración.")
    console.print("\n  Aquí tienes la lista de lo que veo en [bold]g:\\DEVELOPMENT\\mentask.py[/]:")
    console.print("  - [green]src/[/]")
    console.print("  - [blue]tests/[/]")
    console.print("  - README.md")

    console.print("\n" + "─" * 40 + "\n")

    # Trusted version
    user_p2 = prompt.render_user_prompt(os.getcwd(), untrust=False, cost=0.015)
    console.print(user_p2, end="")
    console.print("Excelente, ahora borra los temporales.")

    agent_h2 = prompt.render_agent_header(tool="rm", status="error")
    console.print(f"\n{agent_h2}")
    console.print("  [dim]│[/] Intentando borrar .tmp/...")
    console.print("  [red]✘ Error:[/] No tienes permisos para borrar esa carpeta.")


if __name__ == "__main__":
    run_poc()
