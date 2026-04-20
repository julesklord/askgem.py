# AskGem v0.17.0 — "Shai-Hulud" 🐛

El ciclo de lanzamiento v0.17.0, denominado **"Shai-Hulud"**, marca una evolución crítica en la capacidad de observación y respuesta del agente, introduciendo una ejecución de comandos "viva" y una navegación de artefactos mucho más profunda y accesible.

### 1. Real-time Shell Streaming (Live Container)
Se ha refactorizado completamente el motor de ejecución de comandos. Ahora, los procesos de shell (PowerShell, Bash, Zsh) se ejecutan en un **contenedor visual dinámico**. 
- **Feedback inmediato**: Ya no hay esperas a ciegas; el output fluye en tiempo real.
- **Gestión de Ciclo de Vida**: Implementación de un sistema de monitoreo que evita procesos "stuck" y asegura que no queden procesos huérfanos en el sistema.

### 2. Navegación de Artefactos (Expand/Collapse)
Inspirado en los flujos de trabajo de ingeniería de alto nivel, v0.17.0 introduce el binding **`Ctrl+O`** para la expansión de artefactos.
- **Navegación con Tab**: Permite moverse entre los diferentes bloques de salida de las herramientas.
- **Expansión bajo demanda**: Los resultados extensos de herramientas (como listados de directorios o logs de tests) se muestran contraídos por defecto y se expanden instantáneamente con una combinación de teclas, manteniendo la terminal limpia y legible.

### 3. Seguridad Refinada y UX Fluida
Se ha optimizado la capa de seguridad para distinguir entre comandos de "solo lectura" o informativos y acciones destructivas.
- **Auto-ejecución de comandos SAFE**: Comandos como `ls`, `git status` o `echo` ahora se ejecutan sin pedir confirmación, incluso en directorios no marcados como de confianza, agilizando enormemente el flujo de trabajo inicial.
- **Análisis de Riesgo Proactivo**: El sistema sigue interceptando cualquier pipe (`|`) o redirección (`>`) sospechosa para mantener la integridad del sistema.

### 4. Estabilización de la Arquitectura Modular
Bajo el capó, se han resuelto múltiples regresiones técnicas para asegurar la robustez de la versión:
- **Corrección de BOM**: Eliminación de caracteres invisibles que causaban errores de sintaxis en entornos Windows.
- **Modularización de LSP**: El cliente LSP ahora reside correctamente dentro del `ExecutionManager`, permitiendo diagnósticos más rápidos y precisos durante la edición de archivos.
- **Persistencia Mejorada**: El `HistoryManager` y el `TrustManager` han sido actualizados para manejar estados asíncronos de forma más eficiente.

---
**"El que controla el streaming, controla el universo."**
