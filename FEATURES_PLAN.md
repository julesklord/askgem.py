# Plan de Implementación de Features - mentask.py

> **Versión:** 0.30.0-dev | **Fecha:** Junio 2026
> **Estado base:** 98 archivos, 11,139 LOC, v0.29.0 en producción
> **Análisis previo:** plan.md (auditoría de calidad)

---

## Resumen de Dependencias entre Features

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Feature 6 (Hook System)      Feature 1 (Streaming)          Feature 10        │
│       │                              │                          (Cost)          │
│       └────────────┬─────────────────┘                                           │
│                    ▼                                                            │
│            ┌──────────────┐                                                     │
│            │  Execution   │                                                     │
│            │   Manager    │                                                     │
│            └──────┬───────┘                                                     │
│                   │                                                              │
│       ┌───────────┼───────────┐                                                 │
│       ▼           ▼           ▼                                                 │
│ Feature 7   Feature 3      Feature 4                                            │
│ (Undo/Redo) (Context Mgmt) (Multi-model)                                       │
│       │           │           │                                                  │
│       └───────────┴───────────┘                                                  │
│                   │                                                              │
│                   ▼                                                              │
│       ┌───────────────────────┐                                                 │
│       │   Core Transaction    │                                                 │
│       │    & State Layer      │                                                 │
│       └──────┬──────┬─────────┘                                                 │
│              │      │                                                             │
│       ┌──────┘      └──────┐                                                     │
│       ▼                      ▼                                                    │
│ Feature 2 (Plugins)     Feature 5 (Branching)                                    │
│       │                      │                                                   │
│       └──────────────────────┘                                                    │
│                              │                                                    │
│       ┌──────────────────────┘                                                    │
│       ▼                                                                           │
│ Feature 8 (Prompt Templates)                                                        │
│       │                                                                           │
│       ▼                                                                           │
│ Feature 9 (TUI)  ←─ consumes todas las features anteriores                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Fase 1: Infraestructura Compartida (Sprint 0)

### 1.1 Sistema de Eventos y Estado (Requisito para casi todas las features)

**Archivos nuevos:**
- `src/mentask/core/events.py` — Bus de eventos centralizado
- `src/mentask/core/state.py` — Snapshots inmutables de estado

**Diseño:**
```python
# events.py
class EventBus:
    """Publicación/suscripción de eventos para desacoplar componentes."""

# state.py
@dataclass(frozen=True)
class AgentState:
    """Snapshot inmutable del estado completo del agente."""
    messages: tuple[Message, ...]
    model_name: str
    total_cost: float
    context_tokens: int
    branch_id: str
    parent_branch_id: str | None
    checkpoint_id: str | None
```

### 1.2 Jerarquía de Excepciones (reutilizada en todas las features)

**Archivo:** `src/mentask/core/exceptions.py`

```python
class MentaskError(Exception): ...
class ConfigError(MentaskError): ...
class SecurityError(MentaskError): ...
class ProviderError(MentaskError): ...
class CompactionError(MentaskError): ...
class HookError(MentaskError): ...
class UndoError(MentaskError): ...
class FallbackError(MentaskError): ...
```

---

## Feature 1: Streaming de Respuestas (Token-level)

### Estado actual: INFRAESTRUCTURA BASE YA EXISTE
- `BaseProvider.generate_stream()` ya devuelve `AsyncGenerator`
- `GeminiProvider`, `OpenAIProvider`, `CLIProvider` implementan streaming
- `stream_response()` en `chat.py` ya consume eventos por chunks

### Gap Analysis
- **Problema:** UI espera a recopilar todo el texto antes de renderizar
- **No hay problema:** El streaming a nivel de provider funciona correctamente
- **Faltante:** Unificación del renderizado en tiempo real (UI consumer)

### Implementación

#### 1.1 TokenBufferRenderer

**Archivo nuevo:** `src/mentask/cli/token_renderer.py`

```python
class StreamingTokenRenderer:
    """Renderiza tokens uno por uno con latencia perceptible pero fluida."""

    def __init__(self, console: Console, min_delay_ms: float = 8):
        self.console = console
        self.min_delay_ms = min_delay_ms
        self._buffer = []
        self._last_flush = time.monotonic()
```

