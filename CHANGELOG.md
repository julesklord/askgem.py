# Changelog

All notable changes to askgem are documented here.
Follows [Semantic Versioning](https://semver.org/) and [Keep a Changelog](https://keepachangelog.com/) conventions.

---

## [Unreleased]

---

## [0.8.0] — 2026-04-03

### Fixed
- `edit_file` now rejects ambiguous replacements when `find_text` appears more than once in the target file, returning a descriptive error instead of silently corrupting unintended sections.
- `edit_file` replacement now uses `str.replace(..., 1)` as an additional safeguard even after the uniqueness check passes.
- `read_file` now enforces a 30,000-character safety cap with a truncation notice, preventing context window explosion on large files.
- `_stream_response` inline imports cleaned up — removed stale `asyncio` reference from the synchronous code path; `max_retries` variable restored after accidental removal during refactor.

### Added
- **Autonomous agentic engine** — full migration to `google-genai>=0.2.0` with native multi-turn tool calling support. The agent can now chain multiple tool invocations within a single model turn.
- **`read_file` tool** — reads files with optional `start_line`/`end_line` parameters to prevent token overflow on large codebases.
- **`edit_file` tool** — find-and-replace with automatic `.bkp` backup before every write. Requires `find_text` to be non-empty on existing files.
- **`execute_bash` tool** — runs shell commands with a 60-second hard timeout and full stdout/stderr capture.
- **`list_directory` tool** — returns a formatted directory tree for filesystem navigation.
- **Human-in-the-loop safety** — all destructive actions prompt for `(Y/n)` confirmation in manual mode (default). Auto mode available via `/mode auto`.
- **Exponential backoff retry** — transient API errors (429, 500, 503) trigger up to 3 automatic retries with exponential backoff and jitter.
- **Dual function call detection** — streaming tool call detection uses both the SDK `chunk.function_calls` helper and a `candidate.content.parts` fallback to handle SDK version differences reliably.
- **Internationalization engine** — `core/i18n.py` auto-detects OS locale via `LANG`/`LC_ALL` env vars and `locale.getlocale()`. Falls back to English gracefully.
- **8 supported languages** — English, Español, Français, Português, Deutsch, Italiano, 日本語, 中文 (简体).
- **Session persistence** — `HistoryManager` auto-saves every conversation to `~/.askgem/history/<session_id>.json` after each turn.
- **Rolling context window** — reloaded sessions are trimmed to the most recent 20 messages and 40,000 characters to stay within free-tier TPM limits.
- **`/history` commands** — `list`, `load <id>`, `delete <id>` for full session management.
- **`/model` command** — lists all `generateContent`-capable Gemini models for the current API key; switches model mid-session with history preserved.
- **`/mode` command** — toggles between `manual` and `auto` edit confirmation modes; persisted to `settings.json`.
- **`/clear` command** — resets the context window without ending the session.
- **Rich TUI** — welcome panel on startup showing active model, edit mode, and detected language. Real-time Markdown streaming via `rich.Live`. Spinner feedback during tool execution via `rich.Status`. Styled confirmation prompts via `rich.Confirm`.
- **Debug logging** — silent SDK errors and retry events written to `~/.askgem/askgem.log`.
- **`ConfigManager`** — JSON-based settings persistence at `~/.askgem/settings.json` with safe load/save and API key management.
- **`paths.py`** — centralized cross-platform config directory resolution (`~/.askgem/` on POSIX, `%APPDATA%\askgem` on Windows).

### Changed
- Complete rewrite from PyGemAi v1.x. Legacy features removed: encryption via `cryptography`, rigid theme system, complex security layer.
- Architecture reorganized into `agent/`, `cli/`, `core/`, `tools/`, `locales/` — clean layer separation with no circular dependencies.
- Entry point moved from `main.py` to `askgem.cli.main:run_chatbot` via `pyproject.toml` scripts.
- Packaging migrated from `setup.py` to `pyproject.toml` (setuptools build backend).

### Removed
- `cryptography` dependency — removed encryption layer in favor of a plaintext key file with restricted POSIX permissions (`0600`).
- All v1.x theme and profile management features.

---

## [1.3.0] — 2026-03-29

### Changed
- First modularization pass — split monolithic script into separate modules.
- Migrated packaging from `setup.py` to `pyproject.toml`.

### Fixed
- Eliminated "double printing" bug where streamed text was rendered twice on some terminals.
- Broad exception handling cleanup — removed bare `except:` blocks across the codebase.

---

## [1.2.1] — 2026-03-29

- Minor version corrections and initial `pyproject.toml` packaging setup.

---

## [1.2.0] — Prior

Initial experimental release under the name **PyGemAi**. Included profile management, a theme system, and API key encryption. Deprecated and superseded by the v2.x rewrite.
