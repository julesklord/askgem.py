# Contributing to mentask

Thank you for your interest in contributing to **mentask**! This guide will help you get started with development, testing, and submitting your changes.

---

## Prerequisites

- **Python:** 3.10 or higher (validated: 3.10–3.13)
- **Git:** Ability to clone, branch, and push
- **Virtual environment:** Recommended (`venv`, `conda`, or similar)

---

## Setup Development Environment

```bash
# 1. Clone the repository
git clone https://github.com/julesklord/mentask.git
cd mentask.py

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install in development mode with dependencies
pip install -e ".[dev]"

# 4. Verify installation
mentask --help
```

---

## Repository Structure

Respect these boundaries to maintain code clarity:

| Path | Purpose | Rules |
|------|---------|-------|
| `src/mentask/` | Product code | No tests, no experiments |
| `tests/` | Unit & integration tests | No probes or disposable scripts |
| `scratch/` | Diagnostics & experiments | Temporary, safe to delete |
| `docs/` | User documentation | Link to code, don't duplicate |
| `wiki/` | Technical reference | Architecture, API details |

**Golden rule:** If you're unsure where code belongs, check [STANDARD.md](../STANDARD.md).

---

## Before You Code

### 1. Understand the Architecture

Read [AGENTS.md](../AGENTS.md) for a quick overview of the 4-layer architecture:
- **CLI** (`src/mentask/cli/`) — Terminal UI
- **Orchestration** (`src/mentask/agent/`) — Thinking → Action → Observation loop
- **Managers** (`src/mentask/agent/core/`) — Session, Context, Stream
- **Safety** (`src/mentask/core/`) — TrustManager, SecurityCheck, paths

For deep dives, see [wiki/Architecture.md](../wiki/Architecture.md).

### 2. Check the Roadmap

Before starting work, ensure your feature aligns with project priorities. See [ROADMAP.md](../ROADMAP.md).

### 3. Open an Issue (for significant work)

For non-trivial changes:
1. Describe the problem or feature
2. Explain the proposed approach
3. Ask for feedback before coding

This saves time and ensures alignment.

---

## Development Workflow

### Create a Feature Branch

```bash
# Start from main
git checkout main
git pull origin main

# Create a feature branch (use descriptive names)
git checkout -b feat/your-feature-name
# or
git checkout -b fix/your-bug-name
```

### Code & Style

**Code style:** Ruff (linter + formatter)

```bash
# Lint and check
ruff check src/ tests/

# Auto-format (if needed)
ruff format src/ tests/
```

**Key conventions:**
- Use **Pydantic models** for all internal communication (type safety)
- Imports: `from src/mentask/...` (not relative paths)
- Use `async/await` for I/O-bound operations (API, file reads)
- Manager classes compose dependencies explicitly (dependency injection)

### Writing Tests

