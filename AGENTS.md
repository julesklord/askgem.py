# AI Agent Instructions for mentask

## Development Commands

Use `uv` (uv.lock present):
- **Setup:** `uv sync --all-extras --dev`
- **All tests:** `uv run pytest` or `tox`
- **CLI tests:** `uv run pytest tests/cli -q`
- **Orchestration/LSP:** `uv run pytest tests/test_orchestrator.py tests/test_lsp_integration.py -q`
- **Lint:** `uv run ruff check .`
- **Format:** `uv run ruff format .` (check: `--check`)

CI order: lint → format check → test (no typecheck).

## Key Constraints

- **Security:** All file operations must validate paths through `TrustManager` (`core/trust_manager.py`) and use tools in `src/mentask/tools/`.
- **Plugins:** 3-Layer Architecture:
  1. Core tools (`src/mentask/tools/`) - immutable
  2. MCP integrations (`core/mcp_manager.py`)
  3. Dynamic plugins (`.mentask/plugins/`) - use `forge_plugin` for repetitive tasks
- **Dependencies:** Explicit composition via `ChatAgentDependencies` (`agent/chat.py`). No heavyweight boots in unit tests.
- **Imports:** From `src/mentask/`, not relative paths.

## References

- Standards: [STANDARD.md](STANDARD.md)
- Architecture: [wiki/Architecture.md](wiki/Architecture.md)
- Security: [SECURITY.md](SECURITY.md)