#### 1.2 Cambios necesarios

**`src/mentask/cli/gem_renderer.py`:**
- Modificar `update_stream()` para no insertar texto completo sino append incremental
- `end_stream()` ya funciona como flush final
- Agregar `token_buffer: str = ""` en estado

**`src/mentask/cli/main.py`:**
- `stream_response()` debe pasar cada chunk de texto a UI en tiempo real
- Remover la acumulación en buffer antes de rendenderizar

### Tests

```python
# tests/cli/test_token_streaming.py
async def test_streaming_renders_tokens_in_realtime(): ...
async def test_streaming_handles_tool_interleaving(): ...
async def test_streaming_cancel_on_interrupt(): ...
```

### Estimación: **2 días** (la infraestructura base ya existe)

---

## Feature 2: Marketplace/Registry de Plugins

### Estado actual: Sistema de plugins básico existe
- `plugin_loader.py`: carga dinámica desde `~/.mentask/plugins`
- `ForgePluginTool`: agente puede generar plugins en runtime
- No hay registry remoto ni marketplace

### Diseño: Arquitectura Registry

```
┌─────────────────────────────────────────────────────────────────────────  ┐
│                          MENTASK REGISTRY                                 │
│  (GitHub Releases + JSON Index)                                           │
├─────────────────────────────────────────────────────────────────────────  ┤
│  URL: https://raw.githubusercontent.com/mentask/registry/main/index.json  │
│  Formato:                                                                 │
│    {                                                                      │
│      "plugins": [                                                         │
│        { "name": "docker-compose-gen",                                    │
│          "version": "1.3.0",                                              │
│          "description": "Genera docker-compose.yml desde natural language"│
│          "author": "user/",                                               │
│          "repo": "user/mentask-plugin-docker",                            │
│          "entrypoint": "docker_plugin.py",                                │
│          "tags": ["docker", "devops"],                                    │
│          "sha256": "abc123...",                                           │
│          "requires_mcp": false                                            │
│        }                                                                  │
│      ]                                                                    │
│    }                                                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Componentes

#### 2.1 PluginRegistry (remoto)

**Archivo:** `src/mentask/core/plugin_registry.py`

```python
@dataclass
class PluginEntry:
    name: str
    version: str
    description: str
    author: str
    url: str  # GitHub raw URL
    sha256: str
    tags: list[str]
    requires_mcp: bool

class PluginRegistry:
    """Cliente del registry remoto."""

    INDEX_URL = "https://raw.githubusercontent.com/mentask/registry/main/index.json"
    CACHE_TTL = 86400  # 1 día

    def __init__(self, config_dir: Path):
        self.cache_path = config_dir / "plugin_registry_cache.json"
        self.entries: list[PluginEntry] = []

    async def sync(self) -> None:
        """Descarga índice con cache TTL."""

    def search(self, query: str, tags: list[str] | None = None) -> list[PluginEntry]: ...

    async def install(self, entry: PluginEntry, target_dir: Path) -> Path:
        """Download, verify hash, extract to plugins dir."""
```

#### 2.2 PluginManager (hot-reload mejorado)

**Archivo:** `src/mentask/core/plugin_manager.py`

```python
class PluginManager:
    """Gestiona ciclo de vida de plugins: install, activate, deactivate, uninstall."""

    def __init__(self, registry: PluginRegistry, loader: PluginLoader):
        self.registry = registry
        self.loader = loader
        self._active: dict[str, BaseTool] = {}
        self._watcher: PluginWatcher | None = None

    async def install(self, name: str) -> bool: ...
    async def uninstall(self, name: str) -> bool: ...
    def enable_hot_reload(self, interval: int = 2) -> None: ... setuptools
    def disable_hot_reload(self) -> None: ...
