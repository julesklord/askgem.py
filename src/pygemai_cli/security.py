import os
import base64
from typing import Optional
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, InvalidToken
from .constants import SALT_SIZE, ITERATIONS, ENCRYPTED_API_KEY_FILE, UNENCRYPTED_API_KEY_FILE
from .utils import get_config_path

def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def save_encrypted_api_key(api_key: str, password: str, theme_manager) -> None:
    path = get_config_path(ENCRYPTED_API_KEY_FILE)
    try:
        salt = os.urandom(SALT_SIZE)
        derived_key = _derive_key(password, salt)
        f = Fernet(derived_key)
        encrypted_api_key = f.encrypt(api_key.encode())
        with open(path, "wb") as key_file:
            key_file.write(salt)
            key_file.write(encrypted_api_key)
        print(theme_manager.style("info_message", f"API Key encriptada y guardada en {path}"))
        if os.name != "nt":
            os.chmod(path, 0o600)
    except (OSError, ValueError) as e:
        print(theme_manager.style("error_message", f"Error al guardar la API Key encriptada: {e}"))

def load_decrypted_api_key(password: str, theme_manager) -> Optional[str]:
    path = get_config_path(ENCRYPTED_API_KEY_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as key_file:
            salt = key_file.read(SALT_SIZE)
            encrypted_api_key = key_file.read()
        derived_key = _derive_key(password, salt)
        f = Fernet(derived_key)
        return f.decrypt(encrypted_api_key).decode()
    except InvalidToken:
        return None
    except (OSError, ValueError) as e:
        print(theme_manager.style("error_message", f"Error al cargar o desencriptar la API Key: {e}"))
        return None

def save_unencrypted_api_key(api_key: str, theme_manager) -> None:
    path = get_config_path(UNENCRYPTED_API_KEY_FILE)
    try:
        with open(path, "w") as key_file:
            key_file.write(api_key)
        warning_style = theme_manager.get_color("warning_message")
        from .constants import Colors
        print(f"{Colors.BOLD}{warning_style}ADVERTENCIA:{Colors.RESET}{warning_style} "
              f"API Key guardada SIN ENCRIPTAR en {path}.{Colors.RESET}")
        if os.name != "nt":
            os.chmod(path, 0o600)
    except OSError as e:
        print(theme_manager.style("error_message", f"Error al guardar la API Key sin encriptar: {e}"))

def load_unencrypted_api_key(theme_manager) -> Optional[str]:
    path = get_config_path(UNENCRYPTED_API_KEY_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as key_file:
            api_key = key_file.read().strip()
            if api_key:
                warning_style = theme_manager.get_color("warning_message")
                from .constants import Colors
                print(f"{Colors.BOLD}{warning_style}ADVERTENCIA:{Colors.RESET}{warning_style} "
                      f"API Key cargada SIN ENCRIPTAR desde {path}.{Colors.RESET}")
                return api_key
            return None
    except OSError as e:
        print(theme_manager.style("error_message", f"Error al cargar la API Key sin encriptar: {e}"))
        return None
