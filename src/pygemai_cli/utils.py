import os
from pathlib import Path

def get_config_dir() -> Path:
    """Retorna el directorio de configuración ~/.pygemai."""
    config_dir = Path.home() / ".pygemai"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_config_path(filename: str) -> str:
    """Retorna la ruta absoluta de un archivo de configuración."""
    return str(get_config_dir() / filename)