**Testing standard** (see [AGENTS.md](../AGENTS.md#testing-standard)):

- **CLI entrypoints:** Have contract tests (see `tests/cli/test_cli_main.py`)
- **Orchestration flows:** Focused unit tests (see `tests/test_orchestrator.py`)
- **External integrations:** Isolated from unit tests; use mocking where practical
- **Determinism:** Preferred for CI reliability

**Example workflow:**

```bash
# Run all tests locally (single Python version)
pytest tests/ -v

# Run targeted tests for a changed surface
pytest tests/agent/test_chat_agent.py -v

# Run across all supported Python versions (3.10–3.13)
tox
```

### Making Commits

Write clear, atomic commits:

```bash
git add src/mentask/agent/orchestrator.py tests/test_orchestrator.py
git commit -m "refactor: decompose orchestrator loop into smaller helpers

- Extract tool execution logic into _execute_tool_with_validation()
- Extract thinking phase into _run_thinking_loop()
- Improves testability and reduces cognitive load

Fixes #123"
```

**Commit message conventions:**
- Use type prefixes: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `ci:`
- Reference GitHub issues when relevant
- Keep first line under 50 characters
- Add details in the body if needed

---

## Running Tests Locally

### Full Test Suite (recommended before PR)

```bash
# All environments (Python 3.10–3.13)
tox

# Or, single environment (faster for iteration)
pytest tests/ -v
```

### Targeted Testing

```bash
# CLI only
pytest tests/cli -q

# Orchestration & LSP
pytest tests/test_orchestrator.py tests/test_lsp_integration.py -q

# Specific test
pytest tests/agent/test_chat_agent.py::test_agent_handles_api_error -v
```

### Running with Coverage (optional)

```bash
pip install pytest-cov
pytest tests/ --cov=src/mentask --cov-report=html
# Open htmlcov/index.html in your browser
```

---

## Security Considerations

Before submitting:

1. **Credentials:** Never commit API keys, tokens, or passwords. Use `keyring` for sensitive data.
2. **Path validation:** Always validate paths through `TrustManager` before file operations.
3. **External APIs:** Ensure backoff and retry logic matches `SessionManager` patterns.
4. **Tests:** Don't mock external services in unit tests unless isolated as integration tests.

See [SECURITY.md](../SECURITY.md) for the full threat model.

---

## Submitting a Pull Request

### Before Pushing

1. **Run the full test suite:**
   ```bash
   tox
   ```

2. **Check lint:**
   ```bash
   ruff check src/ tests/
   ```

3. **Update docs if behavior changed:**
   - If feature: update `ROADMAP.md` status
   - If bug fix: document the issue in the PR body
   - If public API changed: update `wiki/API_Reference.md`

### Create the PR

```bash
git push origin feat/your-feature-name
# Then open a PR on GitHub with:
# - Clear title ("Fix authentication retry logic" or "Add multimodal image support")
# - Reference to related issue (#123)
# - Summary of changes
# - Testing notes (what you tested, edge cases covered)
```

### PR Guidelines

- **Title:** Use the same commit convention (`feat:`, `fix:`, etc.)
- **Body:** Link to related issues, explain the "why" not just the "what"
- **Size:** Keep PRs focused; split large changes into multiple PRs
- **Reviews:** Address feedback promptly; don't resolve conversations until approved

---

## After Merge

Your work will be included in the next release, which follows **semantic versioning**:

- **Patch** (0.13.4 → 0.13.5): Bug fixes
- **Minor** (0.13.4 → 0.14.0): New features
- **Major** (0.13.4 → 1.0.0): Breaking changes

Release schedule: See [ROADMAP.md](../ROADMAP.md) for milestones.

---

## Common Questions

### Q: Where do I add a new tool?
**A:** Tools live in `src/mentask/tools/`. Create a new file (e.g., `my_tool.py`), register it in the `ToolRegistry` (`src/mentask/agent/tools_registry.py`), and add tests in `tests/tools/test_my_tool.py`.

### Q: How do I add a new language string?
**A:** Use the i18n system in `src/mentask/locales/`. See `tests/core/test_i18n.py` for examples.

### Q: Can I modify the system prompt?
**A:** The Knowledge Hub (hierarchical markdown files) drives the system prompt. Behavioral rules are modular. See `src/mentask/core/identity_manager.py` and [wiki/Architecture.md](../wiki/Architecture.md#hierarchical-intelligence).

### Q: How do I test with the full Gemini API?
**A:** Set `GEMINI_API_KEY` env var and run with `--no-simulate`. For CI, use the mock session in tests.

### Q: What if my PR fails CI?
**A:** Review the workflow logs:
1. Check [python-ci.yml](../.github/workflows/python-ci.yml) — lint & test failures
2. Check [security.yml](../.github/workflows/security.yml) — gitleaks
3. Fix locally and push again

---

## Need Help?

- **Architecture questions?** Ask in an issue or PR comment; reference [AGENTS.md](../AGENTS.md)
- **Testing patterns?** See `tests/` examples or ask in a discussion
- **Security concerns?** Email the maintainer; don't open public issues

---

## Code of Conduct

This project is committed to providing a welcoming, inclusive environment. Be respectful, constructive, and professional in all interactions.

Maintainer: [@julesklord](https://github.com/julesklord)
