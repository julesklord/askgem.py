# mentask

<table>
<tr>
<td><img src="docs/assets/logo.svg" alt="mentask logo" width="64"></td>
<td>

**Autonomous coding agent for the terminal.**

[![PyPI version](https://img.shields.io/pypi/v/mentask.svg)](https://pypi.org/project/mentask/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/pitahayaDevSoft/mentask.py/blob/main/LICENSE/README.md)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

</td>
</tr>
</table>

---

<div align="center"><img src="docs/assets/shot.png" alt="mentask screenshot" width="900"></div>

---

mentask is a CLI-based AI agent that reads, writes, and edits code autonomously. It connects to cloud LLMs (Gemini, OpenAI, DeepSeek) or runs locally via Ollama. It manages its own tooling, context, and state across multi-turn conversations.

```
$ mentask
? > refactor the error handling in src/services/ to use a custom exception hierarchy

  󱚣 Refactoring error handling in src/services/...
    󰓆 Reading src/services/auth.py (142 lines)
    󰓆 Reading src/services/payment.py (89 lines)
    󰓆 Editing src/services/auth.py — replacing bare except blocks
    󰓆 Editing src/services/payment.py — adding PaymentError class
    󰓆 Writing src/exceptions.py — new exception hierarchy
    󰄬 Done — 3 files modified, 1 file created
```

---

## Installation

```bash
pip install mentask
```

Or from source:

```bash
git clone https://github.com/pitahayaDevSoft/mentask.py.git
cd mentask.py
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Requirements

- Python 3.10+
- `bash` (Linux/macOS) or `pwsh` (Windows)
- An API key for one of: Google Gemini, OpenAI, DeepSeek, Groq
- For local use: [Ollama](https://ollama.com) with a compatible model

### API Keys

mentask stores keys in your OS secret service (Keychain, GNOME Keyring, Windows Credential Vault) via `keyring`. On first use, you'll be prompted to enter your key, or you can set it manually:

```bash
# Via keyring
keyring set mentask gemini_api_key

# Or via environment variables
export GEMINI_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
export DEEPSEEK_API_KEY="your-key"
```

### Local Mode (Ollama)

```bash
ollama pull qwen3.5
mentask --local
```

---

## How It Works

mentask runs an autonomous Think-Act-Observe loop. Given a prompt, it:

1. Classifies the task into an engineering level (inquiry, pragmatic, standard, architect).
2. Plans a sequence of tool calls to accomplish the goal.
3. Executes tools (read files, edit code, run shell commands, search, fetch URLs).
4. Observes results, self-corrects on failures, and iterates until done.

The agent has access to 20+ built-in tools and can synthesize new ones at runtime via the Forge engine.

### Supported Providers

| Provider | Models | Notes |
|----------|--------|-------|
| Google Gemini | gemini-2.5-pro, gemini-2.5-flash | Default cloud provider |
| OpenAI | gpt-4o, gpt-4.1, o3 | Via OpenAI API |
| DeepSeek | deepseek-chat, deepseek-reasoner | Via OpenAI-compatible endpoint |
| Ollama | Any local model | Runs fully offline |
| Gemma | gemma3, gemma4 | Native Ollama integration |
| CLI Bridge | Any subprocess-based model | Custom provider via CLI |

### Built-in Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with line numbers |
| `edit_file` | Surgical find-and-replace edits |
| `write_file` | Create or overwrite files |
| `list_dir` | List directory contents |
| `shell` | Execute shell commands |
| `python_repl` | Run Python code in a sandboxed subprocess |
| `grep_search` | Regex search across files |
| `glob_find` | Find files by pattern |
| `web_search` | Search the web |
| `web_fetch` | Fetch and parse web pages |
| `git_commit` | Stage and commit changes |
| `worktree` | Create/exit git worktrees for parallel work |
| `memory` | Store and retrieve project knowledge |
| `plan` | Create and track task plans |
| `subagent` | Delegate subtasks to a child agent |
| `ask_user` | Ask the user for input |
| `forge_plugin` | Synthesize new tools at runtime |
| `mcp_tool` | Bridge to MCP servers |

---

## Slash Commands

### Session

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/clear` | Clear conversation history |
| `/compact` | Compress history to save tokens |
| `/reset` | Reset session and counters |
| `/undo <path>` | Restore last backed-up version of a file |

### History

| Command | Description |
|---------|-------------|
| `/sessions` | List previous chat sessions |
| `/load <id>` | Load a specific session |

### Configuration

| Command | Description |
|---------|-------------|
| `/model [name]` | List or switch models; `/model configure` to test health |
| `/discover [query]` | Search the models.dev catalog |
| `/mode auto\|manual` | Toggle automatic vs manual tool execution |
| `/stream [mode]` | Change streaming mode (continuous/transient) |
| `/colorscheme [name]` | List or change UI color schemes |
| `/theme --style atomic` | Customize prompt style and icons |
| `/thinking [true\|false]` | Toggle visibility of agent's thought process |
| `/multiline [true\|false]` | Toggle multiline prompt mode |
| `/init` | Initialize local project configuration directory |

### Security

| Command | Description |
|---------|-------------|
| `/auth <key> [provider]` | Set API key for a provider |
| `/trust` | Trust current directory for auto-execution |
| `/untrust` | Remove trust from current directory |
| `/readonly [true\|false]` | Restrict agent to read-only operations |

### Dev Tools

| Command | Description |
|---------|-------------|
| `/export [md\|html\|txt\|json]` | Export conversation to file |
| `/git [status\|diff\|log]` | Git status, diff summary, or recent log |
| `/diff [file]` | Show uncommitted changes |
| `/context` | Show context token usage and limits |
| `/retry` | Re-send last user message |
| `/config` | Show current configuration settings |

### Stats & Control

| Command | Description |
|---------|-------------|
| `/usage [--reset]` | Show historical token usage |
| `/stats` | Show current session statistics |
| `/artifacts [idx]` | List or expand tool outputs |
| `/stop` | Interrupt current generation |
| `/exit` | Exit mentask |

---

## Architecture

```
mentask/
├── agent/
│   ├── core/
│   │   ├── providers/        # LLM adapters (Gemini, OpenAI, Ollama, Gemma, CLI)
│   │   ├── command_handlers/ # Slash command implementations
│   │   ├── lsp_client.py     # Language Server Protocol integration
│   │   ├── session.py        # Runtime session state
│   │   ├── context.py        # Context window management
│   │   └── execution.py      # Tool execution engine
│   ├── tools/                # 20+ built-in tools
│   ├── chat.py               # Multi-turn conversation loop
│   ├── orchestrator.py       # Central Think-Act-Observe engine
│   └── schema.py             # Event types and protocols
├── cli/
│   ├── gem_renderer.py       # Persistent TUI renderer
│   ├── token_renderer.py     # Transient bridge renderer
│   ├── interactive_shell.py  # Prompt-toolkit integration
│   └── themes.py             # Color scheme system
├── core/
│   ├── config_manager.py     # Settings and API key management
│   ├── history_manager.py    # Session persistence (SQLite)
│   ├── rag_manager.py        # TF-IDF workspace indexing
│   ├── plugin_loader.py      # Dynamic plugin system
│   ├── security.py           # Path validation and sandboxing
│   ├── trust_manager.py      # Directory trust management
│   ├── subprocess_safety.py  # Command injection prevention
│   ├── process_tracker.py    # Subprocess lifecycle management
│   └── mcp_manager.py        # Model Context Protocol integration
├── api/
│   └── server.py             # Optional WebSocket/REST API (FastAPI)
└── locales/                  # i18n (en, es, de, fr, it)
```

### Key Components

| Component | Role |
|-----------|------|
| **Orchestrator** | Central loop that routes between thinking, tool execution, and response generation. Uses stall detection to break infinite thinking loops. |
| **Provider Manager** | Abstracts LLM providers behind a unified streaming interface. Handles retries, fallbacks, and token counting. |
| **Execution Engine** | Manages tool dispatch, sandboxing, and concurrency. Supports read-only mode and operation timeouts. |
| **Context Manager** | Handles token budget tracking and automatic history compression when context approaches limits. |
| **RAG Manager** | Lightweight TF-IDF engine that indexes workspace files for semantic code search. Uses SQLite caching for fast startup. |
| **Plugin Loader** | Dynamically synthesizes and loads new tools at runtime. Validates AST and blocks dangerous imports. |
| **Trust Manager** | Controls which directories the agent can modify. Supports per-session and permanent trust. |
| **MCP Manager** | Bridges external MCP servers for extended tool capabilities. |

---

## Configuration

mentask stores configuration in `~/.mentask/config.toml`. Key settings:

```toml
theme = "indigo"
temperature = 0.7
stream_delay = 0.015
nerdfonts_enabled = true
show_thinking = true
readonly_mode = false
max_tokens = 4096          # Override model default (useful for Ollama)
```

### Project Workspaces

Run `mentask` in any project directory. On first launch, mentask offers to create a `.mentask/` directory for project-specific history, knowledge, and configuration. This isolates project state from the global config.

---

## Security

- **Path validation**: All file operations resolve symlinks and validate against the trusted directory set.
- **Command injection prevention**: Shell commands are validated against a blocklist of dangerous patterns (pipe to write, subshell expansion, `/etc/` writes).
- **Git flag injection**: Git arguments are checked for flag injection in positional parameters.
- **Plugin sandboxing**: Dynamic plugins are AST-validated before execution. Dangerous imports (`os`, `subprocess`, `ctypes`, `socket`, etc.) are blocked.
- **Atomic file operations**: File modifications use temporary files and renames to prevent corruption.
- **Keyring integration**: API keys are stored in the OS secret service, not in plaintext files.
- **Read-only mode**: `/readonly true` restricts the agent to reading existing files only.

---

## Development

```bash
git clone https://github.com/pitahayaDevSoft/mentask.py.git
cd mentask.py
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Testing

```bash
pytest tests/                    # Run all tests
pytest tests/ -m "not integration"  # Skip integration tests (requires Ollama)
pytest --cov=mentask --cov-report=html  # Coverage report
```

### Code Quality

```bash
ruff check src/                  # Lint
ruff format src/                 # Format
mypy src/mentask                 # Type check
bandit -r src/mentask            # Security scan
pip-audit                        # Dependency audit
```

### CI Pipeline

The GitHub Actions workflow runs: lint (ruff) → typecheck (mypy) → security (bandit + pip-audit) → test (pytest with coverage). Coverage threshold is 75%.

---

## Documentation

Full documentation is in the [docs/wiki](docs/wiki/) directory:

- [Installation and Setup](docs/wiki/Installation_and_Setup.md)
- [Usage Guide](docs/wiki/Usage.md)
- [API Reference](docs/wiki/API_Reference.md)
- [Architecture](docs/wiki/Architecture.md)
- [Security](docs/wiki/security.md)
- [Development Guide](docs/wiki/Development_Guide.md)
- [Roadmap](docs/wiki/roadmap.md)

---

## License

MIT License. See [LICENSE](LICENSE/README.md).

Developed by [pitahayaDevSoft](https://github.com/pitahayaDevSoft).
