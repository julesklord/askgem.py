# Project Memory: Mentask

## Status: v0.29.0 (Expansion Phase)
- **Current Goal:** Solidify the MCP (Model Context Protocol) integration and improve self-evolution via dynamic plugins.
- **Last Milestone:** Integrated models.dev for multi-provider support and reached v0.29.0 stable beta.

## Persistent Context
- **Stack:** Python 3.10+, `uv`, `ruff`, `pytest`, `tox`.
- **Core Architecture:** Orchestrator-based tool execution with security middleware.

## Active Tasks
- [ ] Refine the `forge_plugin` tool for more complex plugin generation.
- [ ] Expand the standard GitHub/GitLab MCP connectors.
- [ ] Implement advanced semantic search for codebase indexing.

## Technical Debt
- Some legacy tool definitions need to be migrated to the new schema in `src/mentask/tools/`.
- Unit test coverage for the LSP integration layer is below 80%.

## Notes
- *2026-05-18:* Jules Dev Standard v1.0 applied. Mentask is now the "Patient Zero" and benchmark for all other standardized repos.
- Consistently using `uv` for all dependency management.