```

#### 2.3 Comandos CLI

```
/plugin search <query>        # Buscar en registry
/plugin install <name>        # Instalar plugin
/plugin uninstall <name>      # Desinstalar
/plugin list                  # Listar activos
/plugin info <name>           # Detalles de un plugin
/plugin update <name>         # Actualizar a última versión
```

### Tests

```python
async def test_registry_sync_caches_correctly(mock_registry_server): ...
async def test_plugin_install_verifies_sha256(): ...
async def test_hot_reload_detects_file_change(tmp_path): ...
```

### Estimación: **5 días** (desde cero, pero infra de plugins existe)

---

## Feature 3: Context Window Management Inteligente

### Estado actual: PARCIALMENTE IMPLEMENTADO
- `ContextCompressor`: compresión de texto y código
- `ContextSnapper`: detección de threshold por modelo
- `ContextCompactor`: construcción de history compactada
- `SessionManager._compact_history()`: compresión per-request
- `AgentOrchestrator._perform_context_snap()`: duplicado de lógica

### Gap Analysis
1. Duplicación: lógica en dos lugares (SessionManager + Orchestrator)
2. No hay compresión semántica: solo elimina comentarios y whitespace
3. No hay tracking de importancia de mensajes (pueden ser todos iguales)
4. No hay intervención proactiva: solo reactiva al acercarse al límite

### Diseño: Context Manager V2

```python
class IntelligentContextManager:
    """
    Gestiona el context window con estrategias:
    - Compresión sintáctica: comentarios, whitespace (EXISTE)
    - Compresión semántica: summarization LLM (EXISTE parcialmente)
    - Eliminación por relevancia: TF-IDF de mensajes (NUEVO)
    - Sliding window dinámico: tokens por turno (NUEVO)
    """

    def __init__(self, model_limit: int, strategy: CompactionStrategy):
        self.limit = model_limit
        self.strategy = strategy
        self.token_estimator = TokenEstimator()
        self.summarizer = SemanticSummarizer()

    async def compact(self, history: list[Message]) -> list[Message]:
        """
        Pipeline de compresión inteligente:
        1. Estimar tokens actuales
        2. Si < 0.7*limit: return sin tocar
        3. Si > 0.7*limit:
           a. Eliminar mensajes SYSTEM redundantes
           b. Comprimir código con ContextCompressor
           c. Summarize grupos de mensajes USER-ASSISTANT
           d. Si sigue > threshold, sliding window
        4. Reconstruir history compactada
        """
```

### 3.1 Centralización (Resolver duplicación)

**Acción:** Eliminar completamente `_compact_history()` de `SessionManager`.
Delegar todo a `ContextCompactor` compartido.

### 3.2 Semantic Summarizer

**Archivo:** `src/mentask/core/semantic_summarizer.py`

```python
class SemanticSummarizer:
    """Resume conversaciones preservando intención y contexto."""

    async def summarize(self, messages: list[Message], max_tokens: int) -> str:
        """Genera resumen corto que capture intención ejecutiva del diálogo."""

    def score_importance(self, message: Message) -> float:
        """TF-IDF + heurísticas: tool_calls > system > user > assistant"""
```

### 3.3 Configuración por modelo

```json
// settings.json
{
  "context_strategy": "adaptive",  // "none", "aggressive", "adaptive"
  "context_token_threshold": 0.7,
  "context_max_sliding_window": 10
}
```

### Tests

```python
def test_compact_does_nothing_below_threshold(): ...
async def test_compact_summarizes_old_messages(): ...
async def test_compact_preserves_recent_context(): ...
async def test_semantic_summary_preserves_tool_intent(): ...
```

### Estimación: **4 días** (20% ya existe, 80% nuevo)

---

## Feature 4: Multi-modelo con Fallback Automático

### Estado actual: PARCIALMENTE IMPLEMENTADO
- `TimeoutRecoveryManager` existe con estrategia de fallback a modelo local (`qwen2.5-7b`)
- No hay failover entre múltiples proveedores cloud
- No hay health check previo a elegir modelo

### Diseño: ProviderPool + Health Monitor

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ProviderPool                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   Gemini     │    │   OpenAI     │    │   Ollama     │               │
│  │  (priority 1)│───▶│  (priority 2)│───▶│  (priority 3)│               │
│  │  health: OK  │    │  health: OK  │    │  health: OK  │               │
│  │  quota: 80%  │    │  quota: 45%  │    │  quota: 100% │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│         │                   │                   │                       │
│         └───────────────────┴───────────────────┘                       │
│                              ▼                                          │
│                    ┌───────────────────┐                                │
│                    │   HealthMonitor   │                                │
│                    │  (background task)  │                              │
│                    └───────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.1 ProviderPool

**Archivo:** `src/mentask/core/provider_pool.py`

```python
@dataclass
class ProviderConfig:
    name: str
    model_name: str
    provider_id: str  # "google", "openai", "anthropic", "ollama"
    api_key_env: str
    priority: int  # Lower = preferred
    max_retries: int = 3
    health_endpoint: str | None = None

