# API / Module Reference

This section details the primary software contracts within mentask, including the core managers and the new Orchestration Layer introduced in **v0.11.0**.

## `src/mentask/agent/`

### **Class `AgentOrchestrator`** (`orchestrator.py`) [v0.11.0]

The central reasoning engine. It coordinates managers to execute the cognitive loop autonomously.

* **Method `run_thought_loop(prompt)`**: Executes the main *Thinking -> Action -> Observation* cycle.
* **Method `process_tool_calls(calls)`**: Dispatches tools while enforcing security and trust checks.
* **Method `setup()`**: Initializes all cognitive managers (Session, Context, Simulation).

### **Class `ChatAgent`** (`chat.py`)

Serves as the high-level CLI agent entry point.

* **Method `start()`**: Initializes the interactive terminal session and launches the Orchestrator loop.

### **Cognitive Managers** (`agent/core/`)

#### **Class `SessionManager`** (`session.py`)

* **`ensure_session(config)`**: Lazy-loads the chat session with retry-resilient generative configurations.

#### **Class `ContextManager`** (`context.py`) [v0.11.0 Enhanced]

* **`_get_project_blueprint()`**: Performs the recursive project scan on startup.
* **`build_system_instruction()`**: Injects the Blueprint, Memory, and Active Missions into the prompt.

#### **Class `StreamProcessor`** (`stream.py`)

* **`process_async_stream(...)`**: Consumes generators and extracts tool calls mid-flight.

#### **Class `CommandHandler`** (`commands.py`)

* **`handle_command(cmd_text)`**: Dispatcher for slash commands including the new `/trust` system.

---

## `src/mentask/core/`

### **Class `TrustManager`** (`trust_manager.py`) [New in v0.11.0]

The security centinel for directory-level authorization.

* **`is_trusted(path)`**: Validates if a path is within the workspace or the whitelist.
* **`add_trust(path)`**, **`remove_trust(path)`**: Manage the permanent trust whitelist.

### **Module `security.py`** [v0.11.0 Hardened]

* **`analyze_command_safety(command)`**: Runs risk analysis returning a categorized `SafetyReport`.
* **`ensure_safe_path(path)`**: Standardizes and validates paths, protecting against drive-letter escapes on Windows.

### **Module `paths.py`** [v0.11.0 Workspace Aware]

* **`get_working_dir()`**: Automatically detects if a `.mentask/` folder exists in the project root.
* **`get_config_dir()`**: Returns the local workspace directory if available, or falls back to global `~/.mentask`.

---

## `src/mentask/tools/`

**Function `manage_workspace(action)`** [New in v0.11.0]
Handles local project initialization and workspace metadata synchronization.

**Function `read_file(path, ...)`**, **`edit_file(path, ...)`**, **`execute_bash(command)`**
Core agentic tools, now strictly gated by `TrustManager` before execution.
