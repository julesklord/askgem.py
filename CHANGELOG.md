# Changelog - PyGemAi

## [1.3.0] - 2026-03-29

### Auditoria Senior y Refactorización
- **Arquitectura Modular:** El proyecto ha sido completamente refactorizado en módulos especializados (`ui`, `security`, `profiles`, etc.) para mejorar la mantenibilidad.
- **Configuración Centralizada:** Traslado de archivos de configuración (.json, api keys) a la carpeta de usuario `~/.pygemai/`.
- **Corrección de UX:** Eliminado el bug de "doble impresión" en el chat. La respuesta ahora se renderiza de forma completa y formateada tras la generación.
- **Seguridad:** Mejora en el manejo de API Keys y encriptación.

### Mejoras Técnicas
- **Dependencias Actualizadas:** `cryptography` actualizado a `^46.0.0` y `google-generativeai` a `^0.8.0`.
- **Calidad de Código:** Reducción de bloques `except Exception` amplios en favor de capturas de errores específicos.
- **Infraestructura de Pruebas:** Implementación inicial de suite de pruebas con `pytest` cubriendo lógica de seguridad y utilidades.
- **Modernización:** Eliminación de `setup.py` en favor de `pyproject.toml`.

### [1.2.1] - 2026-03-29
- Correcciones menores de versión.

### [1.2.0] - Antes
- Versión inicial con gestión de perfiles y temas.
