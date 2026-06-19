# Plan de Auditoría y Refactorización - mentask.py

> **Objetivo:** Elevar este proyecto de agente de IA a estándar profesional (producción-grade) sin cambiar funcionalidades, enfocánd="doble" en robustez, seguridad, calidad de código y mantenibilidad.
> > **Estado actual:** 98 archivos Python, 350 tests (348 pasan, 2 skip), 11139 líneas de código, 101 errores de tipo (mypy), 68 errores de linting (ruff), 88 alertas de seguridad (bandit).
> > **Fecha de análisis:** 19 Junio 2026 | **Analista:** Senior DevOps/AI Engineer

---

## 1. INFRAESTRUCTURA Y DEPENDENCIAS

### 1.1 Versionado de dependencias
- **Problema:** `pyproject.toml` tiene rangos muy amplios (`google-genai>=0.2.0`, `rich>=13.0.0`) que permiten versiones incompatibles
- **Impacto:** Google GenAI actualmente 2.9.0 (instalado) rompe compatibilidad con `google.genai` v0.2 que asumía el constructor
- **Acción:** Pin a versiones específicas en `pyproject.toml`: `google-genai>=2.0.0,<3.0.0`, `rich>=14.0.0`, `mcp>=1.0.0,<2.0.0`
- **Prioridad:** CRÍTICA

### 1.2 Dependencias faltantes/fantasmales
- `pyyaml`, `toml` mencionados implícitamente pero no en `pyproject.toml`
- `requests` usado en `conftest.py` pero no listado como dependencia directa
- **Acción:** Auditar todo `import` no estándar y agregar a `[project.dependencies]`

### 1.3 Dependencias opcionales
- `[project.optional-dependencies]` tiene `dev` pero faltan herramientas necesarias: `mypy>=1.0.0`, `bandit>=1.7`, `pip-audit`
- **Acción:** Completar grupo `dev` y agregar grupo `security`

### 1.4 Scripts de utilidad
- Faltan scripts `Makefile` o `tox.ini` simplificados para ejecutar calidad
- **Acción:** Agregar `Makefile` con targets: `lint`, `test`, `typecheck`, `security`, `format`

---

## 2. CALIDAD DE CÓDIGO Y TIPO ESTÁTICO

### 2.1 Errores de tipo (mypy) - 101 errores

#### 2.1.1 `typing.AsyncGenerator` no importado (F821)
- **Ubicación:** `src/mentask/agent/chat.py:336`
- **Problema:** `return AsyncGenerator[AgentEvent, None]` sin importar
- **Fix:** `from collections.abc import AsyncGenerator` al inicio

#### 2.1.2 `Any` no definido en `config_manager.py`
- **Ubicación:** `src/mentask/core/config_manager.py:216`
- **Problema:** `def load_api_key(...) -> Any:` sin `from typing import Any`
- **Fix:** Agregar import faltante

#### 2.1.3 Incompatibilidad de firmas `execute()` en herramientas
- **Ubicación:** `working_memory_tool.py`, `user_tool.py`, `search_tool.py`, `shell_tools.py`, `web_tool.py`, `plan_tool.py`, `delegation_tools.py`, `plugin_tools.py`, `repl_tool.py`
- **Problema:** Todas las subclases sobreescriben `execute` con firmas concretas en lugar de `**kwargs`
- **Fix:** Cambiar `BaseTool.execute` a tipo genérico con `@abstractmethod` o adaptar subclassing

#### 2.1.4 `ToolResult` sin `tool_call_id`
- **Ubicación:** `working_memory_tool.py`, `plan_tool.py`, `delegation_tools.py`
- **Problema:** Constructor `ToolResult(content=...)` sin `tool_call_id` requerido por Pydantic
- **Fix:** O hacerlo `Optional` en schema, o pasar siempre un ID

