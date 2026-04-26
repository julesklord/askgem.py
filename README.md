<p align="center">
  <img src="docs/assets/logo.svg" width="120" alt="mentask logo">
</p>

<h1 align="center">mentask</h1>

<p align="center">
  <strong>Autonomous AI Coding Agent for the Terminal</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/mentask/"><img src="https://img.shields.io/pypi/v/mentask.svg" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://models.dev/"><img src="https://img.shields.io/badge/Powered%20by-models.dev-6366f1" alt="Powered by models.dev"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/code%20style-ruff-000000.svg" alt="Code style: ruff"></a><br>
  <a href="https://github.com/julesklord/mentask.py/actions/workflows/security.yml"><img src="https://github.com/julesklord/mentask.py/actions/workflows/security.yml/badge.svg" alt="Security Scan"></a>
  <a href="https://github.com/julesklord/mentask.py/actions/workflows/python-ci.yml"><img src="https://github.com/julesklord/mentask.py/actions/workflows/python-ci.yml/badge.svg" alt="Python CI (Pro)"></a>
  <a href="https://github.com/julesklord/mentask.py/actions/workflows/release.yml"><img src="https://github.com/julesklord/mentask.py/actions/workflows/release.yml/badge.svg" alt="CD - Release"></a>
</p>

---

**WORK IN PROGRESS** | *Professional intelligence for complex codebases*

---

**mentask** is a professional, autonomous coding agent that lives in your terminal. Powered by Google Gemini and a custom orchestration engine, it reads your files, edits your code, runs shell commands, and navigates your filesystem — all within an interactive session and with hardened safety guardrails that keep you in control.

No GUI. No cloud sync. No bloat. Just a fast, opinionated CLI agent you can trust with your codebase.

---

## Contents

