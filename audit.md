# Auditoría de Código — mentask.py v0.30.0

> Revisión general de problemas de calidad, seguridad y arquitectura.
> Fecha: 2026-07-07

---

## 🔴 Críticos

### C1. LSP: subprocess y tareas leaked cuando `start()` falla

**Archivos:** `agent/core/lsp_client.py:40-62`, `agent/core/execution.py:30-38`

Cuando `LSPClient.start()` ejecuta `_handshake()` y esta retorna `False` (timeout, respuesta inválida), el método retorna `False` **sin llamar `stop()`**. El subprocess `ruff server`, `_reader_task` y `_heartbeat_task` quedan huérfanos — siguen ejecutándose pero nadie tiene referencia al `LSPClient`.

En `_init_lsp_background()` el objeto `LSPClient` se crea como variable local; si `start()` falla, la variable se descarta y los recursos quedan leaking.

**Impacto:** Acumulación de procesos zombi `ruff server` y tareas asyncio fantasma.

**Solución:** `_init_lsp_background()` debe llamar `lsp.stop()` cuando `start()` retorna `False`. `start()` debe garantizar cleanup en cualquier camino de fallo (try/finally).

---

### C2. `progress_task` leaked en TimeoutError

**Archivo:** `core/execution.py:51-67`

```python
progress_task = asyncio.create_task(update_progress())
try:
    result = await asyncio.wait_for(...)
    progress_task.cancel()          # solo se cancela en éxito
except asyncio.TimeoutError:
    progress.stop()
    return OperationTimeout(...)     # progress_task SIGUE CORRIENDO
```

El task `update_progress` solo se cancela en el path exitoso. En `TimeoutError` (o cualquier otra excepción), la tarea continúa actualizando un `Progress` que ya fue cerrado, potencialmente escribiendo a I/O clausurado.

Adicionalmente, `progress_task.cancel()` no hace `await` — la `CancelledError` no se procesa antes de que el context manager del `Progress` salga.

**Solución:** Asegurar cancelación + `await` con suppress en **todos** los paths, incluyendo `finally`.

---

### C3. ExecutionManager sin config — readonly mode es letra muerta

**Archivo:** `agent/orchestrator.py:38`

```python
self.executor = ExecutionManager(tool_registry)  # config defaults to None
```

Todas las guardas de `readonly_mode` y `edit_mode` en `execution.py` dependen de `self.config`, que siempre es `None`. La rama:
```python
if self.config and self.config.settings.get("readonly_mode", False):
```
nunca se ejecuta. El readonly mode solo existe como instrucción en el system prompt para el LLM, no tiene enforced en la capa de ejecución.

**Solución:** Pasar `config` al `ExecutionManager`, o eliminar el dead code.

---

### C4. `sys.exit(1)` dentro del agente

**Archivo:** `agent/chat.py:712`

```python
sys.exit(1)
```

Usar `sys.exit()` dentro de lógica de agente (no CLI) mata el intérprete sin posibilidad de shutdown graceful, sin limpiar recursos, sin mensaje de error útil.

**Solución:** Lanzar una excepción (`ProviderError`, `ConfigError`) y dejar que el entry point CLI maneje la salida.

---

## 🟠 Altos

### A1. `initialize()` hace I/O innecesario en cada turno

**Archivos:** `agent/core/execution.py:78-92`, `agent/orchestrator.py:263`

`initialize()` se llama desde `orchestrator.py:263` **en cada iteración del loop** del agente. Cada llamada:
- Recarga el archivo de trust desde disco (`asyncio.to_thread`)
- Re-escanea el directorio de plugins, re-importa módulos, re-ejecuta código Python

En una sesión típica con 50+ turnos, esto multiplica innecesariamente el I/O y puede causar efectos secundarios por re-inicialización de plugins.

**Solución:** Cachear trust tras primera carga. Saltar carga de plugins si ya se cargaron (o detectar cambios).

---

### A2. LSP nunca se reintenta tras primer fallo

**Archivo:** `agent/core/execution.py:91-92`

```python
if self.lsp is None and self._lsp_init_task is None:
    self._lsp_init_task = asyncio.create_task(self._init_lsp_background())
```

Si `_init_lsp_background()` falla o retorna temprano, `self._lsp_init_task` queda con un task **completado**. El guard `self._lsp_init_task is None` impide cualquier reintento. La única forma de recuperar es reiniciar el proceso.

**Solución:** Resetear `self._lsp_init_task = None` cuando falla, o implementar backoff controlado.

---

### A3. `__del__` para cleanup de subprocess (no confiable)

**Archivo:** `agent/tools/repl_tool.py:150-152`

```python
def __del__(self):
    if hasattr(self, "sandbox"):
        self.sandbox.close()
```

`__del__` no es determinista — puede no ejecutarse nunca por:
- Referencias circulares
- Excepciones durante interpreter shutdown
- Ciclos de GC no detectados

