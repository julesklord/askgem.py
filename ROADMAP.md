# askgem — Development Roadmap

> **Last Updated:** April 1, 2026
> **Current Version:** `2.0.0`
> **Maintainer:** [@julesklord](https://github.com/julesklord)
> **Status:** Active Development

This document outlines the comprehensive engineering roadmap for `askgem`, organized into prioritized milestones. Each milestone contains detailed technical specifications, acceptance criteria, and dependency mappings to guide development decisions.

---

## Table of Contents

1. [Current State Assessment](#1-current-state-assessment)
2. [Milestone 1 — Stability & Error Resilience (v2.1)](#milestone-1--stability--error-resilience-v21)
3. [Milestone 2 — Advanced Code Tools (v2.2)](#milestone-2--advanced-code-tools-v22)
4. [Milestone 3 — Web Research Integration (v2.3)](#milestone-3--web-research-integration-v23)
5. [Milestone 4 — Token Economy & Metrics (v2.4)](#milestone-4--token-economy--metrics-v24)
6. [Milestone 5 — LSP Integration (v2.5)](#milestone-5--lsp-integration-v25)
7. [Milestone 6 — Plugin Ecosystem (v3.0)](#milestone-6--plugin-ecosystem-v30)
8. [Technical Debt & Continuous Improvement](#technical-debt--continuous-improvement)
9. [Non-Goals (Explicitly Out of Scope)](#non-goals-explicitly-out-of-scope)

---

## 1. Current State Assessment

### What askgem v2.0 Can Do Today

| Capability | Module | Status |
|---|---|---|
| Interactive multi-turn chat with Gemini models | `engine/query_engine.py` | ✅ Shipped |
| Read files with line range support | `tools/file_tools.py::read_file` | ✅ Shipped |
| Edit files with find-and-replace + `.bkp` backups | `tools/file_tools.py::edit_file` | ✅ Shipped |
| Execute shell commands (PowerShell/bash) with 60s timeout | `tools/system_tools.py::execute_bash` | ✅ Shipped |
| List directory contents | `tools/system_tools.py::list_directory` | ✅ Shipped |
| Human-in-the-loop safety confirmations | `engine/query_engine.py` | ✅ Shipped |
| Model hot-swapping (`/model <name>`) | `engine/query_engine.py::_cmd_model` | ✅ Shipped |
| Rolling window context management | `core/history_manager.py` | ✅ Shipped |
| Session persistence and restore (`/history`) | `core/history_manager.py` | ✅ Shipped |
| OS-level locale auto-detection (8 languages) | `core/i18n.py` + `locales/*.json` | ✅ Shipped |
| Rich TUI with panels, spinners, Markdown streaming | `ui/console.py` + `rich` | ✅ Shipped |
| JSON-based centralized configuration | `core/config_manager.py` | ✅ Shipped |
| Debug logging to `~/.askgem/askgem.log` | `engine/query_engine.py` | ✅ Shipped |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                    main.py                           │
│              (CLI Entry + Welcome Panel)             │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│               engine/query_engine.py                 │
│         (Agentic Loop + Tool Dispatch)               │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Gemini   │  │ History  │  │ Config Manager   │   │
│  │ SDK      │  │ Manager  │  │ (settings.json)  │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
│                                                      │
│  Registered Tools:                                   │
│  ┌────────────┐ ┌────────────┐ ┌────────────────┐   │
│  │read_file   │ │edit_file   │ │list_directory  │   │
│  │execute_bash│ │ (future)   │ │ (future)       │   │
│  └────────────┘ └────────────┘ └────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Known Limitations in v2.0

1. **No retry logic on API errors** — A single `429 Resource Exhausted` or `500 Internal Server Error` from Gemini crashes the current turn with no automatic recovery.
2. **No search capabilities** — The agent cannot search inside files for patterns (grep) or find files by name glob.
3. **No internet access** — The agent cannot look up documentation, APIs, or package versions online.
4. **No cost awareness** — Users have zero visibility into how many tokens each conversation consumes or what it costs.
5. **No `write_file` tool** — Creating a new file requires using `edit_file` with empty `find_text`, which is semantically awkward and error-prone.
6. **Single-file editing only** — Cannot apply multi-file refactors atomically.
7. **No undo mechanism** — `.bkp` files exist but there's no `/undo` command to restore them.

---

## Milestone 1 — Stability & Error Resilience (v2.1)

**Priority:** 🔴 Critical
**Estimated Effort:** 1-2 weeks
**Theme:** Make the existing features bulletproof before adding new ones.

### 1.1 API Error Retry with Exponential Backoff

**Problem:** Currently, a single `google.api_core.exceptions.ResourceExhausted` (HTTP 429) terminates the entire model turn. The user loses their input and must re-type it.

**Solution:** Implement a retry decorator in `engine/query_engine.py::_stream_response` with:
- Maximum 3 retry attempts
- Exponential backoff: 2s → 4s → 8s
- Jitter of ±500ms to avoid thundering herd
- Clear `rich.status.Status` feedback to the user during waits (e.g., "Rate limited, retrying in 4s...")
- Graceful fallback message after all retries exhausted

**Files Modified:**
- `engine/query_engine.py` (retry wrapper around `chat_session.send_message_stream`)
- `locales/*.json` (add `engine.retry`, `engine.retry_exhausted` keys)

**Acceptance Criteria:**
- [ ] A simulated 429 error triggers an automatic retry without user intervention
- [ ] The user sees a spinner with countdown during the backoff
- [ ] After 3 failures, a clean error message appears (not a Python traceback)

### 1.2 Dedicated `write_file` Tool

**Problem:** Creating new files currently requires passing an empty `find_text` to `edit_file`, which is unintuitive and has edge-case bugs when `os.path.dirname()` returns an empty string.

**Solution:** Extract new-file creation into a first-class `write_file(path, content)` tool.

**Files Created:**
- Extend `tools/file_tools.py` with `write_file()` function

**Files Modified:**
- `engine/query_engine.py` (register new tool, add dispatch case)
- `locales/*.json` (add `tool.wants_write` keys)

**Acceptance Criteria:**
- [ ] `write_file("new_folder/new_file.py", "print('hello')")` creates the file and all parent directories
- [ ] Human-in-the-loop confirmation is shown in manual mode
- [ ] Unit test covers creation, overwrite protection, and permission errors

### 1.3 `/undo` Command

**Problem:** Every `edit_file` call creates a `.bkp` backup, but users have no easy way to restore it.

**Solution:** Implement `/undo` slash command that restores the most recent `.bkp` file.

**Files Modified:**
- `engine/query_engine.py` (add `_cmd_undo`, track last edited path)
- `locales/*.json` (add `cmd.desc.undo`, `cmd.undo.success`, `cmd.undo.none` keys)

**Acceptance Criteria:**
- [ ] `/undo` restores the last modified file from its `.bkp` copy
- [ ] If no `.bkp` exists, a clean message is shown
- [ ] The undo action itself creates a recovery point

### 1.4 Graceful Handling of Oversized Context

**Problem:** If the rolling window still exceeds the model's context limit, the SDK throws an opaque `InvalidArgument` error.

**Solution:** Catch `InvalidArgument` in `_stream_response`, automatically truncate the oldest 50% of history, and retry once.

**Files Modified:**
- `engine/query_engine.py`
- `core/history_manager.py` (add `truncate_half()` method)

---

## Milestone 2 — Advanced Code Tools (v2.2)

**Priority:** 🟠 High
**Estimated Effort:** 2-3 weeks
**Theme:** Give the agent the ability to search and navigate codebases like a human developer.

### 2.1 `grep_search` Tool (Pattern Matching)

**Problem:** The agent currently has no way to search for a string across multiple files. If asked "where is the `authenticate` function defined?", it must manually `list_directory` + `read_file` every single file — burning tokens and time.

**Solution:** Implement `grep_search(pattern, path, case_sensitive, is_regex)` that wraps Python's `pathlib.Path.rglob()` + line-by-line regex matching.

**Technical Details:**
- Recursively walk the directory tree, skipping `.git/`, `node_modules/`, `__pycache__/`, `.venv/`
- Return results as `file:line_number: matching_line` (capped at 50 results)
- Support both literal string and regex modes
- Binary file detection via null-byte check in first 8KB

**Files Created:**
- `tools/search_tools.py`

**Files Modified:**
- `engine/query_engine.py` (register tool, add dispatch)

**Acceptance Criteria:**
- [ ] `grep_search("def authenticate", "src/")` returns file paths and line numbers
- [ ] Results are capped at 50 to prevent token overflow
- [ ] Binary files are skipped silently
- [ ] Unit tests cover recursive search, regex mode, empty results

### 2.2 `glob_find` Tool (File Discovery)

**Problem:** The agent cannot find files by name pattern (e.g., "find all `.yaml` files in the project").

**Solution:** Implement `glob_find(pattern, path)` using `pathlib.Path.rglob()`.

**Files Created:**
- Add to `tools/search_tools.py`

**Acceptance Criteria:**
- [ ] `glob_find("*.py", "src/")` returns all Python files
- [ ] Results exclude `.git/`, `node_modules/`, `__pycache__/`

### 2.3 `diff_file` Tool (Change Preview)

**Problem:** The agent applies edits blindly. There's no way for the user to see a unified diff of what changed.

**Solution:** Implement `diff_file(path)` that compares a file against its `.bkp` version using Python's `difflib.unified_diff`.

**Files Created:**
- Add to `tools/file_tools.py`

**Acceptance Criteria:**
- [ ] Shows a colored unified diff in the terminal
- [ ] Returns "No changes detected" if file matches backup
- [ ] Works even if no `.bkp` exists (shows "No backup found")

---

## Milestone 3 — Web Research Integration (v2.3)

**Priority:** 🟡 Medium
**Estimated Effort:** 1-2 weeks
**Theme:** Connect the agent to the live internet for documentation lookups.

### 3.1 `web_search` Tool (Google Custom Search API)

**Problem:** The agent has zero access to external information. When asked about a library it wasn't trained on, it can only hallucinate.

**Solution:** Integrate the [Google Custom Search JSON API](https://developers.google.com/custom-search/v1/overview) as a registered tool.

**Configuration Requirements:**
- `GOOGLE_SEARCH_API_KEY` — stored in `~/.askgem/settings.json` or environment variable
- `GOOGLE_CX_ID` — Programmable Search Engine ID

**Technical Details:**
- HTTP requests via `urllib.request` (zero new dependencies)
- Returns top 5 results: title, URL, snippet
- Rate limit: 100 queries/day on free tier

**Files Created:**
- `tools/web_tools.py`

**Files Modified:**
- `engine/query_engine.py` (register tool, add dispatch, add config prompts)
- `core/config_manager.py` (add search API key fields)
- `locales/*.json` (add `tool.web_search.*` keys)

**Acceptance Criteria:**
- [ ] `web_search("python asyncio tutorial")` returns 5 titled results with URLs
- [ ] Missing API key triggers a friendly setup wizard
- [ ] Rate limit errors are caught and surfaced cleanly
- [ ] No new pip dependencies required

### 3.2 `web_fetch` Tool (Page Content Extraction)

**Problem:** Even with search results, the agent can't read the actual page content.

**Solution:** Implement `web_fetch(url)` that downloads a page and extracts readable text.

**Technical Details:**
- Use `urllib.request.urlopen` with a 10s timeout
- Strip HTML tags using a lightweight regex-based cleaner (avoid `beautifulsoup4` dependency)
- Truncate output to 4000 characters to prevent token explosion
- Support `text/plain`, `text/html`, and `application/json` content types

**Files Created:**
- Add to `tools/web_tools.py`

**Acceptance Criteria:**
- [ ] `web_fetch("https://docs.python.org/3/library/os.html")` returns readable text
- [ ] Binary/media URLs return a clean error message
- [ ] Output is capped at 4000 characters with a truncation notice

---

## Milestone 4 — Token Economy & Metrics (v2.4)

**Priority:** 🟡 Medium
**Estimated Effort:** 1 week
**Theme:** Give users visibility into their API consumption.

### 4.1 Token Counter & Cost Tracker

**Problem:** Users have no idea how many tokens each conversation is consuming or what it costs.

**Solution:** After each model response, extract `usage_metadata` from the Gemini API response and maintain a running tally.

**Technical Details:**
- Read `response.usage_metadata.prompt_token_count` and `candidates_token_count`
- Maintain session totals in `QueryEngine` instance variables
- Display in the TUI footer or via a new `/usage` command
- Cost estimation based on published Gemini pricing (configurable per model)

**Files Created:**
- `core/metrics.py` (TokenTracker class)

**Files Modified:**
- `engine/query_engine.py` (extract metadata after each response)
- `locales/*.json` (add `cmd.usage.*` keys)

**Acceptance Criteria:**
- [ ] `/usage` shows: total input tokens, output tokens, estimated cost
- [ ] Token counts persist per session
- [ ] Cost estimates update when switching models

### 4.2 Session Summary on Exit

**Problem:** When the user exits, there's no summary of what was accomplished.

**Solution:** On exit, show a mini-report: total messages exchanged, tools invoked, files modified, tokens consumed.

**Files Modified:**
- `engine/query_engine.py::start()` (add exit summary panel)

---

## Milestone 5 — LSP Integration (v2.5)

**Priority:** 🔵 Low (High Complexity)
**Estimated Effort:** 3-4 weeks
**Theme:** Give the agent language-aware code intelligence.

### 5.1 LSP Client Bridge

**Problem:** The agent modifies code blindly — it has no way to verify syntax correctness, resolve imports, or check for type errors before submitting a change.

**Solution:** Implement a synchronous LSP client that communicates with local Language Servers via JSON-RPC over stdio.

**Technical Details:**
- Spawn a language server subprocess (e.g., `pyright-langserver --stdio`)
- Implement the LSP initialization handshake (`initialize` → `initialized`)
- Support `textDocument/didOpen`, `textDocument/didChange`, `textDocument/publishDiagnostics`
- Expose as `get_diagnostics(file_path)` tool to the Gemini agent

**Architecture:**
```
askgem QueryEngine
    │
    ├── get_diagnostics("app.py")
    │       │
    │       ▼
    │   LSPClient (JSON-RPC over stdio)
    │       │
    │       ▼
    │   pyright-langserver --stdio
    │       │
    │       ▼
    │   Returns: [{line: 42, message: "Cannot find name 'foo'", severity: "error"}]
    │
    ▼
Agent uses diagnostics to self-correct before proposing edits
```

**Risk Assessment:**
- **High complexity:** JSON-RPC framing (Content-Length headers), async notification handling
- **Mitigation:** Keep it strictly synchronous and read-only (no completions, no refactoring — diagnostics only)
- **Dependency:** Requires the user to have a compatible language server installed

**Files Created:**
- `tools/lsp_tools.py`
- `core/lsp_client.py`

**Acceptance Criteria:**
- [ ] `get_diagnostics("test.py")` returns syntax errors from Pyright
- [ ] Graceful fallback if no language server is installed
- [ ] Timeout protection (5s max per diagnostic request)

---

## Milestone 6 — Plugin Ecosystem (v3.0)

**Priority:** ⚪ Future
**Estimated Effort:** 4-6 weeks
**Theme:** Allow community-contributed tools without modifying core code.

### 6.1 Plugin Loader Architecture

**Problem:** Adding new tools currently requires modifying `query_engine.py` directly. This doesn't scale for community contributions.

**Solution:** Implement a plugin discovery system that loads tools from a `~/.askgem/plugins/` directory.

**Technical Details:**
- Each plugin is a Python file with a `register(engine)` function
- The function receives the engine instance and can call `engine.register_tool(func)`
- Plugins are loaded at startup via `importlib`
- A `plugin.json` manifest declares the plugin name, version, and tool descriptions

**Files Created:**
- `core/plugin_loader.py`

### 6.2 Built-in Plugin: Git Integration

**Problem:** The agent has no native git awareness.

**Solution:** Create a bundled plugin providing `git_status()`, `git_diff()`, `git_log(n)`, and `git_commit(message)` tools.

**Files Created:**
- `plugins/git_tools.py`

---

## Technical Debt & Continuous Improvement

These items should be addressed continuously alongside milestone work:

| Item | Priority | Description |
|---|---|---|
| **Test Coverage** | High | Current: 38 tests covering config, file tools, system tools. Missing: query engine integration tests, i18n tests, history manager edge cases. Target: 80%+ coverage. |
| **Type Hints** | Medium | Add `py.typed` marker and complete `mypy` strict compliance across all modules. |
| **CI/CD Pipeline** | Medium | Set up GitHub Actions workflow: `ruff check` → `pytest` → `python -m build` on every PR. |
| **PyPI Publishing** | Medium | Automate `twine upload` via GitHub Actions on tag push (e.g., `v2.1.0`). |
| **Docstrings** | Low | Ensure every public function has Google-style docstrings with Args/Returns/Raises. |
| **Windows Terminal Encoding** | Low | Handle `cp1252` / `utf-8` mismatches in `execute_bash` output on legacy Windows consoles. |
| **Configuration Validation** | Low | Add JSON Schema validation for `settings.json` to catch corrupted config files early. |

---

## Non-Goals (Explicitly Out of Scope)

The following features are **intentionally excluded** from this roadmap to maintain focus and realistic scope for a solo maintainer:

| Feature | Reason |
|---|---|
| **Multi-agent orchestration** | Requires a full process management layer, IPC, and debugging infrastructure that is impractical for a single developer to maintain reliably. |
| **Voice input/output** | Hardware-dependent, requires microphone access and speech recognition SDKs. |
| **GUI / Electron wrapper** | askgem is a terminal-first tool by design. GUI development is an entirely separate project. |
| **Cross-model support (OpenAI, Anthropic)** | Would fragment the codebase with SDK-specific adapters. askgem is purpose-built for Google Gemini. |
| **Notebook (.ipynb) editing** | Jupyter notebook JSON structure is complex and error-prone. Users should use Jupyter directly. |
| **MCP server hosting** | Acting as an MCP server (not client) requires persistent TCP socket management, auth flows, and schema negotiation beyond current scope. |
| **Real-time collaboration** | Multi-user sessions would require a server component. Out of scope for a CLI tool. |

---

## Version Release Timeline (Estimated)

```
2026-04     v2.0.0  ████████████████  CURRENT RELEASE
2026-05     v2.1.0  ░░░░░░░░          Stability & Error Resilience
2026-06     v2.2.0  ░░░░░░            Advanced Code Tools
2026-07     v2.3.0  ░░░░              Web Research Integration
2026-Q3     v2.4.0  ░░░               Token Economy & Metrics
2026-Q4     v2.5.0  ░░                LSP Integration
2027-Q1     v3.0.0  ░                 Plugin Ecosystem
```

> **Note:** This timeline assumes a single maintainer working part-time. Dates will shift based on community feedback and real-world usage patterns from the v2.0 release.

---

*This roadmap is a living document. It will be updated as priorities shift based on user feedback, bug reports, and community contributions.*
