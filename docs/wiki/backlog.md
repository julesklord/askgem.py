# Roadmap MentAsk v0.27.0: The "Reference Synergy" Initiative

## Introduction

Este documento detalla los hallazgos del sondeo exhaustivo realizado en la base de código de referencia (`K:/source/repos/reference_code`). El objetivo es identificar implementaciones de alto impacto que eleven a MentAsk de un agente CLI estándar a un orquestador autónomo de nivel profesional, optimizando la inteligencia, la seguridad y la experiencia de usuario.

---

## 🚀 Top 5 Ported Features (Arquitectura)

### 1. Delegación Agéntica (Sub-agentes)

**Hallazgo:** La implementación de `AgentTool` permite al agente principal "spawnear" sub-agentes especializados con su propio contexto y memoria aislada.
**Acción para MentAsk:** Implementar `SubagentTool`. Permitirá que MentAsk asigne tareas complejas (como "haz un review de seguridad") a un agente hijo, recibiendo solo el resumen final. Esto evita la explosión de tokens en el hilo principal. (READY)

### 2. Memoria Selectiva vía Side-Query

**Hallazgo:** En lugar de cargar todo el historial o archivos de memoria, el código de referencia usa un "sidechain" (una llamada rápida a un modelo ligero) para seleccionar qué archivos de memoria son relevantes para la consulta actual.
**Acción para MentAsk:** Refactorizar `MemoryManager` para incluir un paso de pre-selección inteligente. Esto permitirá tener miles de archivos de "aprendizaje" sin saturar el contexto.

### 3. Aislamiento por Git Worktrees

**Hallazgo:** `EnterWorktreeTool` permite al agente crear un entorno de trabajo temporal y aislado del branch principal para realizar experimentos o refactorizaciones masivas.
**Acción para MentAsk:** Añadir soporte para `git worktree`. El agente podrá "mudarse" a un directorio temporal para arreglar un bug y solo pedirte que hagas merge cuando esté verificado.

### 4. Motor de Ejecución por Lotes (Batch Execution)

**Hallazgo:** El orquestador de referencia permite emitir múltiples llamadas a herramientas en un solo turno y procesarlas de forma asíncrona, inyectando los resultados de golpe.
**Acción para MentAsk:** Evolucionar el `run_query` de `AgentOrchestrator` para que el modelo pueda decir "lee estos 5 archivos" y MentAsk los lea en paralelo antes de la siguiente reflexión.

### 5. Sistema de Verificación (Doctor/Lint)

**Hallazgo:** Un modo "Doctor" (`Doctor.tsx`) que realiza diagnósticos automáticos del entorno (variables de entorno, dependencias, versiones de herramientas).
**Acción para MentAsk:** Implementar el comando `/doctor` que verifique la salud del LSP, la conexión con Ollama/APIs y el estado del workspace.

---

## 🛠️ Toolbox Expansion (Nuevas Herramientas)

| Herramienta | Función | Impacto |
| :--- | :--- | :--- |
| `BriefTool` | Genera resúmenes ejecutivos de sesiones largas. | Ahorro de tokens en re-activación. |
| `NotebookEditTool` | Soporte nativo para editar celdas en archivos `.ipynb`. | Soporte para Data Science. |
| `ScheduleCronTool` | Permite al agente programar tareas recurrentes (ej. "revisa mis commits cada noche"). | Autonomía temporal. |
| `TodoWriteTool` | Mantiene una lista de tareas pendientes dentro del `.mentask/`. | Organización agéntica. |
| `TeleportTool` | Mueve el contexto o archivos específicos entre sesiones. | Continuidad de flujo. |
| `AnalyzeContextTool` | Realiza un sondeo previo de dependencias antes de empezar. | Análisis de impacto. |

---

## 🎨 UI/UX & Refinamientos

- **Headers Inline Inteligentes:** (Ya iniciado) Refinar para que los cambios de estado (thinking, executing) sean menos intrusivos visualmente.
- **Interactive Helpers:** Implementar diálogos de selección múltiple en la terminal (usando `prompt_toolkit` o un adaptador de `ink`) para permisos granulares.
- **Progress Tracking Profundo:** Mostrar exactamente qué capa del modelo está trabajando (thinking vs output) y el tiempo transcurrido por herramienta de forma granular.

---

## 🔒 Seguridad y Estabilidad

- **Validación AST Proactiva:** Portar la lógica de validación de sintaxis antes de permitir un `edit_file` (evita que el agente se rompa a sí mismo).
- **Recuperación de Timeout:** Implementar la lógica de "re-intento con reducción de contexto" si una llamada a la API falla por límite de tiempo (especialmente útil para Ollama).
- **Resolución de Symlinks:** Asegurar que el `TrustManager` no sea engañado por enlaces simbólicos para escapar del workspace.

---

## 📅 Plan de Acción (0.27.0)

1. **Fase 1: El Cerebro.** Implementar `SubagentTool` y el orquestador de delegación.
2. **Fase 2: La Memoria.** Implementar la selección selectiva de archivos de memoria.
3. **Fase 3: El Cuerpo.** Añadir herramientas de Git Worktree y Notebooks.
4. **Fase 4: El Escudo.** Reforzar validaciones AST y seguridad de rutas.

---
*Nota: Se omitieron todas las implementaciones de telemetría propietaria y conexiones a servicios cerrados, enfocándose puramente en lógica agéntica de código abierto y local-friendly.*
