# Security and Robustness Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement path traversal protection, robust keyring fallback, and tool result truncation to ensure a "Sandboxed" and stable agent experience.

**Architecture:** 
- Centralized path validation in `file_tools.py` to enforce CWD constraints.
- Try/except blocks around `keyring` operations with fallbacks to environment variables and interactive prompts in `config_manager.py`.
- Middleware-style truncation in `ToolDispatcher` to prevent context window overflow.

**Tech Stack:** Python, `os`, `keyring`, `rich`, `asyncio`

---

### Task 1: Path Traversal Protection (Security)

**Files:**
- Modify: `src/askgem/tools/file_tools.py`

- [ ] **Step 1: Implement `_ensure_safe_path` helper function**

```python
def _ensure_safe_path(path: str) -> str:
    """Ensures that the provided path is within the current working directory.
    
    Args:
        path: The path to validate.
        
    Returns:
        The absolute path if safe.
        
    Raises:
        PermissionError: If the path is outside the CWD.
    """
    abs_path = os.path.abspath(path)
    cwd = os.getcwd()
    if not abs_path.startswith(cwd):
        raise PermissionError(f"Access denied: Path '{path}' is outside the allowed directory.")
    return abs_path
```

- [ ] **Step 2: Apply `_ensure_safe_path` to `read_file`**

```python
# Before
# if not os.path.exists(path): ...

# After
try:
    path = _ensure_safe_path(path)
except PermissionError as e:
    return str(e)
```

- [ ] **Step 3: Apply `_ensure_safe_path` to `edit_file`**
Apply it to `path`.

- [ ] **Step 4: Apply `_ensure_safe_path` to `diff_file`**
Apply it to `path`.

- [ ] **Step 5: Apply `_ensure_safe_path` to `list_directory`**
Apply it to `path`.

- [ ] **Step 6: Apply `_ensure_safe_path` to `delete_file`**
Apply it to `path`.

- [ ] **Step 7: Apply `_ensure_safe_path` to `move_file`**
Apply it to both `source` and `destination`.

- [ ] **Step 8: Run existing tests to ensure no regressions**
Run: `pytest tests/test_file_tools.py` (Verify if it exists)

- [ ] **Step 9: Commit as Snuggles**
```bash
git add src/askgem/tools/file_tools.py
git commit --author="Snuggles <snuggles@askgem.ai>" -m "sec: implement path traversal protection in file tools"
```

### Task 2: Robust Keyring Fallback (Robustness)

**Files:**
- Modify: `src/askgem/core/config_manager.py`

- [ ] **Step 1: Update `load_settings` with robust keyring fallback**

```python
        # Load sensitive keys from keyring
        try:
            search_key = keyring.get_password(self.SERVICE_NAME, "GOOGLE_SEARCH_API_KEY")
            if search_key:
                self.settings["google_search_api_key"] = search_key
        except Exception as e:
            self.console.print(f"[error][!] Error accessing keyring for search key: {e}[/error]")
            # Fallback to env var if keyring fails
            env_search_key = os.getenv("GOOGLE_SEARCH_API_KEY")
            if env_search_key:
                self.settings["google_search_api_key"] = env_search_key
```

- [ ] **Step 2: Update `save_settings` with robust keyring fallback**

- [ ] **Step 3: Update `load_api_key` with robust keyring fallback**

- [ ] **Step 4: Update `save_api_key` with robust keyring fallback**

- [ ] **Step 5: Commit as Snuggles**
```bash
git add src/askgem/core/config_manager.py
git commit --author="Snuggles <snuggles@askgem.ai>" -m "fix: add robust keyring fallback in config manager"
```

### Task 3: Tool Result Truncation (Limits)

**Files:**
- Modify: `src/askgem/agent/tools_registry.py`

- [ ] **Step 1: Implement truncation logic in `ToolDispatcher.execute`**

```python
            result = await self._dispatch(tool_name, args)
            
            # Truncate result if it exceeds 10,000 characters
            MAX_CHARS = 10_000
            if isinstance(result, str) and len(result) > MAX_CHARS:
                result = result[:MAX_CHARS] + f"\n\n... [!] Result truncated at {MAX_CHARS} characters to avoid context overflow."

            if self.logger:
                # ...
```

- [ ] **Step 2: Commit as Snuggles**
```bash
git add src/askgem/agent/tools_registry.py
git commit --author="Snuggles <snuggles@askgem.ai>" -m "feat: truncate tool results to 10k characters"
```

### Task 4: Documentation Update

**Files:**
- Modify: `README.md` (or relevant doc file)

- [ ] **Step 1: Mention "Sandboxed" status**
Add a section about security or update existing one.

- [ ] **Step 2: Commit as Snuggles**
```bash
git add README.md
git commit --author="Snuggles <snuggles@askgem.ai>" -m "docs: update README to mention sandboxed agent"
```