class ProviderPool:
    def __init__(self, configs: list[ProviderConfig]):
        self.providers = configs
        self._health: dict[str, ProviderHealth] = {}
        self._lock = asyncio.Lock()

    async def get_healthy_provider(self) -> BaseProvider:
        """Returns highest-priority healthy provider."""

    async def _health_check(self, config: ProviderConfig) -> ProviderHealth: ...

    async def report_failure(self, config: ProviderConfig, error: Exception) -> None: ...

    async def health_monitor_loop(self, interval: int = 60) -> None:
        """Background task checking health periodically."""
```

### 4.2 FailoverStrategy

```python
class FailoverStrategy:
    """Determina cómo reaccionar ante fallo de un provider."""

    async def on_rate_limit(self, provider: BaseProvider) -> BaseProvider:
        """Switch to next provider, cache original for retry."""

    async def on_timeout(self, provider: BaseProvider) -> BaseProvider:
        """Retry same provider with backoff, then switch."""

    async def on_auth_error(self, provider: BaseProvider) -> BaseProvider:
        """Immediately switch, disable provider."""
```

### 4.3 Configuración en settings.json

```json
{
  "providers": [
    {"model": "gemini-2.5-pro", "priority": 1, "max_retries": 3},
    {"model": "openai:gpt-4o", "priority": 2, "max_retries": 2},
    {"model": "ollama:qwen3", "priority": 99, "fallback_only": true}
  ],
  "failover_mode": "automatic",  // "manual", "automatic", "off"
  "health_check_interval": 60
}
```

### Tests

```python
async def test_pool_selects_highest_priority_healthy(): ...
async def test_pool_switches_on_rate_limit(mock_providers): ...
async def test_background_health_check_disables_unhealthy(): ...
async def test_fallback_to_local_on_all_cloud_failure(): ...
```

### Estimación: **5 días**

---

## Feature 5: Sesiones con Branching
 conference proceedings.

### Estado actual: No existe. Solo:
- `HistoryManager`: guarda una secuencia lineal de mensajes por session_id UUID
- No hay concepto de "fork" o "merge"

### Diseño: Modelo de Git (DAG)

```
session-abc-123
├─ turn-1 [system]↵
│  └─ turn-2 [user] "Hola"↵
│     ├─ turn-3 [assistant] "¡Hola! ¿Cómo puedo ayudarte?"↵
│     │  ├─ turn-4 [user] "Refactoriza esto" ← (branch-1, master)
│     │  └─ [branch-2] "Explora alternativas" (fork desde turn-3)
│     │     ├─ turn-4' [assistant] diferente↵
│     │     └─ ...
│     └─ turn-5' (merge opcional desde branch-1 o -2)
```

### 5.1 Estructura de Datos

**Archivo:** `src/mentask/core/branch_model.py`

```python
@dataclass
class Branch:
    branch_id: str
    session_id: str
    parent_turn_id: str | None  # None = root
    turns: list[Turn]  # Linear within this branch

@dataclass
class Turn:
    turn_id: str
    branch_id: str
    sequence: int  # Orden dentro del branch
    messages: list[Message]
    model_used: str
    tokens_used: int
    cost: float
    timestamp: datetime
    tags: list[str]  # Para búsqueda posterior
```

### 5.2 BranchManager

**Archivo:** `src/mentask/core/branch_manager.py`

```python
class BranchManager:
    """Gestiona branching, checkout y merge de sesiones."""

    def __init__(self, history_dir: Path):
        self.branches: dict[str, Branch] = {}  # In-memory cache
        self._db = sqlite3.connect(history_dir / "branches.db")

    def fork(self, from_turn_id: str, branch_name: str | None = None) -> Branch:
        """Crea una nueva rama desde un punto específico."""

    def checkout(self, branch_id: str) -> list[Message]:
        """Reconstruye la historia lineal de un branch para enviar al LLM."""

