# Usage

Launch `mentask` simply via standard terminal hook in the root:

```bash
mentask
```

### Console Output Examples

#### 1. Startup & Welcome
When you launch mentask, you'll see a professional header with the version and current model:

```text
 ──────────────── mentask v0.18.7 • gemini-2.0-flash • manual ───────────────── 
                       Type /help for commands • Ctrl+C to exit                       

 @julesklord
 ──────────────────────────────────────────────────────────────────────────────
```

#### 2. Agent Reasoning & Response
mentask displays its thinking process with a subtle vertical line before delivering the final answer:

```text
 ✨ @mentask
  │ I will check the dependencies in pyproject.toml to understand the project structure.
  │ Then I'll summarize the main libraries used.

  ⚙  EXECUTING: read_file (filePath=G:/DEVELOPMENT/mentask.py/pyproject.toml)
  [✓ tool output ...]

  Based on your `pyproject.toml`, the project uses:
  - google-genai: For Gemini API integration.
  - rich: For the professional TUI rendering.
  - pydantic: For data validation and schemas.
```

#### 3. Security Check (Confirmation)
In `manual` mode (default), mentask will ask for permission before performing destructive actions:

```text
 🛡  SECURITY CHECK
 mentask wants to use edit_file with these parameters:
  filePath: G:/DEVELOPMENT/mentask.py/src/utils.py
  oldString: [dim]def old_func():[/dim]
  newString:
  ╭────────────────────────────────────────────────────────────────────────────╮
  │ def new_func():                                                            │
  │     print("Refactored!")                                                   │
  ╰────────────────────────────────────────────────────────────────────────────╯

 Allow execution? (y/n): 
```

#### 4. Turn Divider & Metrics
After each turn, a subtle divider shows token usage and cost:

```text
 ───────────────── 1.2k tokens • $0.0004 • 4.2s ──────────────────
```

---

## Common Workflows

**1. Resuming a Session [v0.16.0]**
Every session has a unique ID. You can resume exactly where you left off:

```bash
mentask 2026-04-20_15-30-10_x8y9z0
```

**2. Workspace Initialization**
When you launch mentask in a folder for the first time, it checks for a `.mentask/` directory.

- If not found, it asks: *"Initialize Workspace in CWD?"*
- Selecting **Yes** creates a local isolation layer for history, memory, and project-specific blueprints.

**3. Trusting External Directories**
If you need the agent to read or write files outside your current project.

```text
 @julesklord
 /trust G:/COMMON_LIBS

 [✓] Path 'G:/COMMON_LIBS' added to trusted whitelist.
```

---

## Interactive Slash Commands

| Command | Action |
|---------|--------|
| `/help` | Show all commands and current settings. |
| `/init` | Initialize local project isolation and configuration. |
| `/model <name>` | Swap Gemini models (e.g., `/model gemini-2.0-flash`). |
| `/mode [auto/manual]` | Toggle safety confirmation prompts. |
| `/trust [path]` | Authorize a directory for file operations. |
| `/untrust` | Remove authorization from current directory. |
| `/theme [name]` | Switch between premium UI themes. |
| `/prompt` | Customize the interactive prompt style. |
| `/clear` | Wipe context window (history preserved on disk). |
| `/usage` | Detailed token consumption and estimated USD cost. |
| `/stats` | Session summary (messages, tools, files edited). |
| `/sessions` | List recent sessions available to resume. |
| `/load <id>` | Load a specific saved session. |
| `/undo` | Rollback the last file modification. |
| `/artifacts` | List or expand tool results. |
| `/exit` / `q` | Save and exit the session. |

---

## Edge Cases and Known Limitations

1. **Cross-Drive Blocks:** Without an explicit `/trust` command, mentask will fail with a `SecurityError` when attempting to access files on a different drive letter (Windows).
2. **Context Compression:** While mentask manages context efficiently, extremely large file reads in a single turn might still hit model limits.
3. **Shell Interactions:** Interactive shell commands (like `git add -i`) are not supported and may hang. Always use non-interactive flags (e.g., `git add .`).
1. **Cross-Drive Blocks:** Without an explicit `/trust` command, mentask will fail with a `SecurityError` when attempting to access files on a different drive letter (Windows).
2. **Keyring Access:** On some Linux distros without a D-Bus secret service, mentask will fall back to `~/.mentask/settings.json` for key storage.
3. **Context Explosion:** Even with proactive summarization, massive file reads (e.g., >50 files) in a single turn may approach the Gemini context window limits.
>>
