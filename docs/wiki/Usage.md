# Usage

Launch `mentask` simply via standard terminal hook in the root:

```bash
mentask
```

## Console Output Examples

### 1. Startup & Welcome (v0.32.0)

When you launch mentask, you'll see the premium header indicating your active provider, security mode, and the newly standard **Engineering Level**:

```text
 ✦ mentask v0.32.0  ·  ollama:qwen3.5  ·  manual mode
 ⚡ Engineering Level: L1_PRAGMATIC
   Type /help for commands · Ctrl+C to exit
```

After each turn, a unified status line summarizes the session state in a single elegant line that matches your prompt theme:

```text
  󱚣 AUTO   󰚩 cli:gemini   󰊢 main   󰠠 $0.001  󰮄 5,111   ── 04:47:03 ──
```

### 2. Dynamic Engineering Levels (DEL)

mentask now autonomously classifies your task into one of four levels to optimize speed vs. rigor:

- **L0_INQUIRY**: Purely informational questions. No tools used. Ultra-fast response.
- **L1_PRAGMATIC**: Simple technical tasks. mentask avoids over-analysis and uses shell commands (`cat`, `sed`, `echo`) if complex tools fail.
- **L2_STANDARD**: Default development mode (Research -> Plan -> Execute).
- **L3_ARCHITECT**: High-complexity tasks. Forces the creation of `.mentask_plan.md` and deep system-wide mapping.

### 3. Agent Reasoning & The Forge Engine

mentask displays its internal reasoning loop. If it identifies a repetitive task, it may invoke **The Forge** to architect a native Python tool:

```text
 ✨ @mentask
  │ I will analyze the 50 CSV files.
  │ Standard file tools are too slow for this volume.
  │ I am forging a specialized 'bulk_csv_parser' tool...

  ⚙ EXECUTING: forge_plugin (name="bulk_csv_parser", logic="...")
  [✓] Tool 'bulk_csv_parser' synthesized and hot-reloaded into memory.

  ⚙ EXECUTING: bulk_csv_parser (directory="./data")
  [✓] Processed 50 files in 1.2s.
```

### 4. Security Check (Confirmation)

In `manual` mode (default), mentask will ask for permission before performing any mutation. You get a clear diff and risk level:

```text
 🛡  SECURITY CHECK [RISK: MEDIUM]
 mentask wants to use edit_file with these parameters:
  filePath: ./src/orchestrator.py
  ╭────────────────────────────────────────────────────────────────────────────╮
  │ - def old_logic():                                                         │
  │ + def optimized_logic():                                                   │
  │      print("Evolving...")                                                  │
  ╰────────────────────────────────────────────────────────────────────────────╯

 Allow execution? (y/n):
```

### 5. LSP Self-Correction Loop

If the agent makes a syntax error, it will autonomously fix it via **Ruff LSP** diagnostics before finalizing the turn:

```text
 👁 LSP DIAGNOSTIC
   Detected E999 (SyntaxError) in ./src/utils.py.
   Initiating autonomous fix turn...
   [✓] Syntax error resolved.
```

---

## Common Workflows

**1. Resuming a Session**
Every session has a unique ID stored in `.mentask/sessions/`. Resume exactly where you left off:

```bash
mentask 2026-04-26_15-30-10_f9a8b2
```

**2. Local-First Mode (--local)**
Run mentask entirely offline using Ollama. This mandates the use of **qwen3.5** for maximum reliability in local environments:

```bash
mentask --local
```

**3. Stall Detection & Auto-Reset**
If mentask gets stuck in a "thinking loop" (repeating the same explanations without calling tools), the orchestrator will automatically detect it and force a **Strategy Reset**, forcing the agent to try a different path (like using shell commands instead of complex file tools).

**4. Workspace Initialization (/init)**
Launch mentask in any folder. If it's a new project, run `/init` to create the local isolation layer:

- **`.mentask/plugins/`**: Where forged tools are stored.
- **`.mentask/history/`**: Persistent turn-by-turn backups.
- **`.mentask/identity.md`**: Project-specific agent personality.

**5. Tool Discovery (MCP)**
Connect to any Model Context Protocol server. mentask will automatically introspect and bind its tools:

```text
 /mcp connect http://localhost:8080
 [✓] Connected to 'Postgres-MCP'. 12 new tools added to registry.
```

**6. CLI Model Integration (CLI Bridge)**
You can use external CLI agents (such as `gemini-cli`, `codex`, or `opencode`) as your backend model/provider using standard commands:
```text
 /model cli:codex
 # or
 /model cli:opencode
```
MentAsk will run the external CLI non-interactively in the background using structured JSONL streams, parse text outputs/tool calls cleanly (bypassing visual CLI formatting headers), and extract actual token usage metrics directly from the CLI outputs.

---

## Interactive Slash Commands

### Session & Conversation

| Command | Action |
|:---|:---|
| `/help` | Show all commands and current settings. |
| `/clear` | Wipe the active context buffer (history is preserved). |
| `/compact` | Compress conversation history to save tokens. |
| `/reset` | Reset session and all counters. |
| `/undo <path>` | Rollback the last file modification to its previous state. |

### History

| Command | Action |
|:---|:---|
| `/sessions` | List previous chat sessions. |
| `/load <id>` | Load a specific session by ID or index. |

### Configuration

| Command | Action |
|:---|:---|
| `/model [name]` | List models or switch (use `/model configure` to test health). |
| `/discover [query]` | Search models.dev catalog. |
| `/mode [auto\|manual]` | Toggle between full autonomy and safety confirmation. |
| `/stream [transient\|continuous]` | Change streaming display mode. |
| `/colorscheme [name]` | List or change UI color schemes. |
| `/theme [--style <style>]` | Customize prompt style and icons. |
| `/thinking [true\|false]` | Toggle visibility of agent's thought process. |
| `/multiline [true\|false]` | Toggle multiline prompt mode. |
| `/init` | Initialize local project configuration directory. |

### Dev Tools

| Command | Action |
|:---|:---|
| `/export [md\|html\|txt\|json]` | Export conversation to file. |
| `/git [status\|diff\|log]` | Git status, diff summary, or recent log. |
| `/diff [file]` | Show uncommitted changes (staged + unstaged). |
| `/context` | Show context token usage and limits. |
| `/retry` | Re-send the last user message. |
| `/config` | Show current configuration settings. |

### Security

| Command | Action |
|:---|:---|
| `/auth <key> [provider]` | Set API key for a provider. |
| `/trust` | Authorize current directory for auto-execution. |
| `/untrust` | Remove trust from current directory. |
| `/readonly [true\|false]` | Restrict agent to read-only operations. |

### Stats & Tools

| Command | Action |
|:---|:---|
| `/usage [--reset]` | Show historical token usage. |
| `/stats` | View token consumption, USD cost, and execution metrics. |
| `/artifacts [idx]` | List or expand agent-generated tool artifacts. |

### Control

| Command | Action |
|:---|:---|
| `/stop` | Interrupt the current generation. |
| `/exit` / `/q` | Save session state and exit. |

---

## Hardened Security & Edge Cases

1. **The Trust Manager**: mentask is restricted to the current directory by default. Accessing outside paths requires `/trust <path>`.
2. **Context Snapping**: When sessions get too long, mentask proactive summarizes history into a "Snap" to stay within model limits while maintaining perfect "state awareness".
3. **Shell Limitations**: Interactive shell prompts (like `ssh` passwords) are not supported. Use non-interactive flags or keys.
4. **Keyring Fallback**: If your OS lacks a secure secret service (e.g. headless Linux), mentask falls back to `~/.mentask/settings.json` with a warning.
