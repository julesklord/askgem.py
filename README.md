# askgem.py — Autonomous AI Coding Agent for the Terminal

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-green.svg)](LICENSE)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Google%20Gemini-4285F4.svg)](https://ai.google.dev/)
[![Version: 0.8.0](https://img.shields.io/badge/version-0.8.0--beta-orange.svg)](https://github.com/julesklord/askgem/releases)

**askgem** is a powerful, autonomous command-line AI coding agent powered by Google's Gemini models. Unlike simple chatbots, askgem can read your files, edit your code, execute shell commands, and navigate your entire filesystem — all from an interactive terminal session with built-in safety guardrails.

![askgem Logo](docs/askgem.webp)

---

## ✨ Key Features

### 🤖 Autonomous Agentic Engine
askgem integrates natively with `google-genai`, enabling multi-step reasoning and autonomous actions through registered tool functions:
- **`list_directory`** — Explore filesystem trees with intelligent depth management.
- **`read_file`** — Read source code with optional line ranges and automatic token management.
- **`edit_file`** — Precise find-and-replace code blocks with mandatory `.bkp` backups.
- **`execute_bash`** — Run shell commands with configurable timeout and error capturing.

### 🛡️ Human-in-the-Loop Safety
A built-in guardrail system prompts for explicit `(y/n)` confirmation before executing destructive actions.
- `/mode manual` — Approve every file edit and command execution (default).
- `/mode auto` — Trust the agent to operate autonomously (use with caution).

### 🪙 Token Economy & Resilience
- **Compact Prompts**: Optimized system instructions to reduce base token consumption by ~40%.
- **Rolling Context Window**: Intelligent history truncation that monitors both message counts and total character volume to prevent TPM (Tokens Per Minute) exhaustion.
- **Auto-Retry Patterns**: Exponential backoff logic to handle transient 429 and 500 API errors gracefully.

### 🌍 Multi-Language Support (i18n)
askgem automatically detects your OS locale. Currently supported: `en`, `es`, `fr`, `pt`, `de`, `it`, `ja`, `zh`.

---

## 📚 Documentation (Wiki)

Comprehensive guides are available in the [wiki/](wiki/Home.md) folder:

- 🏠 [**Home**](wiki/Home.md) — Quick start and general overview.
- 🏗️ [**Architecture**](wiki/Architecture.md) — System diagram and modular breakdown.
- ⚙️ [**Installation & Setup**](wiki/Installation_and_Setup.md) — Full configuration guide.
- 📖 [**Usage Guide**](wiki/Usage.md) — Workflows, slash commands, and examples.
- 🛠️ [**Development Guide**](wiki/Development_Guide.md) — Contribution conventions and testing logic.
- 📜 [**Changelog**](wiki/Changelog.md) — Version history and release notes.

> [!TIP]
> To view the documentation as a native GitHub Wiki, follow the [Wiki Sync Instructions](#-github-wiki-sync).

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.8** or higher
- A **Google Gemini API Key** — get one free at [Google AI Studio](https://aistudio.google.com/)

### Install from Source
```bash
git clone https://github.com/julesklord/askgem.git
cd askgem
pip install -e ".[dev]"
askgem
```

On first launch, askgem will prompt you for your API Key and save it to `~/.askgem/.gemini_api_key_unencrypted`.

---

## 🏗️ Project Architecture (v0.8.0)

```
askgem/
├── src/askgem/
│   ├── __init__.py          # Version (0.8.0)
│   ├── agent/               # Core reasoning logic
│   │   └── chat.py          # ChatAgent class & event loop
│   ├── cli/                 # User interface
│   │   ├── main.py          # Entry point
│   │   └── console.py       # Rich formatting
│   ├── core/                # Shared utilities
│   │   ├── config_manager.py
│   │   ├── history_manager.py
│   │   ├── i18n.py
│   │   └── paths.py         # Centralized path management
│   ├── tools/               # Agent capabilities
│   │   ├── file_tools.py
│   │   └── system_tools.py
│   └── locales/             # Localization JSONs
├── tests/                   # Test suite & diagnostics
├── wiki/                    # Extensive documentation
└── pyproject.toml           # Package metadata
```

---

## 🔄 GitHub Wiki Sync

The `wiki/` folder in this repository is designed to be compatible with GitHub's native Wiki system. To synchronize them:

1. Clone your project's Wiki repository:
   ```bash
   git clone https://github.com/julesklord/askgem.py.wiki.git
   ```
2. Copy the contents of the `wiki/` directory into the wiki clone.
3. Push the changes to the Wiki repo:
   ```bash
   # Commands sequence:
   cp wiki/* ../askgem.py.wiki/
   cd ../askgem.py.wiki
   git add .
   git commit -m "Sync wiki from main repo"
   git push origin master
   ```

---

## 📝 License

This project is licensed under the **GNU General Public License v3 (GPLv3)**.
See the [LICENSE](LICENSE) file for details.

Built with ❤️ by [julesklord](mailto:julioglez@gmail.com).
