# Agent SOP: Mentask Core Operations

## Operational Mandates
- **Tool-Centric Action:** Always prefer using a tool to investigate or modify the codebase over speculating.
- **Trust Verification:** Every file write or shell command must be preceded by a path validation check via `TrustManager`.
- **Ecosystem Hygiene:** Maintain the `uv` environment. Run `ruff` before every commit.
- **Documentation Parity:** Ensure `CHANGELOG.md` and `docs/MEMORY.md` are updated after every feature or significant fix.

## Core Workflows
1. **Tool Creation:**
   - Define tools in `src/mentask/tools/` for core functionality.
   - Use the `forge_plugin` tool for dynamic, project-specific plugins in `.mentask/plugins/`.
2. **Feature Implementation:**
   - Research -> Strategy -> Execution (Plan-Act-Validate).
   - Use `tests/` for verification (pytest).
3. **Release Management:**
   - Update `VERSION`.
   - Update `CHANGELOG.md`.
   - Update `RELEASE_NOTES.md`.

## Plugin Architecture (3-Layer)
- **Layer 1 (Core):** Immutable, high-integrity tools in the main package.
- **Layer 2 (MCP):** Standardized external integrations.
- **Layer 3 (Dynamic):** User-defined or agent-generated plugins in `.mentask/`.

## Related Docs
- [Project Identity](./IDENTITY.md)
- [Project Soul](./SOUL.md)
- [Wiki Index](./wiki/index.md)
- [Security Standard](./wiki/security.md)