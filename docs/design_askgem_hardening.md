# Design Doc: AskGem Refactoring & Security Hardening

**Date:** 2025-05-22
**Status:** Proposed
**Author:** Snuggles (AI Agent)

## 1. Introduction

This document outlines the plan to address critical issues in the AskGem repository, including file management fragilities, tool execution problems, async event loop blocks, and security risks in key storage.

## 2. Goals

- Eliminate blocking calls from the async event loop.
- Securely store API keys using system-level credential managers.
- Optimize file operations for large files and memory efficiency.
- Streamline tool registration and dispatching.
- Update documentation to reflect these changes.

## 3. Architecture Changes

### 3.1. Non-Blocking I/O and Execution

- **File Tools:** All file operations in `file_tools.py` will remain synchronous but will be invoked using `asyncio.to_thread` within the `ToolDispatcher`.
- **System Tools:** `execute_bash` will be refactored to use `asyncio.create_subprocess_exec` (or `shell`) to allow non-blocking command execution and real-time output capture (future-proofing).
- **User Interaction:** Blocking calls like `Confirm.ask` will be wrapped in `asyncio.to_thread` to prevent freezing the UI.

### 3.2. Secure Key Storage

- **Implementation:** Integrate the `keyring` library.
- **ConfigManager Update:**
  - `load_api_key`: Check ENV -> `keyring` -> legacy file (with migration warning).
  - `save_api_key`: Save to `keyring`.
  - `save_settings`: Move sensitive keys (Google Search API Key) from `settings.json` to `keyring`.

### 3.3. Efficient File Management

- **Reading:** `read_file` will use a generator-based approach to skip lines and only read the requested range into memory.
- **Writing:** Implement atomic writes (write to temp, then rename) to prevent file corruption.
- **Redundancy:** Consolidate `list_directory` into `file_tools.py`.

### 3.4. Tool Dispatcher Optimization

- Use a registry pattern where tools are mapped to their implementations via a dictionary, reducing the giant `if/elif` block in `_dispatch`.

## 4. Implementation Plan

### Phase 1: Security & Dependencies

1. Update `pyproject.toml` with `keyring`.
2. Refactor `ConfigManager` to use `keyring`.

### Phase 2: Async & Tool Execution

1. Refactor `ToolDispatcher` to use `asyncio.to_thread` and a registry map.
2. Refactor `execute_bash` to use `asyncio.create_subprocess`.

### Phase 3: File Management

1. Refactor `file_tools.py` for streaming reads and atomic writes.
2. Consolidate `list_directory`.

### Phase 4: Documentation & Cleanup

1. Update `README.md`.
2. Update docstrings in modified files.
3. Remove legacy plaintext key files.

## 5. Success Criteria

- No "Event loop is blocked" warnings (if linter/profiler used).
- API keys no longer stored in plaintext in `~/.askgem/`.
- `read_file` handles 100MB+ files without crashing or hanging the agent (within char limits).
- All tests pass.
