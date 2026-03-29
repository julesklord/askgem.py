import os
import json
from typing import Optional, List
from .utils import get_config_path
from .constants import HISTORY_PREFIX

def get_chat_history_filename(model_name: str) -> str:
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in model_name)
    return get_config_path(f"{HISTORY_PREFIX}{safe_name}.json")

def save_chat_history(chat_session, model_name: str, theme_manager):
    filename = get_chat_history_filename(model_name)
    history = [{'role': c.role, 'parts': [{'text': p.text} for p in c.parts if hasattr(p, "text")]} for c in chat_session.history]
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        print(theme_manager.style("info_message", f"Historial guardado en {filename}"))
    except OSError as e:
        print(theme_manager.style("error_message", f"Error al guardar historial: {e}"))

def load_chat_history(model_name: str, theme_manager) -> Optional[List]:
    filename = get_chat_history_filename(model_name)
    if not os.path.exists(filename):
        return None
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(theme_manager.style("error_message", f"Error al cargar historial: {e}"))
        return None