### Tests

```python
def test_fork_from_turn_creates_isolated_branch(): ...
async def test_checkout_reconstructs_correct_history(): ...
def test_merge_concat_appends_turns(): ...
async def test_diff_shows_divergence_points(): ...
```

### Estimación: **6 días** (feature más compleja, sin base existente)

---

## Feature 6: Hook System Pre/Post Tool

### Estado actual: No existe sistema de hooks
- `ExecutionManager.run_batch()` ejecuta herramientas directamente
- No hay manera de interceptar tool calls sin modificar core
- `build_security_warning()` implementa validación inline (no hook)

### Diseño: Hook Registry + Middleware Pipeline

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        HOOK SYSTEM ARCHITECTURE                             │
│                                                                            │
│   ┌──────────────┐                                                        │
│   │  Tool Call   │                                                        │
│   │   Received   │                                                        │
│   └──────┬───────┘                                                        │
│          │                                                                 │
│          ▼                                                                 │
│   ┌──────────────┐                                                        │
│   │ PRE-HOOKS  │  validate → ask_user → security_check → rate_limit      │
│   │  Pipeline  │  (cada hook puede abortar, modificar, o pasar)         │
│   └──────┬───────┘                                                        │
│          │                                                                 │
│          ▼                                                                 │
│   ┌──────────────┐                                                        │
│   │  Tool.exec() │  ← execute original                                    │
│   │   (unified)  │                                                        │
│   └──────┬───────┘                                                        │
│          │                                                                 │
│          ▼                                                                 │
│   ┌──────────────┐                                                        │
│   │ POST-HOOKS │  audit → lsp_check → format → git_stage → notify       │
│   │  Pipeline  │  (chain of responsibility)                               │
│   └──────┬───────┘                                                        │
│          │                                                                 │
│          ▼                                                                 │
│   ┌──────────────┐                                                        │
│   │    Result    │                                                        │
│   │   Returned   │                                                        │
│   └──────────────┘                                                        │
└──────────────────────────────────────────────────────────────────────────┘
```

### 6.1 HookRegistry

**Archivo:** `src/mentask/core/hooks.py`

```python
from typing import Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

class HookType(str, Enum):
    PRE = "pre"
    POST = "post"

