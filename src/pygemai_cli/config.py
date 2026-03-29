import os
import json
from .utils import get_config_path
from .constants import PREFERENCES_FILE

def save_preferences(prefs: dict, theme_manager):
    path = get_config_path(PREFERENCES_FILE)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(theme_manager.style("error_message", f"Error al guardar preferencias: {e}"))

def load_preferences(theme_manager) -> dict:
    path = get_config_path(PREFERENCES_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(theme_manager.style("error_message", f"Error al cargar preferencias: {e}"))
        return {}
