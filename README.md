<p align="center">
  <img src="docs/assets/logo.svg" width="160" alt="mentask logo">
</p>

<h1 align="center">mentask</h1>

<p align="center">
  <strong>The Self-Evolving Autonomous Agent for Engineers Who Hate Repetitive Tasks.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/mentask/"><img src="https://img.shields.io/pypi/v/mentask.svg" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://models.dev/"><img src="https://img.shields.io/badge/Powered%20by-models.dev-6366f1" alt="Powered by models.dev"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/code%20style-ruff-000000.svg" alt="Code style: ruff"></a>
</p>

---

## 🚀 Installation & Setup

mentask is designed to run locally with a minimal footprint.

### Prerequisites
- **Python:** 3.10+ (Tested up to 3.14)
- **API Key:** A valid Google Gemini API Key (or OpenAI/DeepSeek via models.dev).
- **System:** Standard OS commands (bash on UNIX, pwsh on Windows).

### Detailed Setup (Recommended)

For the best experience, clone the repository and install it in a virtual environment:

```bash
git clone https://github.com/julesklord/mentask
cd mentask

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"
```

Alternatively, install directly from PyPI:
```bash
pip install mentask
```

### First Run & Configuration
Simply run the CLI in your project directory:
```bash
mentask
```
*Note: On the first run, mentask will prompt for your API key and securely store it in your OS\'s native secret service via `keyring` (Keychain/KWallet/Credential Manager). We don't store plain-text keys in configs.*

You can also bypass the prompt by exporting the key:
`export GEMINI_API_KEY="your-key-here"`

---

## 🙄 Why another AI coding agent?

Let's be honest. 90% of "AI agents" today are glorified chat wrappers. You paste an error, the AI hallucinates a function, you copy-paste it back, it fails, you paste the new error. It's a glorified clipboard exercise.

**mentask is fundamentally different.** It is a **Stateful Orchestrator** that lives in your terminal. It owns the execution loop. It reads the file, parses the AST, modifies the code, runs the linter, intercepts the traceback, and fixes its own mistakes before it even bothers to tell you it's done.

But more importantly: **it builds its own tools.**

---

## ⚡ v0.20.0: THE SPICE MUST FLOW (Level 4 Autonomy)

Most agents are limited by the tools their developers hardcoded into them. As of v0.20.0, mentask achieves **Level 4 Autonomy**: The ability to dynamically expand its own operational schema.

### 🛠️ The Autonomous Forge Engine
When mentask encounters a repetitive or highly specific engineering problem (e.g., "parse 50 CSVs, normalize the timestamps, and dump to sqlite"), it realizes that doing this via bash commands is inefficient. 

Instead, it invokes `forge_plugin`. 
1. **Synthesis**: The LLM writes a native Python module subclassing `BaseTool`, complete with Pydantic schemas for the arguments.
2. **AST Validation**: Before the code ever touches your disk, mentask runs `ast.parse()` to guarantee the syntax is valid Python. No `SyntaxError` crashes mid-loop.
3. **Hot-Reload Injection**: Using `importlib.util.module_from_spec`, the new tool is compiled and injected directly into the `ToolRegistry`'s memory space. 
4. **Execution**: The agent immediately calls its newly forged tool in the very next turn. 

The tool is saved to `.mentask/plugins/` and persists for your entire project lifecycle. You didn't write the tool. You didn't restart the agent. It just evolved.

---

## 🏗️ The 3-Tier Architecture (Under the Hood)

mentask isn't a monolith; it's a decoupled orchestration engine.

```mermaid
flowchart TD
    CLI(["User execution (mentask)"]) --> Main(cli/main.py)
    Main --> Renderer(cli/renderer.py)
    Renderer <--> Orchestrator(agent/orchestrator.py: AgentOrchestrator)
    
    subgraph Cognitive_Layer [Cognitive Managers]
        Orchestrator --> Session[SessionManager: persistent memory, rollback]
        Orchestrator --> Context[ContextManager: compression, snapping]
        Orchestrator --> Hub[KnowledgeManager: semantic indexing]
        Orchestrator --> Loader[PluginLoader: hot-reload, runtime injection]
    end

    subgraph Tool_Ecosystem [3-Layer Toolset]
        Registry[ToolRegistry]
        Registry --> Layer1(src/mentask/tools/: Immutable Core Tools)
        Registry --> Layer2(mcp_manager.py: Community MCP servers)
        Registry --> Layer3(.mentask/plugins/: Agent-Forged Plugins)
    end

    Orchestrator <--> Registry
    Loader -. hot-reload .-> Registry
    Loader -. scan .-> Layer3

    Orchestrator <--> LLM[Google Gemini / DeepSeek / Claude]
    
    subgraph Security_Layer [Security & Trust Centinel]
        LLM -. function calls .-> Trust[core/trust_manager.py]
        Trust --> SecurityCheck[core/security.py]
        SecurityCheck --> Registry
    end
```