#### 2.1.5 Incompatibilidad tipos `Message.tool_calls`
- **Ubicación:** `src/mentask/agent/orchestrator.py:322-387`
- **Problema:** Lista de `Message` genérico accede a `msg.tool_calls` que solo existe en `AssistantMessage`
- **Fix:** Usar `isinstance(msg, AssistantMessage)` antes de acceder al atributo

#### 2.1.6 `RAGManager` sin anotaciones
- **Ubicación:** `src/mentask/core/rag_manager.py`
- **Problema:** Atributos `chunks`, `idf`, `chunk_vectors`, `_file_mtimes` sin tipo; variable `doc_frequencies` con tipo incorrecto
- **Fix:** `chunks: list[dict[str, Any]]`, etc.

#### 2.1.7 `FileReadingSession` sin anotaciones críticas
- **Ubicación:** `src/mentask/core/constraints.py`
- **Problema:** `chunks_read` sin tipo, operaciones entre `object` e `int`
- **Fix:** Tipificar correctamente los atributos del dataclass interno

### 2.2 Linting (ruff) - 68 errores
- **F401:** 31 imports no usados (mayor impacto en `chat.py`, `gem_renderer.py`)
- **F821:** 5 nombres no definidos (`AsyncGenerator`, `_logger`)
- **I001:** 9 bloques de imports no ordenados
- **SIM105/108:** Patrones suprimibles de excepciones
- **B904:** `raise` sin `from` en except
- **Acción:** Ejecutar `ruff check --fix` y resolver residuos manualmente

---

## 3. SEGURIDAD - 88 Alertas Bandit

### 3.1 Ejecución de subprocesos sin validación (B404/B603)
- **Ubicación:** `repl_tool.py`, `worktree_tools.py`, `lsp_client.py`
- **Problema:** `subprocess.run([...])` sin validar que los argumentos no vienen de input no confiable
- **Impacto:** Posible ejecución de comandos arbitrarios si el LLM genera argumentos maliciosos
- **Fix:** Crear wrapper `SafeSubprocess` que whitelistee comandos permitidos; validar/escapar todos los args

### 3.2 `urllib.request.urlopen` sin validación de esquemas (B310)
- **Ubicación:** `openai.py:112`, `openai.py:315`
- **Problema:** URLs construídas dinámicamente podrían apuntar a `file://` o `data://`
- **Fix:** Validar esquema HTTPS antes de `urlopen` (ya existe `is_safe_url` en `web_tools.py`, pero no se usa en provider)

### 3.3 `try/except: pass` silenciosos (B110)
- **Ubicación:** `execution.py:210`, `cli.py:501`
- **Problema:** Errores LSP/diagnósticos y parsing JSON silenciados completamente
- **Fix:** Al menos loggear en `DEBUG`, o propagar si es crítico

### 3.4 `try/except: continue` sin manejo (B112)
- **Ubicación:** `cli.py:434`, `openai.py:136`
- **Problema:** Parsing de JSON y chunks fallidos se ignoran silenciosamente
- **Fix:** Contabilizar errores de parsing, aplicar backoff

### 3.5 Generador pseudo-aleatorio no criptográfico (B311)
- **Ubicación:** `gemini.py:161`
- **Problema:** `random.uniform(0, 1)` para jitter en retry
- **Fix:** Usar `secrets.SystemRandom` si es para seguridad; para retry de red es aceptable pero documentar
- **Prioridad:** BAJA (no es vulnerabilidad crítica)

### 3.6 Valores hardcodeados sensibles
- **API keys en texto plano:** ConfigManager permite `settings.get("xxx_api_key")` en archivos locales
- **Endpoint URLs:** `localhost:11434`, `models.dev` en múltiples archivos sin configurabilidad
- **Timeout fijos:** `60`, `300` segundos sin centralización
- **Fix:** Extraer a constantes en módulo `core/constants.py` o usar pydantic-settings con validación

---

## 4. ARQUITECTURA Y DISEÑO

