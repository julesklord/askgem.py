# askgem.py — Autonomous AI Coding Agent for the Terminal

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-green.svg)](LICENSE)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Google%20Gemini-4285F4.svg)](https://ai.google.dev/)

**askgem** is a powerful, autonomous command-line AI coding agent powered by Google's Gemini models. Unlike simple chatbots, askgem can read your files, edit your code, execute shell commands, and navigate your entire filesystem — all from an interactive terminal session with built-in safety guardrails.

![askgem Logo](docs/askgem.webp)

---

## ✨ Key Features

### 🤖 Autonomous Agentic Engine
askgem integrates natively with `google-genai`, enabling multi-step reasoning and autonomous actions through registered tool functions:
- **`list_directory`** — Explore filesystem trees
- **`read_file`** — Read source code with optional line ranges (prevents token overflow)
- **`edit_file`** — Find-and-replace code blocks with mandatory `.bkp` backups
- **`execute_bash`** — Run shell commands with configurable timeout (60s default)

### 🛡️ Human-in-the-Loop Safety
A built-in guardrail system prompts for explicit `(Y/n)` confirmation before executing destructive actions. Toggle between modes:
- `/mode manual` — Approve every file edit and command execution (default)
- `/mode auto` — Trust the agent to operate autonomously

### 🌍 Multi-Language Support (i18n)
askgem automatically detects your operating system locale and renders the entire interface in your language. Currently supported:

| Code | Language              | File        |
|------|-----------------------|-------------|
| `en` | English               | `en.json`   |
| `es` | Español               | `es.json`   |
| `fr` | Français              | `fr.json`   |
| `pt` | Português (Brasil)    | `pt.json`   |
| `de` | Deutsch               | `de.json`   |
| `it` | Italiano              | `it.json`   |
| `ja` | 日本語                 | `ja.json`   |
| `zh` | 中文 (简体)            | `zh.json`   |

If your language is not available, askgem gracefully falls back to English. You can also override detection by setting the `LANG` environment variable (e.g., `LANG=fr_FR askgem`).

### 📚 Smart Context Windows
Sessions are persisted automatically to `~/.askgem/history/`. The rolling window context manager keeps the most relevant messages loaded, discarding older ones to optimize token usage and API costs.

### 🌈 Premium Terminal UI
Rich terminal rendering powered by the `rich` library — real-time Markdown streaming, syntax-highlighted code blocks, stylized panels, spinners during tool execution, and interactive prompts.

---

## 🚀 Installation

### Prerequisites
- **Python 3.8** or higher
- A **Google API Key** — get one free at [Google AI Studio](https://aistudio.google.com/)

### Install from Source (Development)
```bash
git clone https://github.com/julesklord/askgem.git
cd askgem
pip install -e ".[dev]"
```

### Install from PyPI (Coming Soon)
```bash
pip install askgem
```

---

## 📖 Usage

Launch the interactive agent:
```bash
askgem
```

On first launch, askgem will prompt you for your Google API Key and optionally save it to `~/.askgem/` for future sessions.

### Slash Commands

| Command                | Description                                                      |
|------------------------|------------------------------------------------------------------|
| `/help`                | Display the full command reference                               |
| `/model`               | List all available Gemini models for your API key                |
| `/model <name>`        | Switch to a different model (preserves chat history)             |
| `/mode auto`           | Allow the agent to edit files without confirmation               |
| `/mode manual`         | Require confirmation before every file edit (default)            |
| `/clear`               | Wipe the current context window (saves tokens)                   |
| `/history list`        | List all previously saved sessions                               |
| `/history load <id>`   | Resume a saved session (applies context window limit)            |
| `/history delete <id>` | Permanently delete a session from disk                           |
| `exit` / `quit` / `q`  | Exit askgem                                                      |
| `Ctrl+C`               | Interrupt generation or forcefully close the program             |

---

## 🏗️ Project Architecture

```
askgem/
├── src/askgem/
│   ├── __init__.py          # Package version
│   ├── main.py              # CLI entry point & Welcome Panel
│   ├── core/
│   │   ├── config_manager.py    # JSON-based settings persistence
│   │   ├── history_manager.py   # Rolling window session management
│   │   └── i18n.py              # Auto-detecting translation engine
│   ├── engine/
│   │   └── query_engine.py      # Main agentic loop & tool dispatch
│   ├── tools/
│   │   ├── file_tools.py        # read_file, edit_file
│   │   └── system_tools.py      # list_directory, execute_bash
│   ├── ui/
│   │   └── console.py           # Shared Rich console instance
│   └── locales/
│       ├── en.json, es.json, fr.json, pt.json
│       ├── de.json, it.json, ja.json, zh.json
├── tests/
│   ├── test_config_manager.py
│   ├── test_file_tools.py
│   └── test_system_tools.py
├── docs/
├── pyproject.toml
├── CHANGELOG.md
├── LICENSE (GPLv3)
└── README.md
```

---

## 🧪 Development & Testing

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run the test suite
pytest tests/

# Run static analysis
ruff check src/askgem tests/

# Build the package
python -m build
```

### Configuration Paths

| Path                                      | Purpose                          |
|-------------------------------------------|----------------------------------|
| `~/.askgem/settings.json`                 | User preferences (model, mode)   |
| `~/.askgem/.gemini_api_key_unencrypted`   | Locally stored API key           |
| `~/.askgem/history/`                      | Persisted chat sessions          |
| `~/.askgem/askgem.log`                    | Debug log file                   |

---

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md) for the full development roadmap covering upcoming features:
- **v2.1** — Stability & error resilience (retry logic, `/undo`, `write_file`)
- **v2.2** — Advanced code tools (`grep_search`, `glob_find`, `diff_file`)
- **v2.3** — Web research integration (Google Custom Search API)
- **v2.4** — Token economy & cost tracking
- **v2.5** — LSP integration (syntax-aware diagnostics)
- **v3.0** — Plugin ecosystem

---

## 🤝 Contributing

Contributions are welcome! To add a new language translation:
1. Copy `src/askgem/locales/en.json` to `src/askgem/locales/<your_lang_code>.json`
2. Translate all string values (keep the keys untouched)
3. Submit a pull request

---

## 📝 License

This project is licensed under the **GNU General Public License v3 (GPLv3)**.
See the [LICENSE](LICENSE) file for details.

---

Built with ❤️ by [julesklord](mailto:julioglez.93@gmail.com)
