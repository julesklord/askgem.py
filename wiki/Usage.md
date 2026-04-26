# Usage

Launch `mentask` simply via standard terminal hook in the root:

```bash
mentask
```

### Console Output Examples

#### 1. Startup & Welcome (v0.20.1)
When you launch mentask, you'll see the premium header indicating your active provider and security mode:

```text
 ✦ mentask v0.20.1  ·  gemini-2.0-flash  ·  manual mode
   Type /help for commands · Ctrl+O to expand last result · Ctrl+C to exit
```

#### 2. Agent Reasoning & The Forge Engine
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

#### 3. Security Check (Confirmation)
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

#### 4. LSP Self-Correction Loop
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

**2. Workspace Initialization (/init)**
Launch mentask in any folder. If it's a new project, run `/init` to create the local isolation layer:
- **`.mentask/plugins/`**: Where forged tools are stored.
- **`.mentask/history/`**: Persistent turn-by-turn backups.
- **`.mentask/identity.md`**: Project-specific agent personality.

**3. Tool Discovery (MCP)**
Connect to any Model Context Protocol server. mentask will automatically introspect and bind its tools:

```text
 /mcp connect http://localhost:8080
 [✓] Connected to 'Postgres-MCP'. 12 new tools added to registry.
```

---

## Interactive Slash Commands

| Command | Action |
|:---|:---|
| `/help` | Show all commands and current settings. |
| `/init` | Initialize local project isolation (Workspaces). |
| `/model <name>` | Swap providers/models (Gemini, DeepSeek, Claude). |
| `/mode [auto\|manual]` | Toggle between full autonomy and safety confirmation. |
| `/trust [path]` | Authorize a directory for recursive file operations. |
| `/artifacts` | List or expand agent-generated tool artifacts. |
| `/undo` | Rollback the last file modification to its previous state. |
| `/stats` | View token consumption, USD cost, and execution metrics. |
| `/clear` | Wipe the active context buffer (history is preserved). |
| `/sessions` | List recent sessions available to resume. |
| `/exit` / `q` | Save session state and exit. |

---

## Hardened Security & Edge Cases

1. **The Trust Manager**: mentask is restricted to the current directory by default. Accessing outside paths requires `/trust <path>`.
2. **Context Snapping**: When sessions get too long, mentask proactive summarizes history into a "Snap" to stay within model limits while maintaining perfect "state awareness".
3. **Shell Limitations**: Interactive shell prompts (like `ssh` passwords) are not supported. Use non-interactive flags or keys.
4. **Keyring Fallback**: If your OS lacks a secure secret service (e.g. headless Linux), mentask falls back to `~/.mentask/settings.json` with a warning.
