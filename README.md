# askgem.ai

PyGemAi es un potente cliente de línea de comandos (CLI) para interactuar con los modelos de inteligencia artificial Google Gemini. Diseñado para la simplicidad y la eficiencia, ofrece una experiencia de chat rica y personalizable directamente desde tu terminal.

![PyGemAi Logo](docs/PyGemAi.webp)

## ✨ Características Principales

*   **⚡ Arquitectura Modular (NUEVO v1.3.0):** Código reestructurado para máxima estabilidad y facilidad de desarrollo.
*   **🏠 Configuración Centralizada:** Todos tus ajustes y llaves API se guardan en `~/.pygemai/` (Carpeta de usuario).
*   **🔐 Seguridad Reforzada:** Almacenamiento seguro de llaves API con encriptación PBKDF2 + Fernet.
*   **🎨 Temas Personalizables:** Soporte para múltiples esquemas de colores (Cyberpunk, Matrix, Dracula, etc.).
*   **👤 Gestión de Perfiles:** Crea perfiles específicos con diferentes modelos, prompts del sistema y niveles de seguridad.
*   **📚 Historial de Chat:** Guardado automático de conversaciones por modelo.
*   **🌈 Renderizado Markdown:** Visualización fluida de código, listas y formato de texto en el terminal.

## 🚀 Instalación Rápida

### Prerrequisitos
*   Python 3.8 o superior.
*   Una Google API Key (Consíguela en [Google AI Studio](https://aistudio.google.com/)).

### Desde el repositorio
```bash
git clone https://github.com/julesklord/PyGemAi.git
cd PyGemAi
pip install .
```

O para desarrollo:
```bash
pip install -e ".[dev]"
```

## 📖 Uso Básico

Solo escribe el comando principal para iniciar:
```bash
pygemai
```

### Comandos de teclado en el chat:
*   `salir`, `exit`, `quit`: Finaliza la sesión actual.
*   `Ctrl+C`: Interrumpe la generación o sale del programa.

## 🛠️ Desarrollo y Pruebas

Si deseas contribuir o ejecutar las pruebas unitarias:
```bash
# Instalar dependencias de desarrollo
pip install -e ".[dev]"

# Ejecutar tests
pytest
```

## 📝 Licencia
Este proyecto está bajo la licencia **GNU General Public License v3 (GPLv3)**. Consulta el archivo `LICENSE` para más detalles.

---
Hecho con ❤️ por [julesklord](mailto:julioglez.93@gmail.com)