El sandbox subprocess (`subprocess.Popen`) puede quedar como proceso zombi.

**Solución:** Usar context manager (`__enter__`/`__exit__`) o exponer método `close()` explícito que el llamador debe invocar.

---

### A4. `exec_module()` sin restricción de imports

**Archivo:** `core/plugin_loader.py:60-62, 113`

```python
# Blocked imports check — COMENTADO
# if isinstance(node, (ast.Import, ast.ImportFrom)):
#    ...
spec.loader.exec_module(module)  # ejecución sin restricciones
```

La validación AST existe pero el bloqueo de imports peligrosos está comentado. Un plugin puede importar `os`, `subprocess`, `ctypes`, `socket` y ejecutar código arbitrario en el proceso principal.

**Solución:** Re-implementar la validación de imports bloqueados o descartar el enfoque AST por uno más robusto (subprocess con aislamiento).

---

## 🔶 Medios

| ID  | Problema | Archivo | Líneas |
|-----|----------|---------|--------|
| M1  | `except Exception: pass` — 11 sitios que tragan errores sin log | varios | varios |
| M2  | `input()` sincrónico congela el event loop | `agent/chat.py` | 459, 811 |
| M3  | `Confirm.ask` sincrónico bloquea event loop | `agent/chat.py` | 699 |
| M4  | `client` tipado como `Any` — accesos frágiles a `.model_name`, `.recent_files`, `.provider` | `agent/orchestrator.py` | 29 |
| M5  | `shutil.rmtree` sin validar nombre de carpeta (borra subdirs por mtime) | `core/history_manager.py` | 249 |
| M6  | Regex de branch name permite `/` → path traversal potencial | `tools/worktree_tools.py` | 13 |
| M7  | `check_file()` manda `didOpen` sin `didClose` → acumula documentos abiertos en LSP server | `agent/core/lsp_client.py` | 180-190 |
| M8  | API key en URL query parameter (loggeable, visible en red) | `core/model_discovery.py` | 107-110 |
| M9  | `create_subprocess_exec` sin timeout → proceso externo puede colgar el agente indefinidamente | `agent/core/providers/cli.py` | 279, 311, 536 |
| M10 | `progress_task.cancel()` sin `await` | `core/execution.py` | 54 |
| M11 | `asyncio.create_subprocess_shell()` sin validación interna en `LocalSandbox` | `core/sandbox.py` | 24 |
| M12 | Git flag-injection validation es no-op (`pass`) | `core/subprocess_safety.py` | 72-77 |
| M13 | Sesión reemplazada sin cleanup en local mode | `agent/chat.py` | 127-130 |
| M14 | Shutdown order puede acceder MCP no inicializado | `agent/chat.py` | 676-683 |

---

## 🔸 Bajos

| ID  | Problema | Archivo | Líneas |
|-----|----------|---------|--------|
| L1  | Métodos sin type hints o return type annotations (~20 ocurrencias) | varios | varios |
| L2  | `pass` muerto (sobra de modularización de prompt_toolkit) | `agent/chat.py` | 697 |
| L3  | Conditional vacío para `/theme` | `agent/chat.py` | 538-540 |
| L4  | `_build_turn_config` puede retornar `None`, callers no checkean | `agent/orchestrator.py` | 180-201 |
| L5  | `active_operations` dict value tipado como `Any` | `core/execution.py` | 24 |
| L6  | Código comentado en plugin_loader (3 líneas) | `core/plugin_loader.py` | 60-62 |
| L7  | `global` keyword en `system_tools.py` (aceptable, pero evitable) | `tools/system_tools.py` | 30 |
| L8  | Regex de usuario sin protección ReDoS | `tools/search_tools.py` | 30-31 |
| L9  | `urllib.urlopen` con `# nosec B310` (TLS no verificado) | `core/model_discovery.py` | 110 |
| L10 | `ensure_safe_path()` usa `os.getcwd()` como trust anchor (mutable vía `chdir`) | `core/security.py` | 127 |

---

## Resumen

| Severidad | Conteo |
|-----------|--------|
| 🔴 Críticos | 4 |
| 🟠 Altos | 4 |
| 🔶 Medios | 14 |
| 🔸 Bajos | 10 |

### Recomendación de orden de corrección

1. **C1** (LSP leak) — crítica, afecta el cambio reciente, recursos no liberados
2. **C2** (progress_task leak) — crítica, tarea fantasma en cada operación larga
3. **C3** (executor sin config) — crítica, readonly mode no funciona
4. **A1** (initialize I/O por turno) — alto impacto en performance
5. **A2** (LSP sin retry) — bloquea recuperación del feature
6. **C4** (sys.exit) — alto riesgo en producción
7. **M1** (except pass) — dificulta debugging en producción
8. **A3** (__del__) — subprocess zombi
9. Resto de medios y bajos