### Module Breakdown (The Core Contracts)

We don't hide our internals. Here is exactly what runs when you launch mentask.

| Component | Path | Core Responsibility |
|:---|:---|:---|
| **The Heart** | `agent/orchestrator.py` | Central `Thinking -> Action -> Observation` loop. Uses ReAct prompting but optimized for system-level operations. |
| **The Snap** | `agent/core/context.py` | **Context Snapping**. When the token buffer hits 80%, it pauses execution, synthesizes history into a dense state representation, and flushes raw logs to save tokens. |
| **The Evolver** | `core/plugin_loader.py` | Handles dynamic `importlib` logic to inject new agent-forged tools into the registry at runtime. |
| **The Guard** | `core/trust_manager.py` | Whitelist-based security centinel. Validates if a path is within the workspace or explicitly trusted. |
| **The Linter** | `Ruff LSP (Background)` | Direct integration. Intercepts `E999` and `F821` diagnostics to initiate autonomous self-correction loops. |

---

## 🛡️ The Guard (Zero-Trust Security)

We know you're paranoid about an AI running `rm -rf /` or leaking your `.env`. We are too.

- **Strict Whitelisting (`TrustManager`)**: By default, mentask can only touch the directory it was launched in. Trying to access `/etc/` or `../other_project` throws a hard `SecurityError` unless explicitly authorized via `/trust`.
- **Canonical Path Traversal Guards**: It resolves all symlinks and strictly checks bounds. You can't trick it with `../../../`.
- **Atomic Operations**: File modifications use a `write-to-temp -> validate -> rename` strategy. Every mutation generates an automatic `.bkp` snapshot in `.mentask/history/`. If it breaks your code, just type `/undo`.
- **OS Keyring Integration**: API keys are stored in your OS's native secure enclave (Keychain/KWallet/SecretService).

---

## 📦 Dependency Footprint (Minimalist)

We hate bloat. mentask forces an extremely strict minimal dependency tree. No heavy ORMs, no web frameworks.

| Package | Purpose | Replaceable? |
|:---|:---|:---|
| `google-genai` | Fundamental API transaction protocols. | No. Direct platform wrapper. |
| `rich` | Low-level console formatting and styled TUI tables. | Highly difficult. |
| `keyring` | Secure OS-level storage for API keys. | Recommended for security standards. |

---

## ⌨️ TUI & Commands (Ditch the Mouse)

A premium, Rich-powered terminal UI that streams the agent's internal monologue.

| Command | Action |
|:---|:---|
| `/help` | Show all commands and current settings. |
| `/init` | Bootstrap your project. Creates the local `.mentask/` brain and SQLite history DB. |
| `/model <id>` | Hot-swap between Gemini 2.5 Pro, DeepSeek V3, or Claude 3.5 Sonnet mid-session. |
| `/mode [auto\|manual]` | Toggle between `manual` (ask before running tools) and `auto` (Jesus take the wheel). |
| `/trust [path]` | Authorize a directory for file operations. |
| `/artifacts` | List or expand agent-generated tool artifacts. |
| `/undo` | Rollback the AST state of the last modified file. |
| `/stats` | View token consumption, execution times, and estimated API costs in real-time. |
| `/sessions` | List recent sessions available to resume. |

---

## 🗺️ Roadmap: The God Emperor Era

- [x] **v0.18.0**: Lisan al-Gaib (Core Orchestrator, TrustManager, Multi-Provider)
- [x] **v0.20.0**: The Spice Must Flow (The Forge Engine, AST Validation, Hot-Reloading)
- [ ] **v0.21.0**: God Emperor (Semantic Vector Indexing for massive mono-repos, Distributed parallel sub-agents)

---

### Contributing
Licensed under the **MIT License**. 

Built with ❤️, excessive caffeine, and a deep hatred for manual refactoring by [julesklord](https://github.com/julesklord). If it breaks, open an issue. If it automates your job, buy me a beer.
