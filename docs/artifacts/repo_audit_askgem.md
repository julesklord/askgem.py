# Repository Audit: askgem.py

## 1. Discovery Phase
**Autonomous AI Coding Agent powerd by Google Gemini.**

- **Entry Point**: `src/askgem/cli/main.py:run_chatbot`
- **Manifest**: `pyproject.toml`
- **Config**: `~/.askgem/settings.json`, System Keyring.
- **CI/CD**: GitHub Actions (`.github/workflows/deploy.yml`)
- **Test Suite**: Pytest (located in `tests/`)

---

## 2. Dependency Map
| Dependency | Category | Usage |
|---|---|---|
| `google-genai` | Core | Primary SDK for Gemini 2.0+ models |
| `rich` | Core | Terminal rendering, panels, and streaming Markdown |
| `textual` | Core | TUI Dashboard engine |
| `keyring` | Core | Secure API Key and secret storage |
| `pytest` | Dev | Unit and integration testing |
| `ruff` | Dev | Linting and code formatting |

> [!NOTE]
> No critical version lags or unused core dependencies were detected.

---

## 3. Architecture & Logic

### 3.1 Program Flow
1. **Bootstrap**: `main.py` loads settings and initializes `ChatAgent`.
2. **Setup**: API Key validation via `ConfigManager` (Keyring support).
3. **Session**: `ChatAgent` starts an `AsyncClient` session.
4. **Loop**: User input -> Gemini reasoning -> Tool Dispatch -> Model Feedback.
5. **Persistence**: Auto-saves JSON history; updates `memory.md` and `heartbeat.md`.

### 3.2 Module Map
- `src/askgem/agent/` : Core "Brain" (ChatAgent, ToolDispatcher).
- `src/askgem/cli/` : "Face" (Rich Console, Textual Dashboard).
- `src/askgem/core/` : "Senses/Memory" (Config, History, i18n, Paths).
- `src/askgem/tools/` : "Hands" (File system, Bash, Web, Memory tools).

### 3.3 Data Flow
- **Inputs**: CLI Args, Stdin, `.env`, Keyring.
- **Outputs**: Stdout (Rich), File Edits (with atomic backups), JSON History.
- **State**: Centralized in `~/.askgem/` for cross-platform consistency.

---

## 4. Risk & Quality Assessment

### 4.1 Quality Signals
- **Error Handling**: **GOOD**. Implements exponential backoff and granular `try/except` for I/O.
- **Security**: **GOOD**. CONFIRMED manual mode defaults and path traversal guards.
- **Testability**: **ACCEPTABLE**. Good structure, though UI-heavy components need more mock-based tests.

### 4.2 Structural Risks
> [!WARNING]
> **Tool Confirmation Coupling**: The logic for confirming destructive actions (Delete/Edit) is currently inside `ToolDispatcher._dispatch`. This makes the dispatcher aware of UI concerns (Rich console).

---

## 5. Final Report Summary

**Project**: askgem.py (CLI Agent)
**Overall Health**: **HEALTHY**

### Top 3 Strengths
1. **Security-First**: Keyring integration and mandatory confirmation.
2. **Cognitive Features**: Context summarization and persistent "mission" tracking.
3. **UX**: Multi-language support and real-time streaming Markdown.

### Top 3 Risks
1. [SEVERITY: MED] **UI/Logic Coupling** in the Tool Dispatcher.
2. [SEVERITY: LOW] **Cost/Token Sensitivity** due to high summarization threshold.
3. [SEVERITY: LOW] **System Complexity** as the TUI (Textual) and CLI (Rich) modes evolve separately.

### Recommended Next Steps
1. **LSP Diagnostics**: Integrate syntax checking into the `edit_file` tool.
2. **Async Refactor**: Decouple Tool confirmation from the dispatcher using an event-based approach.
3. **History Cleanup**: Implement a cleanup tool for old session files.
