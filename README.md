# askgem.py — Autonomous AI Coding Agent for the Terminal

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-4285F4.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-FBBC05.svg?logo=gnu&logoColor=black)](LICENSE)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Google%20Gemini-4285F4.svg?logo=google-gemini&logoColor=white)](https://ai.google.dev/)

**askgem** is a powerful, autonomous command-line AI coding agent powered by Google's Gemini models. Reborn with the **Friendly Prism** identity, it features a premium Google Blue/Yellow interface designed for 2000s-style technical clarity.

![askgem Banner](docs/assets/banner.png)

## 📸 Preview

**askgem in action (v2.3.0 Dashboard)**  
![askgem v2.3.0 TUI Dashboard](docs/assets/askgem_v230_dash.png)

---

## ✨ Key Features

- **Autonomous Agent:** Can read/edit files, search the web, run bash commands, and explore directories.
- **Human-in-the-Loop:** Optional confirmation prompts for all file/system actions.
- **Professional TUI:** Full-pane Dashboard with **Animated Mascot**, Live Metrics, and Debug Logs.
- **Multi-Language:** Automatic or manual language detection (8 locales supported).
- **Advanced Code Search:** Recursive `grep` and `glob` support for mapping large repositories.
- **Web Intelligence:** Live internet access via Google Search & DuckDuckGo fallbacks.

### 🤖 Autonomous Agentic Engine

askgem integrates natively with `google-genai`, enabling multi-step reasoning and autonomous actions through registered tool functions:

- **`list_directory`** — Explore filesystem trees (capped at 100 items).
- **`read_file`** — Read source code with safety character truncated (30kb).
- **`write_file`** — Create new files and directories atomically.
- **`edit_file`** — Precise find-and-replace code blocks with mandatory `.bkp` backups.
- **`grep_search`** — Recursive text/regex searching across entire codebases.
- **`glob_find`** — Recursive file discovery by filename patterns.
- **`web_search`** — [NEW] Live Google/DuckDuckGo research for docs and APIs.
- **`web_fetch`** — [NEW] Clean and truncate webpage content for ingestion.
- **`execute_bash`** — Run shell commands with configurable timeout.

### 🛡️ Human-in-the-Loop Safety

A built-in guardrail system prompts for explicit `(Y/n)` confirmation before executing destructive actions. Toggle between modes:

- `/mode manual` — Approve every file edit and command execution (default).
- `/mode auto` — Trust the agent to operate autonomously.

### 🌍 Multi-Language Support (i18n)

askgem automatically detects your operating system locale. Currently supported: `en`, `es`, `fr`, `de`, `pt`, `it`, `ja`, `zh`.

---

## 📚 Documentation & Wiki

For detailed guides, please visit our **[GitHub Wiki](https://github.com/julesklord/askgem.py/wiki)** (also available locally in the `wiki/` folder):

- [Installation Guide](https://github.com/julesklord/askgem.py/wiki/Installation_and_Setup)
- [Command Reference](https://github.com/julesklord/askgem.py/wiki/Usage)
- [Architecture Deep-Dive](https://github.com/julesklord/askgem.py/wiki/Architecture)
- [Development Guide](https://github.com/julesklord/askgem.py/wiki/Development_Guide)

### 🔄 GitHub Wiki Sync

The `wiki/` folder is designed to be compatible with GitHub's native Wiki system. To synchronize them:

1. Clone your project's Wiki repository: `git clone https://github.com/julesklord/askgem.py.wiki.git`
2. Copy contents from `wiki/` to the wiki clone.
3. Commit and push: `git add . && git commit -m "Sync wiki" && git push origin master`

---

## 📦 Installation

### Prerequisites

- **Python 3.8** or higher
- A **Google Gemini API Key** — [Google AI Studio](https://aistudio.google.com/)

### Install from Source (Development)

```bash
git clone https://github.com/julesklord/askgem.git
cd askgem
pip install -e ".[dev]"
```

### Install directly via pip (v2.3.0)

```bash
pip install askgem
```

---

## 📖 Usage

Launch the interactive agent:

```bash
askgem
```

In-session commands start with `/`. Use `/help` for the full reference.

---

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md) for the full development roadmap.

- **v2.1** — Stability & Visual Rebirth (retry logic, `/undo`) [SHIPPED]
- **v2.2** — Advanced Code Tools (`grep_search`, `glob_find`) [SHIPPED]
- **v2.3** — TUI Dashboard & Web Research (Intelligence Update) [CURRENT]
- **v2.4** — Visionary Terminal Experience (Code Navigation)
- **v2.5** — LSP Integration (Syntax-aware coding)

---

## 📝 License

This project is licensed under the **GNU General Public License v3 (GPLv3)**.
See the [LICENSE](LICENSE) file for details.

Built with ❤️ by [julesklord](mailto:julioglez@gmail.com).
