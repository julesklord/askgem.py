import re
import sys
import os
import time
import shutil
import threading
import itertools
from typing import Optional, Dict
from .constants import Colors, PREDEFINED_THEMES, __version__

class ThemeManager:
    def __init__(self, available_themes: dict, default_theme_name: str = "Legacy"):
        self.available_themes = available_themes
        self.default_theme_name = default_theme_name
        self.active_theme_name = default_theme_name
        
        if default_theme_name not in available_themes:
            if available_themes:
                self.default_theme_name = list(available_themes.keys())[0]
                self.active_theme_name = self.default_theme_name
            else:
                self.active_theme_colors = {}
                return
        self.active_theme_colors = available_themes[self.active_theme_name].get("colors", {})

    def set_active_theme(self, theme_name: str):
        if theme_name in self.available_themes:
            self.active_theme_name = theme_name
            self.active_theme_colors = self.available_themes[theme_name].get("colors", {})
        else:
            self.active_theme_name = self.default_theme_name
            self.active_theme_colors = self.available_themes[self.default_theme_name].get("colors", {})

    def get_color(self, element_key: str) -> str:
        return self.active_theme_colors.get(element_key, "")

    def style(self, element_key: str, text: str, apply_reset: bool = True) -> str:
        color_code = self.get_color(element_key)
        if not text.strip() and (element_key == "markdown_bold" or element_key == "markdown_italic_underline"):
            return text
        if color_code:
            reset_code = Colors.RESET if apply_reset else ""
            return f"{color_code}{text}{reset_code}"
        return text

def process_standard_markdown(text: str, theme_manager: ThemeManager) -> str:
    text = re.sub(r"`(.*?)`", lambda m: theme_manager.style("inline_code", m.group(1)), text)
    text = re.sub(r"^### (.*)", lambda m: theme_manager.style("markdown_h3", m.group(1).strip()), text, flags=re.MULTILINE)
    text = re.sub(r"^## (.*)", lambda m: theme_manager.style("markdown_h2", m.group(1).strip()), text, flags=re.MULTILINE)
    text = re.sub(r"^# (.*)", lambda m: theme_manager.style("markdown_h1", m.group(1).strip()), text, flags=re.MULTILINE)
    text = re.sub(r"^(\s*)\* (.*)", lambda m: f"{m.group(1)}{theme_manager.get_color('list_item_bullet')}* {Colors.RESET}{theme_manager.style('list_item_text', m.group(2))}", text, flags=re.MULTILINE)
    text = re.sub(r"^(\s*)- (.*)", lambda m: f"{m.group(1)}{theme_manager.get_color('list_item_bullet')}- {Colors.RESET}{theme_manager.style('list_item_text', m.group(2))}", text, flags=re.MULTILINE)
    text = re.sub(r"^(\s*)(\d+\.) (.*)", lambda m: f"{m.group(1)}{theme_manager.get_color('list_item_bullet')}{m.group(2)} {Colors.RESET}{theme_manager.style('list_item_text', m.group(3))}", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", lambda m: theme_manager.style("markdown_bold", m.group(1)), text)
    text = re.sub(r"\*([^*]+?)\*", lambda m: theme_manager.style("markdown_italic_underline", m.group(1)), text)
    text = re.sub(r"_(.+?)_", lambda m: theme_manager.style("markdown_italic_underline", m.group(1)), text)
    return text

def format_gemini_output(text: str, theme_manager: ThemeManager) -> str:
    processed_parts = []
    last_end = 0
    for match in re.finditer(r"```(\w*)\n?(.*?)```", text, flags=re.DOTALL):
        pre_match_text = text[last_end:match.start()]
        processed_parts.append(process_standard_markdown(pre_match_text, theme_manager))
        lang = match.group(1) or ""
        code_content = match.group(2).strip('\n')
        indented_code = "\n".join([f"  {line}" for line in code_content.split('\n')])
        lang_styled = theme_manager.style("code_block_lang", f"```{lang}", apply_reset=False)
        content_styled = theme_manager.style("code_block_content", indented_code)
        code_block_formatted = (f"{lang_styled}{Colors.RESET}\n{content_styled}\n"
                                f"{theme_manager.style('code_block_lang', '```')}")
        processed_parts.append(code_block_formatted)
        last_end = match.end()
    remaining_text = text[last_end:]
    processed_parts.append(process_standard_markdown(remaining_text, theme_manager))
    base_response_color = theme_manager.get_color("response_text")
    final_content = "".join(processed_parts)
    if final_content.strip() and not final_content.startswith("\033["):
        return base_response_color + final_content + Colors.RESET if base_response_color else final_content
    return final_content

THINKING_MESSAGES = ["Pensando...", "Thinking...", "Réflexion...", "Meditando...", "Un momento..."]
SPINNER_CHARS = itertools.cycle(['-', '\\', '|', '/'])
stop_animation_event = threading.Event()

def animate_thinking(theme_manager: ThemeManager, model_prompt_text: str):
    message_cycler = itertools.cycle(THINKING_MESSAGES)
    current_message = next(message_cycler)
    counter = 0
    terminal_width = shutil.get_terminal_size((80, 24)).columns
    while not stop_animation_event.is_set():
        if counter >= 20:
            current_message = next(message_cycler)
            counter = 0
        spinner = next(SPINNER_CHARS)
        msg_styled = theme_manager.style("thinking_message", f" {current_message} {spinner}", apply_reset=False)
        full_line = f"\r{model_prompt_text}{msg_styled}{Colors.RESET} "
        sys.stdout.write(full_line.ljust(terminal_width)[:terminal_width] + '\r')
        sys.stdout.flush()
        counter += 1
        time.sleep(0.1)
    sys.stdout.write('\r' + ' ' * terminal_width + '\r')
    sys.stdout.flush()

def display_welcome_message(theme_manager: ThemeManager):
    art = f"""
PPPPPPP  YY    YY   GGGGGG   EEEEE   MMMMM      MMMMM     AAAAA      II 
PP    PP  YY  YY   GG        EE       MM MMM  MMM MM     AA   AA     
PP    PP   YYYY    GG   GGG  EEEEEEE  MM  MMMMMM  MM    AAAA AAAA    II
PPPPPPP     YY     GG    GG  EE       MM   MMMM   MM   AA  AAA  AA   II
PP          YY   ___GG__GG____EEEEE____M____MM____M__ A_A_______A_A__II____
PP          YY      ___________________________________________________________ 
__________________________________________________________________________________
Refactorizado y Mejorado! ___________________________________________________________
"""
    print(theme_manager.style("welcome_message_art", art.strip()))
    welcome = f"¡Bienvenido a PyGemAi v{__version__}!"
    dev = "Un desarrollo de: julesklord(julioglez.93@gmail.com)"
    print(theme_manager.style("welcome_message_text", f"{welcome:^80}"))
    print(theme_manager.style("welcome_message_dev", f"{dev:^80}"))
    print(theme_manager.style("welcome_message_changes_title", "\n--- Cambios en esta versión ---"))
    changes = [
        "📦 Arquitectura modular mejorada para mayor estabilidad.",
        "🏠 Configuración centralizada en ~/.pygemai.",
        "💬 Chat optimizado: Formateado perfecto sin doble impresión.",
        "🔐 Seguridad reforzada en el manejo de API Keys."
    ]
    for change in changes:
        bullet = theme_manager.style("welcome_message_changes_item_bullet", "* ")
        text = theme_manager.style("welcome_message_changes_item_text", change)
        print(bullet + text)
    print(theme_manager.style("section_header", "\n" + "-" * 80))
    time.sleep(1)
