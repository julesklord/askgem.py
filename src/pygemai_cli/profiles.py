import os
import json
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from typing import Optional, List, Dict
from .constants import PROFILES_FILE, PREDEFINED_THEMES
from .utils import get_config_path

def _parse_safety_settings(profile_settings: dict, theme_manager) -> dict:
    parsed_settings = {}
    harm_category_map = {
        "HARM_CATEGORY_HARASSMENT": HarmCategory.HARM_CATEGORY_HARASSMENT,
        "HARM_CATEGORY_HATE_SPEECH": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        "HARM_CATEGORY_SEXUALLY_EXPLICIT": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        "HARM_CATEGORY_DANGEROUS_CONTENT": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    }
    harm_block_threshold_map = {
        "BLOCK_NONE": HarmBlockThreshold.BLOCK_NONE,
        "BLOCK_ONLY_HIGH": HarmBlockThreshold.BLOCK_ONLY_HIGH,
        "BLOCK_MEDIUM_AND_ABOVE": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        "BLOCK_LOW_AND_ABOVE": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    }
    for key, value_str in profile_settings.items():
        category_enum = harm_category_map.get(key)
        threshold_enum = harm_block_threshold_map.get(value_str)
        if category_enum and threshold_enum:
            parsed_settings[category_enum] = threshold_enum
        else:
            print(theme_manager.style("warning_message", f"Advertencia: Configuración de seguridad desconocida '{key}: {value_str}'."))
    return parsed_settings

def load_profiles(theme_manager) -> list:
    path = get_config_path(PROFILES_FILE)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            profiles = json.load(f)
            return profiles if isinstance(profiles, list) else []
    except (OSError, json.JSONDecodeError) as e:
        print(theme_manager.style("error_message", f"Error al cargar perfiles: {e}"))
        return []

def save_profiles(profiles: list, theme_manager):
    path = get_config_path(PROFILES_FILE)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(theme_manager.style("error_message", f"Error al guardar perfiles: {e}"))

def display_profiles(profiles: list, theme_manager, show_details: bool = False, current_profile_name: Optional[str] = None):
    if not profiles:
        print(theme_manager.style("warning_message", "No hay perfiles para mostrar."))
        return
    print(theme_manager.style("section_header", "\n--- Perfiles Disponibles ---"))
    for i, profile in enumerate(profiles):
        name = profile.get("profile_name", f"Perfil {i + 1}")
        model = profile.get("model_id", "No especificado")
        indicator = theme_manager.style("info_message", " (Actual)") if current_profile_name and name == current_profile_name else ""
        num = theme_manager.style("list_item_bullet", f"{i + 1}.")
        text = theme_manager.style("list_item_text", f" {name}{indicator}" + (f" (Modelo: {model})" if show_details else ""))
        print(num + text)
        if show_details:
            prompt = profile.get("system_prompt", "Ninguno")
            print(theme_manager.style("list_item_text", f"    System Prompt: {prompt[:60]}..."))
            print(theme_manager.style("list_item_text", f"    Tema: {profile.get('color_theme_name', 'Legacy')}"))

def _get_predefined_safety_settings(level_name: str) -> Optional[Dict]:
    levels = {
        "Default": None,
        "Lenient": {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE", "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_ONLY_HIGH", "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_ONLY_HIGH",
        },
        "Balanced": {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_ONLY_HIGH", "HARM_CATEGORY_HATE_SPEECH": "BLOCK_ONLY_HIGH",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE", "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_ONLY_HIGH",
        },
        "Strict": {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE", "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE", "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE",
        }
    }
    return levels.get(level_name)

def create_profile_ui(theme_manager) -> Optional[Dict]:
    print(theme_manager.style("section_header", "\n--- Crear Nuevo Perfil ---"))
    name = ""
    while not name:
        name = input(theme_manager.style("prompt_user", "Nombre del perfil: ")).strip()
        if not name: print(theme_manager.style("error_message", "El nombre es obligatorio."))
    
    available = []
    try:
        all_models = list(genai.list_models())
        available = [m for m in all_models if "generateContent" in m.supported_generation_methods]
        available.sort(key=lambda m: m.name)
        for i, m in enumerate(available):
            print(f"{theme_manager.style('list_item_bullet', f'  {i+1}.')} {theme_manager.style('list_item_text', m.name)}")
        
        c = input(theme_manager.style("prompt_user", "Selecciona un modelo por número: ")).strip()
        model_id = available[int(c)-1].name if c.isdigit() and 1 <= int(c) <= len(available) else available[0].name
    except:
        print(theme_manager.style("error_message", "Error al listar modelos."))
        return None

    sys_prompt = input(theme_manager.style("prompt_user", "\nSystem prompt (opcional): ")).strip()
    
    themes = list(PREDEFINED_THEMES.keys())
    print("\nTemas:", ", ".join(themes))
    t_c = input(theme_manager.style("prompt_user", "Tema por nombre (Enter para Legacy): ")).strip()
    theme_name = t_c if t_c in themes else "Legacy"

    return {
        "profile_name": name, "model_id": model_id, "system_prompt": sys_prompt,
        "color_theme_name": theme_name, "safety_settings": _get_predefined_safety_settings("Balanced")
    }

def manage_profiles_ui(profiles: list, theme_manager):
    while True:
        print(theme_manager.style("section_header", "\n--- Gestión de Perfiles ---"))
        print("1. Listar | 2. Crear | 3. Eliminar | b. Volver")
        c = input(theme_manager.style("prompt_user", "Opción: ")).strip().lower()
        if c == '1': display_profiles(profiles, theme_manager, True)
        elif c == '2':
            p = create_profile_ui(theme_manager)
            if p: profiles.append(p); save_profiles(profiles, theme_manager)
        elif c == '3':
            display_profiles(profiles, theme_manager)
            idx = input(theme_manager.style("prompt_user", "Número a eliminar (0 para cancelar): ")).strip()
            if idx.isdigit() and 1 <= int(idx) <= len(profiles):
                profiles.pop(int(idx)-1); save_profiles(profiles, theme_manager)
        elif c == 'b': break
