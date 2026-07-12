# API / Module Reference

This section details the primary software contracts within mentask, including the core managers and the Orchestration Layer.

## `src/mentask/agent/`

### **Class `AgentOrchestrator`** (`orchestrator.py`)

The central reasoning engine. It coordinates managers to execute the cognitive loop autonomously.

* **Method `run_query(prompt, history)`**: Executes the main *Thinking -> Action -> Observation* cycle with **Stall Detection**.
* **Method `_get_level_instruction(level)`**: Returns dynamic system instructions based on the classified engineering rigor.
* **Method `_perform_context_snap()`**: Summarizes history to stay within token limits.

### **Class `TaskClassifier`** (`core/classifier.py`)

* **Method `classify(prompt)`**: Uses a fast LLM pass to assign an `EngineeringLevel` (L0-L3) to the session.

### **Enum `EngineeringLevel`** (`schema.py`)

Defines the mindset of the orchestrator:

* `L0_INQUIRY`: Pure info, no tools.
* `L1_PRAGMATIC`: Fast execution, shell fallback.
* `L2_STANDARD`: Standard Research-Execute cycle.
* `L3_ARCHITECT`: Maximum rigor, forces formal planning.

### **Class `ChatAgent`** (`chat.py`)

Serves as the high-level CLI agent entry point.

* **Method `start()`**: Initializes the interactive terminal session and launches the Orchestrator loop.

### **Cognitive Managers** (`agent/core/`)

#### **Class `SessionManager`** (`session.py`)

* **`ensure_session(config)`**: Lazy-loads the chat session with retry-resilient generative configurations.

#### **Class `ContextManager`** (`context.py`)

* **`_get_project_blueprint()`**: Performs the recursive project scan on startup.
* **`build_system_instruction()`**: Injects the Blueprint, Memory, and Active Missions into the prompt.

#### **Class `StreamProcessor`** (`stream.py`)

* **`process_async_stream(...)`**: Consumes generators and extracts tool calls mid-flight.

#### **Class `CommandHandler`** (`commands.py`)

* **`execute(user_input)`**: Dispatcher for slash commands via registry lookup.
* **Registry**: Maps `/command` names to async handlers. Includes `/export`, `/git`, `/diff`, `/context`, `/retry`, `/config`, `/colorscheme`, `/theme`, and more.

---

## `src/mentask/core/`

### **Class `TrustManager`** (`trust_manager.py`)

The security sentinel for directory-level authorization.

* **`is_trusted(path)`**: Validates if a path is within the workspace or the whitelist.
* **`add_trust(path)`**, **`remove_trust(path)`**: Manage the permanent trust whitelist.

### **Class `ContextSnapper`** (`compression.py`)

Proactive context compaction based on token thresholds.

* **`should_snap(current_tokens)`**: Returns True if context exceeds threshold.
* **`get_token_status(current_tokens)`**: Returns dict with tokens, limit, percentage, is_dangerous.

### **Class `TimeoutRecoveryManager`** (`retry_strategy.py`)

Handles API timeouts with severity classification and exponential backoff.

* **`handle_timeout(error, provider, elapsed, attempt)`**: Returns recovery strategy dict.
* **`get_metrics()`**: Returns timeout statistics.

### **Module `security.py`**

* **`analyze_command_safety(command)`**: Runs risk analysis returning a categorized `SafetyReport`.
* **`ensure_safe_path(path)`**: Standardizes and validates paths, protecting against directory traversal.

### **Module `paths.py`**

* **`get_working_dir()`**: Automatically detects if a `.mentask/` folder exists in the project root.
* **`get_config_dir()`**: Returns the local workspace directory if available, or falls back to global `~/.mentask`.

---

## `src/mentask/tools/`

**Function `manage_workspace(action)`**
Handles local project initialization and workspace metadata synchronization.

**Function `read_file(path, ...)`**, **`edit_file(path, ...)`**, **`execute_bash(command)`**
Core agentic tools, now strictly gated by `TrustManager` before execution.

**Function `get_git_diff_stat(base_ref)`**
Returns `git diff --stat` output for change summaries.

**Function `diff_file(path, find_text, replace_text)`**
Generates unified diff preview without modifying the file.
