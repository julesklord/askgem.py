# API / Module Reference

This section details the primary software contracts within AskGem.

## `src/askgem/agent/chat.py`

**Class `ChatAgent`**
The primary lifecycle object handling chat orchestration and tool injection bounds.

* **Method `setup_api`**: Determines active API mapping paths. Halts system loop if authorization blocks fail.
* **Method `_stream_response`**: *[Internal]* Manages continuous dual-path function call detection algorithms handling generator parsing.
* **Method `start`**: Initializes the prompt loop and handles exit events cleanly.

## `src/askgem/core/`

**Module `paths.py`**

* **`get_config_dir`**: Computes `~/.askgem` root resolution reliably tracking OS environments.
* **`get_config_path(filename)`**: Safe join paths.
* **`get_history_dir`**: History routing target paths.

**Class `ConfigManager`**

* **Method `save_settings`**, **`load_settings`**: Manage dynamic state blocks serialized to `settings.json`.
* **Method `save_api_key`**: Disk flush logic to fallback target `.gemini_api_key_unencrypted`.

**Class `HistoryManager`**

* **Method `save_session(history_list)`**: Applies mapping blocks to JSON disk representations mapping generative SDK parts.
* **Method `load_session(session_id)`**: Loads and truncates large windows against `MAX_CONTEXT_WINDOW` enforcing maximum message limitations globally.

## `src/askgem/tools/`

**Function `read_file(path, start_line, end_line)`**
Extracts context data locally. Bound dynamically. Explicitly forbids `dict` passing via SDK.

* **Returns**: Plain string output bounded by index locations.

**Function `edit_file(path, find_text, replace_text)`**
Targets explicit blocks.

* **Caution**: The exact matching target enforces exact indentation spacing checks. Creates `.bkp` references.

**Function `execute_bash(command)`**
Asynchronous terminal execution wrapper.

* **Timeout**: Hardcoded 60s max.
* **Windows Subsystems**: Rewrites target endpoints natively to point to `pwsh` arrays mitigating whitespace CLI failures.
