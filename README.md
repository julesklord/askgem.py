# askgem — Autonomous AI Coding Agent for the Terminal

[![Python 3.8+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-green.svg)](LICENSE) [![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Google%20Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev/) [![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff) [![Security Scan](https://github.com/julesklord/askgem.py/actions/workflows/security.yml/badge.svg)](https://github.com/julesklord/askgem.py/actions/workflows/security.yml) [![CD - Release](https://github.com/julesklord/askgem.py/actions/workflows/release.yml/badge.svg)](https://github.com/julesklord/askgem.py/actions/workflows/release.yml)

**askgem** is a professional, autonomous coding agent that lives in your terminal.
Powered by Google Gemini, it reads your files, edits your code, runs shell commands,
and navigates your filesystem — all within an interactive session and with
hardened safety guardrails that keep you in control.

No GUI. No cloud sync. No bloat. Just a fast, opinionated CLI agent you can trust
with your codebase.

![askgem terminal session](docs/assets/banner.png)

---

## Contents

- [How it works](#how-it-works)
- [Features](#features)
- [New in v0.10.0: Modular Architecture](#new-in-v0100-modular-architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Slash commands](#slash-commands)
- [Safety model](#safety-model)
- [Architecture](#architecture)
- [Development & Simulation](#development--simulation)
- [Internationalization](#internationalization)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## How it works

askgem runs an asynchronous agentic loop powered by the `google-genai` SDK and a modular manager-based core. On each turn:

1. Your message is sent to the selected Gemini model with a set of dynamic system instructions assembled by the **ContextManager**.
2. The model reasons about the request and may call one or more tools (read a file,
   run a command, list a directory).
3. askgem intercepts those tool calls via a **ToolDispatcher**, executes them locally (subject to **Security Layer** risk analysis), and feeds results back to the model.
4. The **StreamProcessor** handles the generator stream, updating the UI in real-time and extracting function calls mid-flight.
5. The model synthesizes a final response, streamed to your terminal in real-time Markdown.
6. The full conversation is auto-saved to `~/.askgem/history/` after every turn by the **HistoryManager**.

This loop repeats until the model stops requesting tools or you exit the session.

---

## Features

### Agentic tool engine

| Tool | Description |
|---|---|
| `list_directory` | Explore filesystem trees with depth control |
| `read_file` | Read any file with optional line ranges — 30k char cap prevents token overflow |
| `edit_file` | Find-and-replace with **atomic writing**, uniqueness guard, and automatic `.bkp` backup |
| `execute_bash` | Run shell commands with 60s timeout and full **Risk Analysis** |
| `manage_memory` | Save important project facts to `memory.md` for long-term recall |
| `manage_mission` | Track complex goals and sub-tasks via `heartbeat.md` mission control |

### Human-in-the-loop safety

Every destructive action is categorized by risk level (`SAFE`, `NOTICE`, `WARNING`, `DANGEROUS`).
Switch modes anytime mid-session:

- **`/mode manual`** (default) — approve each file edit and shell command.
- **`/mode auto`** — trust the agent fully; all actions execute without prompts.

### Modern TUI Dashboard (Push-Layout)

A stable, high-performance interface built with the `Textual` framework, optimized for Windows:
- Real-time syntax-highlighted Markdown streaming.
- Reactive Sidebar showing live model context, current mission, and token stats.
- Command Palette with autocomplete suggestions for slash commands.
- Hidden output pane (F12) for detailed tool execution logs and debug info.

### Persistent session history

Every conversation auto-saves to `~/.askgem/history/` as JSON. Reload any past
session with `/history load <id>`. A rolling context window and proactive summarization
keep reloaded sessions within token budget.

---

## New in v0.10.0: Modular Architecture

The monolithic core has been refactored into specialized managers to improve stability and testability:

### 1. SessionManager
Handles the entire lifecycle of the Gemini API connection. It manages client initialization, authentication via system keyring, and implements a robust **exponential backoff retry** strategy for transient errors (429, 500, 503).

### 2. ContextManager
The "brain" of the state layer. It dynamically assembles the system prompt by combining OS metadata, Persistent Memory, and Active Missions. It also monitors history length and triggers **Proactive Summarization** when token limits are approached, compressing early turns without losing technical context.

### 3. StreamProcessor
A low-level async handler that consumes chunks from the Gemini SDK. It performs dual-path tool detection (SDK property + raw part traversal) to ensure reliable tool extraction regardless of streaming variations.

### 4. CommandHandler
A centralized dispatcher for slash commands. It allows AskGem to be configured mid-session (switching models, changing safety modes, or wiping context) without disrupting the conversation flow.

### 5. SimulationManager
Introduces a deterministic execution layer. It can **record** real API interactions into JSON transcripts and **playback** them during testing, allowing for 100% reliable CI/CD verification of complex agentic loops.

---
## Installation

### Prerequisites

- **Python 3.8 to 3.14** (v0.10.0 adds support for Python 3.14).
- A **Google API Key** — free at [Google AI Studio](https://aistudio.google.dev/).

### From source (recommended)

```bash
git clone https://github.com/julesklord/askgem.py
cd askgem.py
python -m venv venv
# On Windows: venv\Scripts\activate
source venv/bin/activate
pip install -e ".[dev]"
```

---

## Configuration

### API key (Standardized)

askgem loads your key from these sources, in order:

1. **Environment variable** — `GEMINI_API_KEY=your_key askgem` (Preferred)
2. **System Keyring** — Secure storage via Windows Credential Manager or macOS Keychain (Recommended).
3. **Saved file** — `~/.askgem/settings.json` (Local fallback).

On first launch without a key, askgem prompts interactively and saves it securely in your system's keyring.

### Settings file

Stored at `~/.askgem/settings.json` (POSIX) or `%APPDATA%\askgem\settings.json` (Windows):

```json
{
    "model_name": "gemini-1.5-flash",
    "edit_mode": "manual"
}
```

### Configuration paths

| Path | Purpose |
|---|---|
| `~/.askgem/settings.json` | Model name, edit mode, and user preferences |
| `~/.askgem/history/` | Auto-saved session JSON files |
| `~/.askgem/askgem.log` | Debug log — tool execution events and retry details |

---

## Usage

Launch the agent:

```bash
askgem
```

### Common Workflows

- **Context Analysis:** "Read my `pyproject.toml` and explain the dependencies."
- **Code Generation:** "Create a `src/utils.py` file with a function to calculate SHA256 hashes."
- **Refactoring:** "Refactor `authenticate()` in `src/auth.py` to use JWT instead of sessions."
- **Exploration:** "Find all TODO comments in the project and group them by file."

### Exiting

Type `exit`, `quit`, `q`, or press `Ctrl+C`.

---

## Slash commands

| Command | Description |
|---|---|
| `/help` | Show the full command reference and examples |
| `/model <name>` | Switch Gemini models mid-conversation (history preserved) |
| `/mode [auto/manual]` | Toggle between approving actions or automatic execution |
| `/clear` | Reset the context window to free up tokens without ending session |
| `/usage` | **[v0.10.0]** Show detailed token consumption and estimated USD cost |
| `/stats` | **[v0.10.0]** Summary of session accomplishments (messages, tools, files) |
| `/stop` | **[v0.10.0]** Interrupt the current generation immediately |
| `/reset` | **[v0.10.0]** Restart the entire session and reset all counters |
| `/history [list/load/delete]` | Manage saved conversation sessions |

---

## Safety model

**Always, regardless of mode (Sandboxed Environment):**

- **Risk Analysis Engine:** Powered by `core/security.py`, every command is categorized:
    - `SAFE`: Informative commands (ls, git status).
    - `NOTICE`: Standard operations.
    - `WARNING`: High-risk patterns (sudo, sensitive file access).
    - `DANGEROUS`: Critical risk (rm -rf, fork bombs, world-writable chmod).
- **Path Traversal Protection:** All file operations are strictly confined to the current working directory.
- **Atomic Writing:** `edit_file` uses a temporary file + rename strategy to prevent corruption.
- **Automatic Backups:** Every file modification creates a `.bkp` backup at `<path>.bkp`.
- **Context Limit Protection:** Tool results are automatically truncated to prevent context window explosion.
- **Hard Timeouts:** Shell commands have a strict 60-second execution limit.

---
## Architecture

```
askgem.py/
├── src/askgem/
│   ├── __init__.py              # Single source of truth for version (0.10.0)
│   ├── agent/
│   │   ├── chat.py              # ChatAgent — The central orchestrator
│   │   └── core/                # Cognitive Managers (v0.10.0)
│   │       ├── session.py       # API lifecycle and Exponential Backoff
│   │       ├── context.py       # Prompt assembly and Proactive Summarization
│   │       ├── stream.py        # Async generator handling and Tool extraction
│   │       ├── commands.py      # Slash command dispatcher
│   │       └── simulation.py    # Deterministic recording/playback engine
│   ├── cli/
│   │   ├── dashboard.py         # Textual TUI Dashboard (Push-Layout)
│   │   └── ui_adapters.py       # TUI/Rich compatibility layer
│   ├── core/
│   │   ├── security.py          # Hardened safety engine
│   │   ├── config_manager.py    # Keyring integration and settings persistence
│   │   ├── history_manager.py   # Context serialization and rolling windows
│   │   ├── i18n.py              # Locale auto-detection engine
│   │   ├── metrics.py           # Real-time Token tracking and costing
│   │   └── paths.py             # OS-agnostic path resolution
│   ├── tools/                   # Atomic agentic tools
│   └── locales/                 # i18n JSON data (8 languages supported)
├── tests/                       # 39+ reliable unit and integration tests
├── scripts/                     # Maintenance and diagnostic utilities
├── docs/                        # Rich documentation and assets
└── pyproject.toml
```

---

## Development & Simulation

### Setup

```bash
git clone https://github.com/julesklord/askgem.py
cd askgem.py
pip install -e ".[dev]"
```

### Reliable Testing Protocol

AskGem v0.10.0 introduces a **Simulation Layer**. You can record agent turns and play them back deterministically:

1. **Record:** Set `SIMULATION_MODE=record` to capture interactions.
2. **Playback:** Run `pytest tests/integration/test_full_agent_loop.py` to verify the logic against the recorded transcript without hitting the real API.

### Tests & Linting

```bash
pytest tests/                   # full reliable suite (39 tests)
ruff check src/ tests/ --fix    # auto-fix linting violations
```

---

## Internationalization

AskGem is **English-First** at the SDK/System level for maximum model reliability, but the entire user interface supports 8 languages:

| Code | Language | File |
|---|---|---|
| `en` | English (Standard) | `en.json` |
| `es` | Español | `es.json` |
| `fr` | Français | `fr.json` |
| `pt` | Português | `pt.json` |
| `de` | Deutsch | `de.json` |
| `it` | Italiano | `it.json` |
| `ja` | 日本語 | `ja.json` |
| `zh` | 中文 (简体) | `zh.json` |

---

## Roadmap

| Version | Theme | Status |
|---|---|---|
| `v0.8.0` | Autonomous agent, i18n, TUI, retry logic | ✅ Done |
| `v0.9.0` | Security hardening, context overflow guard | ✅ Done |
| `v0.10.0`| **Modular core, Stable TUI, Simulation, CD** | ✅ Current |
| `v1.0.0` | Stable Release — Full docs, PyPI publication | 📋 Planned |
| `v1.1.0` | Web tools — Google Search integration | 📋 Planned |
| `v2.0.0` | LSP diagnostics and plugin ecosystem | 🔵 Future |

---

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE) for full terms.

Built with 💎 by [julesklord](https://github.com/julesklord).