### 4.1 Acoplamiento excesivo `ChatAgent`
- **Problema:** `ChatAgent.__init__` tiene 250+ líneas, inicializa 15+ managers, acopla UI con lógica de negocio
- **Impacto:** Imposible testear unitariamente, difícil de modificar
- **Fix:** Aplicar inyección de dependencias completa dividiendo en:
  - `AgentFactory` (crea todo el grafo de dependencias)
  - `ChatAgent` solo orquesta, no construye

### 4.2 Patrón Singleton en `ModelsHub`
- **Problema:** `_instance = None` patrón clásico no es thread-safe en async, dificulta tests
- **Fix:** Reemplazar con inyección de dependencias o usar `functools.lru_cache` singleton testeable

### 4.3 Acoplamiento UI-Agent en `chat.py`
- **Problema:** `ChatAgent._stream_response` maneja eventos `AgentEvent` y se los pasa a un renderer concreto (`GemStyleRenderer`)
- **Fix:** Definir interfaz `EventSink` protocolo y que `ChatAgent` solo publique a un observer sin conocer la UI

### 4.4 Tratamiento de errores inconsistente
- **Problema:** Múltiples patrones en el codebase:
  - `try/except: pass` en LSP/diagnósticos
  - `except Exception as e: _logger.error(...)` en algunos lugares
  - `except (TimeoutError, asyncio.TimeoutError)` en orchestrator
  - `except json.JSONDecodeError` con mensajes genéricos
- **Fix:** Definir jerarquía de excepciones propia:
  ```python
  class MentaskError(Exception): ...
  class ConfigError(MentaskError): ...
  class SecurityError(MentaskError): ...
  class ProviderError(MentaskError): ...
  ```

### 4.5 Context Snapping / Compaction
- **Problema:** Lógica duplicada entre `SessionManager._compact_history()` y `AgentOrchestrator._perform_context_snap()`
- **Fix:** Centralizar en un único `ContextCompactor` que maneje:
  - Threshold calculation
  - Summary generation
  - History reconstruction
  - File context injection

### 4.6 Manejo de streaming duplicado
- **Problema:** `AgentOrchestrator.run_query()` tiene yield de eventos y también muta `history[]` in-place
- **Impacto:** Race conditions potenciales, difícil de razonar sobre estado
- **Fix:** Patrón de "state machine" con eventos inmutables, o "copy-on-write" para history

---

## 5. HERRAMIENTAS Y TESTS

### 5.1 Cobertura de tests desconocida
- **Problema:** No hay reporte de cobertura configurado
- **Acción:** Agregar `pytest-cov` y target `make coverage`

### 5.2 Tests con mocks frágiles
- **Ubicación:** `tests/agent/test_chat_agent.py`
- **Problema:** Mocking extenso de 5+ dependencias con `MagicMock` anidados
- **Fix:** Usar factory functions y fixtures reusables; considerar `pytest-mock`

### 5.3 Test conecta a Ollama real
- **Problema:** `conftest.py` arranca Ollama como subprocess en tests de sesión
- **Impacto:** Tests lentos, no determinísticos, dependen de infraestructura externa
- **Fix:** Mockear completamente las respuestas de Ollama; usar fixture condicional con `pytest.mark.integration`

### 5.4 Tests de CLI mock incompletos
- **Problema:** `test_cli_main.py` solo prueba `_parse_args()` pero no el flujo de ejecución completo
- **Acción:** Agregar tests con `capsys`, `caplog` o `unittest.mock.patch("builtins.input")`

---

## 6. PERFORMANCE Y RECURSOS

### 6.1 Leaks de recursos async
- **Ubicación:** `MCPManager`, `CLIProvider`
- **Problema:** Context managers (`__aenter__`) guardados manualmente pero `__aexit__` puede fallar
- **Fix:** Usar `async with` pattern siempre que sea posible, o manejar excepciones en shutdown

