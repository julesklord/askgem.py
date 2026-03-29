import os
import sys
import time
import getpass
import threading
import google.generativeai as genai
from typing import Optional

# Importaciones locales
from .constants import (
    PREDEFINED_THEMES, ENCRYPTED_API_KEY_FILE, UNENCRYPTED_API_KEY_FILE,
    Colors, __version__
)
from .utils import get_config_path
from .ui import ThemeManager, display_welcome_message, animate_thinking, format_gemini_output, stop_animation_event
from .security import (
    load_decrypted_api_key, save_encrypted_api_key, 
    load_unencrypted_api_key, save_unencrypted_api_key
)
from .profiles import load_profiles, manage_profiles_ui, _parse_safety_settings
from .config import load_preferences, save_preferences
from .history import load_chat_history, save_chat_history

def run_chatbot():
    theme_manager = ThemeManager(PREDEFINED_THEMES, "Legacy")
    profiles_data = load_profiles(theme_manager)
    active_profile = None
    profile_model_id = None
    profile_safety_settings = None
    profile_system_prompt = None
    profile_name = "Default"

    if profiles_data:
        active_profile = profiles_data[0]
        profile_name = active_profile.get("profile_name", "Perfil Desconocido")
        theme_manager.set_active_theme(active_profile.get("color_theme_name", "Legacy"))

    display_welcome_message(theme_manager)

    if active_profile:
        print(theme_manager.style("info_message", f"Perfil activo: '{profile_name}'"))
        profile_model_id = active_profile.get("model_id")
        profile_system_prompt = active_profile.get("system_prompt")
        if active_profile.get("safety_settings"):
            profile_safety_settings = _parse_safety_settings(active_profile.get("safety_settings"), theme_manager)
    
    # --- Manejo de API KEY ---
    API_KEY = None
    key_loaded = False
    
    enc_path = get_config_path(ENCRYPTED_API_KEY_FILE)
    if os.path.exists(enc_path):
        for _ in range(3):
            pwd = getpass.getpass(theme_manager.style("prompt_user", "Contraseña API Key (Enter para omitir): "))
            if not pwd: break
            API_KEY = load_decrypted_api_key(pwd, theme_manager)
            if API_KEY: key_loaded = True; break
            print(theme_manager.style("error_message", "Incorrecta."))

    if not API_KEY:
        API_KEY = load_unencrypted_api_key(theme_manager) or os.getenv("GOOGLE_API_KEY")
        if API_KEY: key_loaded = True

    if not API_KEY:
        API_KEY = input(theme_manager.style("prompt_user", "Ingresa tu Google API Key: ")).strip()
        if not API_KEY: sys.exit(1)
        
    if API_KEY and not key_loaded:
        print(theme_manager.style("prompt_user", "¿Guardar? 1. Encriptada | 2. Plano | 3. No"))
        c = input("> ").strip()
        if c == '1':
            p = getpass.getpass("Nueva contraseña: ")
            if p and p == getpass.getpass("Confirma: "): save_encrypted_api_key(API_KEY, p, theme_manager)
        elif c == '2': save_unencrypted_api_key(API_KEY, theme_manager)

    genai.configure(api_key=API_KEY)

    # --- Selección de Modelo ---
    MODEL_NAME = profile_model_id
    if not MODEL_NAME:
        prefs = load_preferences(theme_manager)
        try:
            models = [m for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
            for i, m in enumerate(models):
                print(f"{i+1}. {m.name}")
            idx = input(theme_manager.style("prompt_user", "Selecciona modelo: ")).strip()
            MODEL_NAME = models[int(idx)-1].name if idx.isdigit() else models[0].name
            prefs["last_used_model"] = MODEL_NAME
            save_preferences(prefs, theme_manager)
        except (ValueError, RuntimeError) as e:
            print(theme_manager.style("error_message", f"Error: {e}")); sys.exit(1)

    # --- Chat Loop ---
    history = load_chat_history(MODEL_NAME, theme_manager) or []
    if profile_system_prompt:
        history.insert(0, {'role': 'user', 'parts': [{'text': profile_system_prompt}]})
    
    model = genai.GenerativeModel(MODEL_NAME, safety_settings=profile_safety_settings)
    chat = model.start_chat(history=history)
    
    print(theme_manager.style("info_message", f"\nChat iniciado con {MODEL_NAME}. Escribe 'salir' para terminar."))
    
    while True:
        try:
            user_input = input(theme_manager.style("prompt_user", "Tú: ")).strip()
            if user_input.lower() in ["salir", "exit", "quit"]: break
            if not user_input: continue

            model_prompt = theme_manager.style("prompt_model_name", f"{MODEL_NAME.split('/')[-1]}: ", apply_reset=False)
            
            stop_animation_event.clear()
            anim = threading.Thread(target=animate_thinking, args=(theme_manager, model_prompt))
            anim.daemon = True
            anim.start()

            try:
                # OPTION A: No streaming to avoid double-printing
                response = chat.send_message(user_input, stream=False)
                stop_animation_event.set()
                anim.join()
                
                # Print and format once
                print(f"\r{model_prompt}{Colors.RESET}", end="")
                formatted = format_gemini_output(response.text, theme_manager)
                print(formatted + "\n")
                
            except RuntimeError as e:
                stop_animation_event.set()
                print(theme_manager.style("error_message", f"\nError API: {e}"))
                
        except KeyboardInterrupt:
            break

    if input(theme_manager.style("prompt_user", "¿Guardar historial? (S/n): ")).lower() != 'n':
        save_chat_history(chat, MODEL_NAME, theme_manager)
    print(theme_manager.style("section_header", "\n--- ¡Hasta la próxima! ---"))

if __name__ == "__main__":
    # Ajuste de path para ejecución directa
    if __package__ is None:
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run_chatbot()
