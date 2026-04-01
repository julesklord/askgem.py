import os
import subprocess
from typing import List

def listar_directorio(ruta: str = ".") -> str:
    """
    Lista todos los archivos y carpetas dentro de un directorio específico en el sistema del usuario.
    Útil para explorar el entorno de trabajo actual, encontrar código fuerte u otros recursos.
    
    Args:
        ruta: La ruta absoluta o relativa del directorio a listar. Si está vacío usa el directorio actual.
        
    Returns:
        Un string con el listado de elementos encontrados o un mensaje de error si la ruta es inválida.
    """
    try:
        elementos = os.listdir(ruta)
        if not elementos:
            return f"El directorio '{ruta}' está vacío."
        
        listado = [f"Directorio: {ruta}"]
        listado.append("Elementos:")
        for item in sorted(elementos):
            full_path = os.path.join(ruta, item)
            tipo = "📁" if os.path.isdir(full_path) else "📄"
            listado.append(f"- {tipo} {item}")
            
        return "\n".join(listado)
    except FileNotFoundError:
        return f"Error: La ruta '{ruta}' no existe."
    except PermissionError:
        return f"Error: Permiso denegado para leer la ruta '{ruta}'."
    except Exception as e:
        return f"Error inesperado al listar la ruta '{ruta}': {e}"


def ejecutar_bash(comando: str) -> str:
    """
    Ejecuta un comando en la terminal (bash o cmd), captura su salida estándar (stdout) y sus errores (stderr), 
    y los devuelve como texto.
    
    ATENCIÓN: Se debe usar primariamente para ejecución de scripts inofensivos, testings automáticos,
    git status, chequeo de versiones o compilación.
    
    Args:
        comando: El comando exacto a ejecutar en la terminal local del usuario.
        
    Returns:
        El output del comando ejecutado o un mensaje de fallo si el comando no se encuentra o revienta.
    """
    try:
        # shell=True permite ejecución literal (ej. soportando 'Pipes', 'cd')
        resultado = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            check=False # Retornamos código de salida nosotros mismos en vez de crashear Python
        )
        
        salida = ""
        if resultado.stdout:
            salida += f"STDOUT:\n{resultado.stdout}\n"
        if resultado.stderr:
            salida += f"STDERR:\n{resultado.stderr}\n"
            
        if not salida:
            salida = "Comando ejecutado con éxito. (Sin salida en pantalla)"
            
        return salida.strip()
    except Exception as e:
        return f"Error crítico al intentar ejecutar el comando '{comando}': {e}"