### 6.2 File descriptors no cerrados
- **Ubicación:** `config_manager.py` (lectura de settings), `history_manager.py`
- **Problema:** Archivos abiertos sin `with` explícito en algunos paths (ya usa `with` en general, pero no es consistente)
- **Acción:** Auditar para asegurar 100% uso de context managers

### 6.3 Indexación RAG sin caché persistente
- **Ubicación:** `rag_manager.py`
- **Problema:** `index_workspace()` recalcula TF-IDF completo cada vez que se invoca `query()` si detecta cambios
- **Fix:** Implementar caché persistente en disco (SQLite o JSON) para workspaces grandes

---

## 7. DOCUMENTACIÓN Y MANTENIMIENTO

### 7.1 Docstrigs inconsistentes
- **Problema:** Algunos módulos tienen Google Style, otros no tienen docstrings, parámetros no documentados
- **Fix:** Estandarizar en Google Style o NumPy Style; integrar en `ruff` con reglas `D`

### 7.2 CHANGELOG desincronizado
- **Problema:** `CHANGELOG.md` es grande (61KB) y observa "hardcoded from current release notes" en `audit_manager.py`
- **Fix:** Implementar generación automática con `git-cliff` o `commitizen`

### 7.3 Falta CONTRIBUTING.md
- **Acción:** Documentar flujo de trabajo, convenciones de commits, guía de estilo

---

## 8. PLAN DE ACCIÓN PRIORIZADO

### Fase 1: Bloqueantes (1-2 días)
1. [ ] Corregir imports rotos (`AsyncGenerator`, `Any`)
2. [ ] Pin versiones de dependencias en `pyproject.toml`
3. [ ] Agregar dependencias faltantes (`pyyaml`, `toml`, `requests`)
4. [ ] Ejecutar `ruff check --fix` y resolver residuos
5. [ ] Crear `Makefile` con targets de calidad

### Fase 2: Seguridad (2-3 días)
1. [ ] Crear `SafeSubprocess` wrapper con whitelist
2. [ ] Validar URLs en `OpenAIProvider` con `is_safe_url`
3. [ ] Eliminar `try/except: pass` silenciosos (log mínimo)
4. [ ] Centralizar constantes sensibles en módulo dedicado

### Fase 3: Tipado y Calidad (2-3 días)
1. [ ] Corregir 101 errores de mypy (fases iterativas)
2. [ ] Agregar `mypy` a dependencias de dev y CI
3. [ ] Refactorizar firmas `execute()` de herramientas
4. [ ] Corregir `ToolResult(tool_call_id)` en todo el codebase

### Fase 4: Arquitectura (3-5 días)
1. [ ] Extraer `ContextCompactor` único
2. [ ] Refactorizar `ChatAgent` con inyección de dependencias
3. [ ] Eliminar Singleton `ModelsHub` (o hacerlo testeable)
4. [ ] Definir jerarquía de excepciones propia

### Fase 5: Testing y CI/CD (2 días)
1. [ ] Configurar `pytest-cov` con umbral de cobertura
2. [ ] Refactorizar mocks en `test_chat_agent.py`
3. [ ] Marcar tests de Ollama como `integration`
4. [ ] Configurar GitHub Actions con lint+type+security

### Fase 6: Performance y Polish (2 días)
1. [ ] Implementar caché RAG persistente
2. [ ] Mejorar manejo de recursos async (MCP, CLI providers)
3. [ ] Documentar con `CONTRIBUTING.md`

---

## 9. MÉTRICAS OBJETIVO

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Tests pasando | 348/348 | 350/350 (añadir 2 tests pendientes) |
| Errores mypy | 101 | 0 |
| Errores ruff | 68 | 0 |
| Alertas bandit (Med+) | 8 | 0 |
| Alertas bandit (Low) | 80 | <30 (solo B404/B603 de librerías necesarias) |
| Cobertura tests | Desconocida | >75% |
| Dependencias desactualizadas | ~18 | 0 críticas |

---

*Documento generado como plan de acción pre-implementación. Ejecutar en orden de prioridad, validando con tests en cada fase.*