- [How it works](#how-it-works)
- [Features](#features)
- [New in v0.18.5: Lisan al-Gaib](#new-in-v0185-lisan-al-gaib)
- [Project Isolation (/init)](#project-isolation-init)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Slash commands](#slash-commands)
- [Safety model](#safety-model)
- [Architecture](#architecture)
- [Development & Simulation](#development--simulation)
- [Internationalization](#internationalization)
- [Repository Standard](#repository-standard)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## How it works

mentask runs an advanced asynchronous reasoning loop powered by the **AgentOrchestrator** and a modular manager-based core. On each turn:

1. **Environmental Awareness**: At startup, the **ContextManager** performs a **Project Blueprint** scan, discovering the project type, structure, and key files to build a proactive system instruction.
2. **Cognitive Loop**: Your message is processed by the **AgentOrchestrator**, which manages the *Thinking -> Action -> Observation* cycle.
3. **Tool Reasoning**: The model calls specialized tools (read, edit, execute). mentask intercepts these via the **ToolDispatcher**.
4. **Safety Guard**: Every action passes through the **Security Layer** for real-time risk analysis and path validation.
5. **Stream Processing**: The **StreamProcessor** extracts function calls and text mid-flight, showing you the agent's "thought process" in real-time.
6. **Persistence**: The full session, including tool results and metrics, is auto-saved to your Workspace history.

This autonomous loop repeats until the mission is accomplished or you interrupt it.

---

## Features

### Agentic Tool Engine

| Tool | Description |
|---|---|
| `list_directory` | Explore filesystem trees with depth control |
| `read_file` | Read any file with optional line ranges — 30k char cap prevents token overflow |
| `edit_file` | Find-and-replace with **atomic writing**, uniqueness guard, and automatic `.bkp` backup |
| `execute_bash` | Run shell commands with 60s timeout and full **Risk Analysis** |
| `manage_memory` | Save important project facts to `memory.md` for long-term recall |
| `manage_mission` | Track complex goals and sub-tasks via `heartbeat.md` mission control |
| `manage_workspace` | Detects and initializes local project knowledge bases |

### Workspace Isolation & Local Intelligence

mentask now distinguishes between your **Global Persona** and your **Project Context**:

- **Local Isolation**: Run `/init` to create a dedicated `.mentask/` folder in your project. This isolates sessions, settings, and identity to the current directory.
- **Local Priority**: If a `.mentask/` folder exists, it takes precedence for settings, memory, and history.
- **Project Memory**: Knowledge saved via `manage_memory` is stored in `.mentask/memory.md` (or `.mentask_knowledge.md` as fallback), preventing context leakage between repositories.
- **Project Identity**: Customize mentask's personality for a specific project via `.mentask/identity.md`.

### Human-in-the-loop safety

Every destructive action is categorized by risk level (`SAFE`, `NOTICE`, `WARNING`, `DANGEROUS`).
Switch modes anytime mid-session:

- **`/mode manual`** (default) — approve each file edit and shell command.
- **`/mode auto`** — trust the agent fully; all actions execute without prompts.

### Streaming terminal UX

mentask now runs through a Rich-based terminal renderer:

- Real-time Markdown streaming in the terminal.
- Inline confirmations for file edits and shell commands.
- Focus on a fast, scriptable CLI flow instead of a separate dashboard app.

### Persistent session history

Every conversation auto-saves to `~/.mentask/history/` as JSON. Reload any past session with `/history load <id>`. A rolling context window and proactive summarization keep reloaded sessions within token budget.

---

## New in v0.18.5: Lisan al-Gaib

The v0.18.5 release ("Lisan al-Gaib") transforms mentask into a persistent, self-correcting agent with advanced cognitive tools.

### 1. Persistent Gem-Style Renderer
A complete architectural overhaul of the CLI output. All thoughts, tool calls, and results now persist in your terminal scroll buffer, providing a seamless and professional experience.

### 2. Intelligence Tools (Working Memory & Planning)
- **`working_memory`**: A semantic scratchpad for the agent to store hypotheses and partial conclusions across multiple turns.
- **`plan`**: Interactive checkpointing of `.mentask_plan.md` to track multi-step missions effectively.

### 3. Self-Critique & Error Correction
Integrated reflection loops that force the agent to analyze tool failures before attempting alternative strategies, significantly increasing operational success rates.

### 4. Advanced UX Commands
- **`/undo`**: Instantly rollback accidental file modifications.
- **`/artifacts`**: Browse and expand previous tool results with a compact, interactive UI.
- **`/theme`**: Switch between premium color schemes (indigo, monokai, ocean) in real-time.

---

## Installation

### Prerequisites
- Python 3.10+
- A Google API Key — free at [Google AI Studio](https://aistudio.google.dev/).

### From Source
```bash
git clone https://github.com/julesklord/mentask
cd mentask.py
python -m venv venv
# On Windows: venv\Scripts\activate
source venv/bin/activate
pip install -e ".[dev]"
```

### Via Pip
```bash
pip install mentask
```

---

## Configuration

### API key (Standardized)
mentask loads your key from these sources, in order:
1. **Environment variable** — `GEMINI_API_KEY=your_key mentask` (Preferred)
2. **System Keyring** — Secure storage via Windows Credential Manager or macOS Keychain.
3. **Saved file** — `~/.mentask/settings.json` (Local fallback).

### Hierarchical Knowledge Hub
The agent reloads its intelligence every turn from three layers:
1. **Standard Hub (Internal)**: Built-in modules defining the "Staff Engineer" persona, operational safety rules, and multimodal guidelines (audio/video/vision).
2. **Global Hub (`~/.mentask/*.md`)**: Your cross-project technical preferences, API guidelines, or personal style.
3. **Project Hub (`.mentask/*.md`)**: Project-specific context, build commands, architecture rules, and "Mission" specifics.

> [!TIP]
> Just drop a `.md` file in any of these locations to instantly update mentask's cognitive behavior without touching the code.

---

## Multimodal Intelligence

Fully optimized for Gemini 1.5 Pro and 2.0 Flash:

- **Screenshots**: Analyze UI layouts and design systems.
- **Video**: Summarize technical demos and terminal recordings.
- **Audio**: Digest project discussions and voice notes.

---

## Usage

Launch the agent:
```bash
mentask
```

### Configuration paths

| Path | Purpose |
|---|---|
| `~/.mentask/settings.json` | Model name, edit mode, and user preferences |
| `~/.mentask/history/` | Auto-saved session JSON files |
| `~/.mentask/mentask.log` | Debug log — tool execution events and retry details |

### Common Workflows
- **Context Analysis**: "Read my `pyproject.toml` and explain the dependencies."
- **Code Generation**: "Create a `src/utils.py` file with a function to calculate SHA256 hashes."
- **Refactoring**: "Refactor `authenticate()` in `src/auth.py` to use JWT instead of sessions."

---

## Slash commands

| Command | Description |
|---|---|
| `/help` | Show the full command reference and examples |
| `/model <name>` | Switch Gemini models mid-conversation (history preserved) |
| `/mode [auto/manual]` | Toggle between approving actions or automatic execution |
| `/clear` | Reset the context window to free up tokens |
| `/usage` | Show detailed token consumption and estimated cost |
| `/stats` | Summary of session accomplishments |
| `/undo` | Rollback the last file modification |
| `/init` | Initialize local project isolation and configuration |
| `/history` | Manage saved conversation sessions |
| `/trust [path]` | Add a directory to the permanent whitelist |

---

## Safety model

**Trust Management Layer**: mentask implements a strict whitelist for file operations. By default, it can only touch the current workspace. Use `/trust` to authorize external paths.

**Cross-Drive Protection**: On Windows, the agent is blocked from crossing drive letters unless the target is explicitly trusted.

**Risk Analysis Engine**: Every command is categorized:
- `SAFE`: Informative commands (ls, git status).
- `NOTICE`: Standard operations.
- `WARNING`: High-risk patterns (sudo, sensitive file access).
- `DANGEROUS`: Critical risk (rm -rf, world-writable chmod).

**Atomic Writing**: `edit_file` uses a temporary file + rename strategy to prevent corruption.
**Automatic Backups**: Every file modification creates a backup at `~/.mentask/backups/`.

---

## Architecture

mentask operates across three tightly decoupled layers enforcing strong logical boundaries.

### High-Level System Diagram

```mermaid
flowchart TD
    CLI(["User execution (mentask)"]) --> Main(cli/main.py)
    Main --> Renderer(cli/renderer.py)
    Renderer <--> Orchestrator(agent/orchestrator.py)
    
    subgraph Cognitive_Layer [Cognitive Managers]
        Orchestrator --> Session[agent/core/session.py]
        Orchestrator --> Context[agent/core/context.py]
        Orchestrator --> Stream[agent/core/stream.py]
    end

    Orchestrator <--> GenAI[Google Gemini API]
    
    subgraph Security_Layer [Security & Trust]
        GenAI -. function calls .-> Trust[core/trust_manager.py]
        Trust --> SecurityCheck[core/security.py]
        SecurityCheck --> Tools(tools/)
    end

    Tools --> localDisk[(Local Workspace)]
```

### Layer Breakdown
1. **Presentation Layer (`cli/`)**: Handles CLI startup, interactive prompts, and real-time Markdown rendering.
2. **Cognitive Layer (`agent/`)**: The "Brain". Manages state, context blueprints, and mission tracking.
3. **Security Layer (`core/`)**: The "Guard". Gathers risk analysis and whitelisting logic.

### Project Structure

```text
mentask.py/
├── src/mentask/
│   ├── agent/               # Orchestrator and Cognitive Managers
│   ├── cli/                 # Startup and Rich streaming renderer
│   ├── core/                # Safety engine and Path resolution
│   ├── tools/               # Atomic agentic tools
│   └── locales/             # i18n JSON data (8 languages)
├── tests/                   # Unit and integration tests
├── docs/                    # Technical documentation and assets
└── pyproject.toml
```


---

## Development & Simulation

### Setup

```bash
git clone https://github.com/julesklord/mentask
cd mentask.py
pip install -e ".[dev]"
```

### Reliable Testing Protocol

mentask introduces a **Simulation Layer**. You can record agent turns and play them back deterministically:

1. **Record**: Set `SIMULATION_MODE=record` to capture interactions.
2. **Playback**: Run `pytest tests/integration/test_full_agent_loop.py` to verify the logic against the recorded transcript without hitting the real API.

### Tests & Linting

```bash
pytest tests/                   # full reliable suite
ruff check src/ tests/ --fix    # auto-fix linting violations
```

---

## Internationalization

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

## Repository Standard

`mentask.py` is now the reference repo for structure, hygiene, and architecture conventions in this workspace.

See [STANDARD.md](STANDARD.md) for the operating standard to apply across the other repositories.

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for our development workflow and code of conduct.

---

## Roadmap

| Version | Theme | Status |
|---|---|---|
| `v0.18.0`| Cognitive Architecture | ✅ Done |
| `v0.18.5`| Full Branding & Stability | ✅ Done |
| `v0.19.0`| Self-Healing Loop | 📋 Planned |
| `v0.20.0`| Absolute Orchestration | 📋 Planned |

---

## License

Licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

Built with precision by [julesklord](https://github.com/julesklord).
