# AI Agent Instructions for mentask

This document is the source of truth for AI agents operating in this repository.

---

## Development & Testing

Always use the following commands to ensure environment and code quality consistency:

- **Run all tests:** `tox`
- **CLI contract tests:** `pytest tests/cli -q`
- **Orchestration/LSP tests:** `pytest tests/test_orchestrator.py tests/test_lsp_integration.py -q`
- **Linting:** `ruff check src/ tests/`
- **Formatting:** `ruff format src/ tests/`
- **Dev Install:** `pip install -e ".[dev]"`

## Architectural Constraints & Conventions

- **Security (Crucial):** All file operations **must** validate paths through `TrustManager` and use dedicated tools in `src/mentask/tools/`.
- **Plugin Architecture:** mentask uses a 3-Layer Tool Architecture:
  1. **Core Tools (`src/mentask/tools/`):** Immutable base tools.
  2. **Community Tools (`MCP`):** External MCP server integrations.
  3. **Dynamic User Plugins (`.mentask/plugins/`):** Agent-forged, hot-reloaded plugins built on-the-fly using `forge_plugin`. Agents MUST use `forge_plugin` for repetitive tasks rather than generic bash scripts.
- **Communication:** Use Pydantic models for internal data exchange.
- **Async:** Use `async/await` for all I/O-bound operations (API calls, file I/O).
- **Structure:**
  - `src/`: Product code. Import from `src/mentask/`, not relative paths.
  - `tests/`: Unit/Integration tests only.
  - `root/`: Packaging, policies, core documentation.
- **Dependencies:** Composed explicitly (see `ChatAgentDependencies`). Do not add heavyweight external process boots to unit tests.

## References

- **Canonical Standards:** See [STANDARD.md](STANDARD.md) for project-wide conventions.
- **Detailed Architecture:** See [wiki/Architecture.md](wiki/Architecture.md).
- **Security:** See [SECURITY.md](SECURITY.md) for the threat model and trust requirements.
- **Project Roadmap:** See [ROADMAP.md](ROADMAP.md).
