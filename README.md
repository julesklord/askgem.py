# askgem.py — Autonomous AI Coding Agent for the Terminal

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-green.svg)](LICENSE)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Google%20Gemini-4285F4.svg)](https://ai.google.dev/)

**askgem** is a powerful, autonomous command-line AI coding agent powered by Google's Gemini models. Unlike simple chatbots, askgem can read your files, edit your code, execute shell commands, and navigate your entire filesystem — all from an interactive terminal session with built-in safety guardrails.

![askgem Logo](docs/askgem.webp)

---

## ✨ Key Features

- **Autonomous Agent:** Can read/edit files, run bash commands, and explore directories.
- **Human-in-the-Loop:** Optional confirmation prompts for all file/system actions.
- **Multi-Language:** Automatic or manual language detection (8 locales supported).
- **Token Economy:** Smart context window management with character-based limits.
- **Modern TUI:** Stylized `Rich` interface with real-time Markdown and status spinners.

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

| Locale | Language | Description |
| :--- | :--- | :--- |
| `en` | English | Default global locale |
| `es` | Spanish | Full native support |
| `fr` | French | Translated UI & tools |
| `de` | German | Technical localization |
| `pt` | Portuguese | Brazilian support |
| `it` | Italian | Full UI support |
| `ja` | Japanese | Full UI support |
| `zh` | Chinese | Simplified Chinese |

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

### Install directly via pip (v2.1.0)

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

## 🏗️ Project Architecture (v2.1.0)

```text
src/askgem/
├── agent/       # GenAI core & Tool handling
├── cli/         # TUI, Commands & Argument parsing
├── core/        # Paths, History & i18n
└── locales/     # Translation JSONs
```

---

## 📚 Documentation & Wiki

For detailed guides, please visit our **[GitHub Wiki](https://github.com/julesklord/askgem.py/wiki)**:
- [Installation Guide](https://github.com/julesklord/askgem.py/wiki/Installation_and_Setup)
- [Command Reference](https://github.com/julesklord/askgem.py/wiki/Usage)
- [Architecture Deep-Dive](https://github.com/julesklord/askgem.py/wiki/Architecture)
- [Development Guide](https://github.com/julesklord/askgem.py/wiki/Development_Guide)

---

### 💎 Token Economy

askgem v2.1 includes a sophisticated token-aware context manager:

- **Compact Prompts**: Reduced system instruction overhead by 40%.
- **Rolling Context**: Automatically prunes large file reads from memory while retaining conversation logic.
- **Manual Reset**: Use `/clear` to instantly wipe current context to save API tokens.

### 🛡️ Resilience & Safety

- **Retry Logic**: Automatic exponential backoff for 429 (Quota) and 500/503 (API Error) codes.
- **Protected Modes**: Manual confirmation for system-level actions prevents accidental deletions.

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

## 🛠️ Configuration

API keys and settings are stored in your home directory:

```bash
~/.askgem/
├── .gemini_api_key_unencrypted  # Your Google AI Studio Key
└── settings.json                # Model, Persona, and UI preferences
```

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

Built with ❤️ by [julesklord](mailto:julioglez.93@gmail.com) and Claude (Anthropic).