class HookResult(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    MODIFY = "modify"

@dataclass
class ToolContext:
    tool_name: str
    arguments: dict
    tool_call_id: str
    session_id: str
    user_id: str | None = None

@dataclass
class HookOutcome:
    result: HookResult
    modified_arguments: dict | None = None
    error_message: str | None = None

# Type aliases
PreHook = Callable[[ToolContext], Awaitable[HookOutcome]]
PostHook = Callable[[ToolContext, ToolResult], Awaitable[ToolResult]]

class HookRegistry:
    """Central registry for pre/post tool hooks."""

    def __init__(self):
        self._pre_hooks: dict[str, list[PreHook]] = {}   # tool_name -> hooks
        self._post_hooks: dict[str, list[PostHook]] = {}  # tool_name -> hooks
        self._global_pre: list[PreHook] = []
        self._global_post: list[PostHook] = []

    def register_pre(self, hook: PreHook, tool: str = "*") -> None:
        """Register a pre-execution hook. Use '*' for all tools."""

    def register_post(self, hook: PostHook, tool: str = "*") -> None:
        """Register a post-execution hook."""

    def unregister(self, hook_id: str) -> None: ...

    async def run_pre(self, context: ToolContext) -> HookOutcome:
        """Execute all pre-hooks in order."""

    async def run_post(self, context: ToolContext, result: ToolResult) -> ToolResult:
        """Execute all post-hooks in order."""
```

### 6.2 Hooks Built-in

```python
# Security validation hook (migra desde build_security_warning)
security_pre_hook = SecurityValidationHook()

# Audit trail hook
class AuditHook:
    """Logs every tool invocation with full context."""
    async def __call__(self, context: ToolContext, result: Optional[ToolResult] = None):
        pass

# LSP lint hook (migra desde append_lsp_diagnostics)
lint_post_hook = LSPLintHook()

# Git auto-commit hook
class GitAutoStageHook:
    """Automatically stages modified files after write/edit."""
    async def __call__(self, context: ToolContext, result: ToolResult):
        if result.is_error:
            return result
        if context.tool_name in ("write_file", "edit_file"):
            path = context.arguments.get("path")
            if path:
                subprocess.run(["git", "add", path], check=False)
```

### 6.3 Plugin-friendly: API para hooks de usuario

```python
# En plugin_loader.py, permitir:
class MyPlugin(BaseTool):
    def __init__(self):
        self.register_hook(self.on_before_edit, type="pre", tool="edit_file")

    async def on_before_edit(self, context: ToolContext) -> HookOutcome:
        if "production" in str(Path(context.arguments["path"])):
            return HookOutcome.block("Cannot edit production files")
        return HookOutcome.pass_()
```

### Tests

```python
async def test_pre_hook_blocks_tool_execution(): ...
async def test_post_hook_modifies_result(): ...
async def test_global_hook_runs_for_all_tools(): ...
async def test_hook_order_is_respected(): ...
```

### Estimación: **4 días** (requiere refactorización de ExecutionManager)

---

## Feature 7: Undo/Redo de Cambios de Archivos

### Estado actual: PARCIALMENTE IMPLEMENTADO
- `worktree_tools.py`: `enter_worktree`, `exit_worktree` para aislamiento
- No hay stack de undo/redo inline (solo a nivel de git worktree)
- No hay undo por cambio individual, solo por worktree completo

### Diseño: FileChangeStack (patrón Command + Memento)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                      FILE CHANGE STACK                                      │
│                                                                            │
│   ┌───────────────────────────────────────────────────────────────┐     │
│   │ Per-Session Stack (persistente en .mentask/changes/)          │     │
│   │                                                                │     │
│   │  [ undoable ]  push(write_file, /src/app.py)                  │     │
│   │  [ undoable ]  push(edit_file, /src/app.py, old, new)       │     │
│   │  [ undoable ]  push(write_file, /tests/test_app.py)         │     │
│   │  ─────────────────────────────────────────────────────       │     │
│   │  [ redoable ]  (undo de último cambio)                        │     │
│   │                                                                │     │
│   └───────────────────────────────────────────────────────────────┘     │
│                                                                            │
│   Operaciones:                                                            │
│     undo()          → revierte último cambio, mueve a redo_stack     │
│     redo()          → reaplica cambio, mueve de vuelta               │
│     checkpoint()    → marca punto explícito                              │
│     squash(n)       → combina los últimos n cambios en uno            │
│     reset()         → descarta todo redo_stack                         │
└────────────────────────────────────────────────────────────────────────────┘
```

### 7.1 FileChangeTracker

**Archivo:** `src/mentask/core/file_change_stack.py`

```python
@dataclass
class FileChange:
    change_id: str
    tool_name: str
    timestamp: datetime
    path: str
    operation: str  # "write", "edit", "delete", "move"
    before_snapshot: str | None  # contenido anterior (o None si new)
    after_snapshot: str | None   # contenido nuevo
    diff: str  # unified diff
    checksum_before: str | None
    checksum_after: str | None

class FileChangeStack:
    """Stack persistente de cambios por sesión."""

    def __init__(self, session_id: str, base_dir: Path):
        self.session_id = session_id
        self.base_dir = base_dir
        self.undo_stack: list[FileChange] = []
        self.redo_stack: list[FileChange] = []
        self._db = sqlite3.connect(base_dir / "changes.db")

    def push(self, change: FileChange) -> None:
        """Register a new change, clearing redo_stack."""
        self.redo_stack.clear()
        self.undo_stack.append(change)
        self._persist(change)

    def undo(self) -> tuple[bool, str]:
        """Undo last change. Returns (success, message)."""

    def redo(self) -> tuple[bool, str]:
        """Redo last undone change."""

    def squash(self, count: int) -> None:
        """Combine last N changes into a single macro-change."""

    def get_history(self, path: str | None = None) -> list[FileChange]:
        """Get change history, optionally filtered by path."""

    def create_snapshot(self, path: str) -> str:
        """Create a full backup snapshot of a file."""
```

### 7.2 Integración con hooks

```python
# En HookRegistry, registrar automáticamente:
file_change_post_hook = FileChangeTrackingHook(change_stack)
registry.register_post(file_change_post_hook, tool="*")  # All file tools
```

### 7.3 CLI Commands

```
/undo [-n]              # Undo last n changes (default 1)
/redo [-n]              # Redo last n undone changes
/changes list           # Show change history
/changes show <id>      # Show diff of a specific change
/changes squash <n>     # Squash last n changes
/changes reset          # Discard all redo history
```

### Tests

```python
def test_undo_restores_previous_content(tmp_path): ...
def test_redo_reapplies_change_after_undo(): ...
def test_undo_after_new_change_clears_redo(): ...
async def test_checkpoint_persists_across_sessions(): ...
```

### Estimación: **4 días** (se integra con Feature 6 hooks)

---

## Feature 8: Prompt Templates con Variables

### Estado actual: NO EXISTE
- No hay sistema de templates
- `contextual_prompts.py` existe pero es para configuración de contexto (coding, music, etc.)
- Cada turno el usuario escribe el prompt completo

### Diseño: Template Engine con Jinja2

```python
# .mentask/templates/refactor_python.md
---
name: "Refactor Python Code"
tags: ["refactor", "python", "code-quality"]
variables:
  - name: file_path
    description: "Path to the file to refactor"
    required: true
  - name: goal
    description: "Refactoring goal (e.g., 'reduce complexity', 'add type hints')"
    required: true
  - name: max_complexity
    description: "Target cyclomatic complexity"
    default: 10
---

Please refactor the file at {{ file_path }} to achieve: {{ goal }}.

Requirements:
- Keep the {{ max_complexity }} complexity threshold
- Ensure all tests still pass
- Add or update type hints if missing
- Follow PEP 8 style guide

Use the following tools:
1. read_file to load the current content
2. analyze_code for complexity metrics
3. edit_file to apply changes incrementally
4. run_shell_command to run tests after each change
5. commit_changes when done
```

### 8.1 TemplateManager

**Archivo:** `src/mentask/core/template_manager.py`

```python
import jinja2
from pathlib import Path

@dataclass
class PromptTemplate:
    name: str
    content: str
    description: str
    tags: list[str]
    variables: list[TemplateVariable]
    source: Path | str  # local file or remote URL

class TemplateVariable:
    name: str
    description: str
    required: bool = False
    default: str | None = None

class TemplateManager:
    def __init__(self, template_dirs: list[Path]):
        self.template_dirs = template_dirs
        self.templates: dict[str, PromptTemplate] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Scan ~/.mentask/templates/ and .mentask/templates/ for .md templates."""

    def find(self, query: str, tags: list[str] | None = None) -> list[PromptTemplate]: ...

    def render(self, template_name: str, **variables) -> str:
        """Render a template with Jinja2."""

    def render_interactive(self, template_name: str, **defaults) -> str:
        """Prompt user for missing variables, then render."""

    def create_template(self, name: str, content: str, tags: list[str]) -> Path:
        """Save a new template."""

    def builtin_templates(self) -> dict[str, str]:
        """Return default built-in templates."""
        return {
            "refactor": "Refactor Python code...",
            "debug": "Debug and fix errors...",
            "review": "Review code for issues...",
            "test": "Generate comprehensive tests...",
            "doc": "Generate documentation...",
            "optimize": "Optimize performance...",
        }
```

### 8.2 CLI Commands

```
/template list                   # List available templates
/template search <query>         # Search templates by name/tag
/template create <name>          # Create new template interactively
/template edit <name>            # Open editor for template
/template delete <name>          # Remove template
/template info <name>            # Show template details and variables

# Usage:
/refactor --file_path src/app.py --goal "reduce complexity"
# Or interactive:
/refactor                        # Prompt for variables
```

### 8.3 Instalación de dependencias

```bash
pip install Jinja2>=3.0.0
```

### Tests

```python
def test_render_fills_variables(): ...
def test_render_interactive_prompts_for_missing(): ...
def test_builtin_templates_available(): ...
```

### Estimación: **3 días**

---
