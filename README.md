# askgem — Autonomous AI Coding Agent for the Terminal

[![Python 3.8+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-green.svg)](LICENSE)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Google%20Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Security Scan](https://github.com/julesklord/askgem.py/actions/workflows/security.yml/badge.svg)](https://github.com/julesklord/askgem.py/actions/workflows/security.yml)
[![CodeQL](https://github.com/julesklord/askgem.py/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/julesklord/askgem.py/actions/workflows/github-code-scanning/codeql)

**askgem** is a lightweight, autonomous coding agent that lives in your terminal.
Powered by Google Gemini, it reads your files, edits your code, runs shell commands,
and navigates your filesystem — all within an interactive session and with
configurable safety guardrails that keep you in control.

No GUI. No cloud sync. No bloat. Just a fast, opinionated CLI agent you can trust
with your codebase.

![askgem terminal session](docs/askgem.webp)

---

## Contents

- [How it works](#how-it-works)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Slash commands](#slash-commands)
- [Safety model](#safety-model)
- [Architecture](#architecture)
- [Development](#development)
- [Internationalization](#internationalization)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## How it works

askgem runs an asynchronous agentic loop backed by the `google-genai` SDK. On each turn:

1. Your message is sent to the selected Gemini model with a set of registered tool definitions.
2. The model reasons about the request and may call one or more tools (read a file,
   run a command, list a directory).
3. askgem intercepts those tool calls via an **Async Dispatcher**, executes them locally (with confirmation in
   manual mode), and feeds results back to the model.
4. The model synthesizes a final response, streamed to your terminal in real-time Markdown.
5. The full conversation is auto-saved to `~/.askgem/history/` after every turn.

This loop repeats until the model stops requesting tools or you exit the session.

---

## Features

### Agentic tool engine

| Tool | Description |
|---|---|
| `list_directory` | Explore filesystem trees |
| `read_file` | Read any file with optional line ranges — 30k char cap prevents token overflow |
| `edit_file` | Find-and-replace with **atomic writing**, uniqueness guard, and automatic `.bkp` backup |
| `execute_bash` | Run shell commands with 60s timeout and full stdout/stderr capture |

### Human-in-the-loop safety

Every destructive action requires explicit `(Y/n)` confirmation by default.
Switch modes anytime mid-session:

- **`/mode manual`** (default) — approve each file edit and shell command
- **`/mode auto`** — trust the agent fully; all actions execute without prompts

### Streaming Markdown UI

Responses stream in real-time via `rich.Live` with syntax-highlighted code blocks,
spinner feedback during tool execution, and styled panels — not a wall of plain text.

### Persistent session history

Every conversation auto-saves to `~/.askgem/history/` as JSON. Reload any past
session with `/history load <id>`. A rolling context window (20 messages / 40k chars)
keeps reloaded sessions within token budget.

### Model hot-swapping

Switch Gemini models mid-conversation with `/model <n>` — chat history preserved.

### Exponential backoff & retry

Transient API errors (429, 500/503) trigger automatic retries with exponential
backoff up to 3 attempts. You see a countdown spinner, not a crash.

### Multi-language interface

The entire UI auto-detects your OS locale and renders in your language.
Override anytime: `LANG=fr_FR askgem`. See [Internationalization](#internationalization).

---
## Installation

### Prerequisites

- **Python 3.8+**
- A **Google API Key** — free at [Google AI Studio](https://aistudio.google.com/)

### From source (recommended for now)

```bash
git clone https://github.com/julesklord/askgem.py
cd askgem.py
pip install -e ".[dev]"
```

### From PyPI

> The PyPI package is being updated to match this release. Until then, install from source.

```bash
pip install askgem  # targeting v0.9.0
```

---

## Configuration

### API key

askgem loads your key from these sources, in order:

1. **Environment variable** — `GOOGLE_API_KEY=your_key askgem`
2. **System Keyring** — Secure storage via `keyring` (recommended)
3. **Saved file** — `~/.askgem/.gemini_api_key_unencrypted` (Legacy fallback)

On first launch without a key, askgem prompts interactively and saves it securely in your system's keyring.

### Settings file

Stored at `~/.askgem/settings.json`:

```json
{
    "model_name": "gemini-2.5-flash",
    "edit_mode": "manual"
}
```

All settings are changeable mid-session via slash commands and persist automatically.

### Configuration paths

| Path | Purpose |
|---|---|
| `~/.askgem/settings.json` | Model name, edit mode, and other preferences |
| `~/.askgem/.gemini_api_key_unencrypted` | Legacy plaintext API key (deprecated) |
| `~/.askgem/history/` | Auto-saved session JSON files |
| `~/.askgem/askgem.log` | Debug log — silent SDK errors and retry events |

> **Security note:** The API key is now stored securely in the system keyring by default.
> Legacy plaintext storage is only supported for backward compatibility and will be
> removed in future versions.

---

## Usage

Launch the agent:

```bash
askgem
```

A welcome panel shows your active model, edit mode, and detected language.
Then just type naturally:

```
You: refactor authenticate() in src/auth.py to use JWT instead of session tokens
You: find all TODO comments in the project and summarize them
You: create tests/test_auth.py with basic unit tests for the auth module
You: what's the biggest file in this repo?
```

The agent plans, uses tools as needed, and streams the response to your terminal.

### Exiting

Type `exit`, `quit`, `q`, or press `Ctrl+C`.

---

## Slash commands

| Command | Description |
|---|---|
| `/help` | Show the full command reference |
| `/model` | List available Gemini models for your API key |
| `/model <n>` | Switch to model `n` from the list (history preserved) |
| `/mode auto` | Execute edits and commands without confirmation |
| `/mode manual` | Require approval before every destructive action (default) |
| `/clear` | Reset the context window — frees tokens without ending the session |
| `/history list` | List all saved sessions |
| `/history load <id>` | Resume a saved session (rolling window applied automatically) |
| `/history delete <id>` | Permanently remove a session from disk |
| `exit` / `quit` / `q` | Exit askgem |
| `Ctrl+C` | Interrupt current generation or force-quit |

---

## Safety model

**In `manual` mode (default):**
- Every `edit_file` shows you exactly what will be replaced before asking `(Y/n)`
- Every `execute_bash` shows the exact command before running it
- No action modifies your filesystem without your approval

**In `auto` mode:**
- Actions execute without prompts
- `edit_file` still creates `.bkp` backups before every change

**Always, regardless of mode (Sandboxed Environment):**
- **Path Traversal Protection:** All file operations are strictly confined to the current working directory to prevent arbitrary file access.
- **Robust Credentials:** API keys are protected with fallback strategies and system keyring isolation.
- **Context Limits:** Tool results are aggressively truncated (e.g., 10k character limit) to prevent context window overflow and infinite loops.
- `edit_file` verifies `find_text` appears exactly once — ambiguous replacements rejected
- `edit_file` uses **atomic writing** (temporary file + rename) to prevent corruption if a failure occurs during save
- Every file edit creates a `.bkp` backup at `<original_path>.bkp`
- `read_file` is capped at 30,000 characters
- Shell commands have a 60-second hard timeout

---
## Architecture

```
askgem.py/
├── src/askgem/
│   ├── __init__.py              # Package version — single source of truth
│   ├── agent/
│   │   └── chat.py              # ChatAgent — agentic loop, tool dispatch, slash commands
│   ├── cli/
│   │   ├── console.py           # Shared Rich console instance
│   │   └── main.py              # Entry point — welcome panel, boots ChatAgent
│   ├── core/
│   │   ├── config_manager.py    # JSON settings persistence, API key load/save
│   │   ├── history_manager.py   # Session serialization, rolling window context
│   │   ├── i18n.py              # Locale auto-detection, translation engine
│   │   └── paths.py             # Cross-platform config/history directory resolution
│   ├── tools/
│   │   ├── file_tools.py        # read_file, edit_file (backup + uniqueness guard)
│   │   └── system_tools.py      # list_directory, execute_bash
│   └── locales/
│       ├── en.json  es.json  fr.json  pt.json
│       └── de.json  it.json  ja.json  zh.json
├── tests/
│   ├── test_config_manager.py
│   ├── test_file_tools.py
│   ├── test_system_tools.py
│   └── diagnostic_usability.py  # Cross-language smoke tests
├── docs/
├── wiki/
├── pyproject.toml
├── CHANGELOG.md
├── ROADMAP.md
└── tox.ini
```

### Data flow

```
User input
    │
    ▼
ChatAgent._stream_response()
    │  sends to Gemini SDK → streams chunks
    │
    ├── chunk.text ──────────────→ rich.Live (real-time Markdown)
    │
    └── chunk.function_calls ───→ _execute_tool()
                │
                ├── list_directory   → directory tree string
                ├── read_file        → file content (line range + 30k char cap)
                ├── edit_file        → uniqueness check → .bkp → write
                └── execute_bash     → subprocess, 60s timeout → stdout/stderr
                        │
                        ▼
                tool result → fed back as function_response
                        │
                        ▼
                recursive _stream_response() → final model answer
```

---

## Development

### Setup

```bash
git clone https://github.com/julesklord/askgem.py
cd askgem.py
pip install -e ".[dev]"
```

### Tests

```bash
pytest tests/                                        # full suite
pytest tests/ --cov=src/askgem --cov-report=term    # with coverage
pytest tests/test_file_tools.py -v                  # single module
```

### Linting

```bash
ruff check src/ tests/          # check
ruff check src/ tests/ --fix    # auto-fix safe violations
```

### Build

```bash
python -m build
twine check dist/*
```

### Adding a new tool

1. Implement the function in `src/askgem/tools/` — Gemini uses the docstring as
   the tool description, so make it precise.
2. Import and add it to `self._tools` in `ChatAgent.__init__`.
3. Add a dispatch case in `ChatAgent._execute_tool()`.
4. Add `(Y/n)` confirmation UX if the tool is destructive (manual mode).
5. Add i18n keys for any new UI strings to all 8 locale files.
6. Write tests in `tests/`.

---

## Internationalization

Auto-detects your OS locale on startup. Detection order:

1. `LANG` or `LC_ALL` environment variables
2. `locale.getlocale()` system call
3. Falls back to English

**Override:**
```bash
LANG=ja_JP askgem    # Japanese UI
LANG=de_DE askgem    # German UI
```

| Code | Language | File |
|---|---|---|
| `en` | English (fallback) | `en.json` |
| `es` | Español | `es.json` |
| `fr` | Français | `fr.json` |
| `pt` | Português | `pt.json` |
| `de` | Deutsch | `de.json` |
| `it` | Italiano | `it.json` |
| `ja` | 日本語 | `ja.json` |
| `zh` | 中文 (简体) | `zh.json` |

**Adding a language:** copy `en.json` → `<lang_code>.json`, translate all values
(keep keys unchanged), run `python tests/diagnostic_usability.py` to verify, submit PR.

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full plan. Summary:

| Version | Theme | Status |
|---|---|---|
| `v0.8.0` | Autonomous agent, i18n, TUI, retry logic | ✅ Current |
| `v0.9.0` | `write_file`, `/undo`, context overflow guard, CI | 🔄 Next |
| `v0.9.5` | `grep_search`, `glob_find`, `diff_file` | 📋 Planned |
| `v1.0.0` | Stable — 70%+ coverage, full docs, PyPI | 📋 Planned |
| `v1.1.0` | Web tools — Google Search, `web_fetch` | 📋 Planned |
| `v1.2.0` | Token tracking, `/usage`, session summary | 📋 Planned |
| `v2.0.0` | LSP diagnostics, plugin ecosystem | 🔵 Future |

---

## Contributing

PRs welcome. For significant changes, open an issue first to discuss scope.

**Checklist before submitting:**
- [ ] `ruff check src/ tests/` passes
- [ ] `pytest tests/` passes
- [ ] New public functions have complete Google-style docstrings
- [ ] New UI strings added to all 8 locale files
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`

---

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE) for full terms.

Free to use, modify, and distribute. Derivative works must also be GPL-licensed
and open source.

---

Built by [julesklord](https://github.com/julesklord).
