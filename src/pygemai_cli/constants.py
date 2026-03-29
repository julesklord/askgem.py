import os

# --- Versión ---
__version__ = "1.3.0"

# --- Archivos de Configuración (Nombres base) ---
ENCRYPTED_API_KEY_FILE = ".gemini_api_key_encrypted"
UNENCRYPTED_API_KEY_FILE = ".gemini_api_key_unencrypted"
PREFERENCES_FILE = ".gemini_chatbot_prefs.json"
PROFILES_FILE = "pygemai_profiles.json"
HISTORY_PREFIX = "chat_history_"

# --- Configuración de Encriptación ---
SALT_SIZE = 16
ITERATIONS = 390_000

# --- Códigos de Colores ANSI ---
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    # Colores base
    BASE_RED = "\033[91m"
    BASE_GREEN = "\033[92m"
    BASE_YELLOW = "\033[93m"
    BASE_BLUE = "\033[94m"
    BASE_MAGENTA = "\033[95m"
    BASE_CYAN = "\033[96m"
    BASE_WHITE = "\033[97m"

# --- Temas Predefinidos ---
PREDEFINED_THEMES = {
    "Legacy": {
        "colors": {
            "prompt_user": Colors.BOLD + Colors.BASE_CYAN,
            "prompt_model_name": Colors.BOLD + Colors.BASE_MAGENTA,
            "response_text": "",
            "thinking_message": Colors.BASE_GREEN,
            "error_message": Colors.BASE_RED,
            "warning_message": Colors.BASE_YELLOW,
            "info_message": Colors.BASE_GREEN,
            "welcome_message_art": Colors.BOLD + Colors.BASE_CYAN,
            "welcome_message_text": Colors.BOLD + Colors.BASE_GREEN,
            "welcome_message_dev": Colors.BASE_YELLOW,
            "welcome_message_changes_title": Colors.BOLD + Colors.BASE_MAGENTA,
            "welcome_message_changes_item_bullet": Colors.BASE_YELLOW,
            "welcome_message_changes_item_text": "",
            "section_header": Colors.BOLD + Colors.BASE_BLUE,
            "list_item_bullet": Colors.BASE_YELLOW,
            "list_item_text": "",
            "inline_code": Colors.BASE_MAGENTA,
            "code_block_lang": Colors.BASE_YELLOW,
            "code_block_content": Colors.BASE_CYAN,
            "markdown_h1": Colors.BOLD + Colors.BASE_BLUE,
            "markdown_h2": Colors.BOLD + Colors.BASE_CYAN,
            "markdown_h3": Colors.BOLD + Colors.BASE_GREEN,
            "markdown_bold": Colors.BOLD,
            "markdown_italic_underline": Colors.UNDERLINE,
        }
    },
    "DefaultDark": {
        "colors": {
            "prompt_user": Colors.BOLD + "\033[38;5;81m",
            "prompt_model_name": Colors.BOLD + "\033[38;5;208m",
            "response_text": "\033[38;5;229m",
            "thinking_message": "\033[38;5;245m",
            "error_message": Colors.BOLD + "\033[38;5;196m",
            "warning_message": "\033[38;5;220m",
            "info_message": "\033[38;5;113m",
            "welcome_message_art": Colors.BOLD + "\033[38;5;81m",
            "welcome_message_text": Colors.BOLD + "\033[38;5;153m",
            "welcome_message_dev": "\033[38;5;208m",
            "welcome_message_changes_title": Colors.BOLD + "\033[38;5;190m",
            "welcome_message_changes_item_bullet": "\033[38;5;81m",
            "welcome_message_changes_item_text": "\033[38;5;229m",
            "section_header": Colors.BOLD + "\033[38;5;153m",
            "list_item_bullet": "\033[38;5;81m",
            "list_item_text": "\033[38;5;229m",
            "inline_code": "\033[38;5;180m",
            "code_block_lang": "\033[38;5;214m",
            "code_block_content": "\033[38;5;113m",
            "markdown_h1": Colors.BOLD + "\033[38;5;81m",
            "markdown_h2": Colors.BOLD + "\033[38;5;117m",
            "markdown_h3": Colors.BOLD + "\033[38;5;153m",
            "markdown_bold": Colors.BOLD,
            "markdown_italic_underline": Colors.UNDERLINE + "\033[38;5;220m",
        }
    }
}
