Plan: Code Editing System Improvements

### Phase 1 — Safety Infrastructure (core `file_tools.py`, `pyproject.toml`)

**1. File locking with `portalocker`**
- Add `portalocker` to `pyproject.toml` dependencies
- Lock around `_atomic_write`, `_create_backup`, history saves, working_memory writes, memory.md modifications
- Use `portalocker.Lock(file, timeout=30)` with advisory locks — cross-platform (Windows + Unix)
- Only one writer at a time per file; readers can still read freely
- Effort: ~1-2 files, ~50-80 LOC. Low risk, high safety gain.

**2. Content-addressing (stale-read detection)**
- When `read_file` is called, compute `git hash-object` of the content and include the hash in the output (e.g., `[content-hash: abc123]`)
- When `edit_file` is called, optionally accept a `known_hash` parameter
- If provided, compute current hash and compare — warn if mismatch (file changed since read)
- Uses `git hash-object --stdin` via subprocess (no filesystem writes); falls back silently if not in a git repo
- Effort: ~1 file, ~30-50 LOC. Low risk, catches a real class of errors.

### Phase 2 — Editor Power (core `file_tools.py` + agent `file_tools.py`)

**3. New edit modes: `line_range` and `semantic`**

Current `edit_file(path, find_text, replace_text)` is purely find-replace. Add two optional parameters:

**`line_range` mode** (`start_line`, `end_line`):
```
edit_file(path, find_text="", replace_text="...", start_line=42, end_line=55)
```
Replaces lines 42-55 with `replace_text`. If `find_text` is also provided, validates find_text exists on those specific lines first (belt-and-suspenders).

**`semantic` mode** (`semantic="function"` or `semantic="class"`):
```
edit_file(path, find_text="def calculate_total", replace_text="...", semantic="function")
```
Parses the AST to find the exact extent of the function/class containing `find_text`, then replaces the full body. No more off-by-one errors with function boundaries.

Implementation:
- `line_range`: splitlines, slice, replace, join
- `semantic`: use `ast` to find `ast.FunctionDef`/`ast.ClassDef`, extract source lines via `ast.get_source_segment()` or line numbers

The `EditFileInput` Pydantic schema gets new optional fields. Backward compatible — existing find-replace calls continue unchanged.

Effort: ~2 files, ~100-150 LOC. Medium risk (AST edge cases).

**4. Diff aggregation (preview all edits at once)**
- New method `preview_edits(edits: list[dict]) -> str` that shows a unified diff combining all pending changes
- Apply edits to an in-memory copy, then diff once against the original
- The `EditFileTool` agent wrapper already shows per-edit diffs — this aggregates them for multi-file batches
- Useful for batch edit scenarios (e.g., refactoring across 5 files)
- Effort: ~1 file, ~40-60 LOC. Low risk.

### Phase 3 — LSP Maturity (`lsp_client.py`, `execution.py`)

**5. LSP diagnostics as true async feedback (not appended to tool result)**

Current behavior: `append_lsp_diagnostics()` re-reads the file on disk, sends `didOpen`, waits 0.5s, then appends to the tool result string. Problems:
- LSP check is a separate blocking step after the edit result is already computed
- Only one shot at diagnostics (no incremental updates)
- No code actions or formatting

Improvements:
- Replace `didOpen` with `didChange` after each edit (no need to re-read from disk — pass the content directly)
- Implement `textDocument/codeAction` to offer auto-fixes (e.g., "Remove unused import")
- Implement `textDocument/formatting` for auto-format after edits (`ruff format`)
- Make diagnostics injection truly non-blocking: send diagnostics as a separate message/tool result after the edit result, rather than appending to it
- Effort: ~1-2 files, ~100-150 LOC (mostly LSPClient additions)

**6. Git pre-edit snapshot**
- Before an edit session begins, auto-stash/commit dirty state: `git stash push -m "mentask-pre-edit-{timestamp}"`
- On session end, show clean diff since snapshot
- Only active when in a git repo
- Respects existing `.mentask/` critical directories
- Effort: ~1 file, ~50-80 LOC. Medium risk (git stash interaction).

---

### Summary Table

| # | Feature | Files | LOC | Risk | Impact |
|---|---------|-------|-----|------|--------|
| 1 | File locking | `file_tools.py`, `pyproject.toml` | ~80 | Low | High |
| 2 | Content-addressing | `file_tools.py` | ~50 | Low | Medium |
| 3 | Edit modes (line_range, semantic) | `file_tools.py` + agent wrapper | ~150 | Medium | High |
| 4 | Diff aggregation | `file_tools.py` | ~60 | Low | Medium |
| 5 | LSP maturity | `lsp_client.py`, `execution.py` | ~150 | Medium | High |
| 6 | Git pre-edit snapshots | new file or `execution.py` | ~80 | Medium | Medium |

The features are independent — any subset can be done in any order. **Phase 1** is pure safety with no API change. **Phase 2** adds the most visible editing power. **Phase 3** polishes the feedback loop.
