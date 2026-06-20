# Contributing to mentask

Thank you for your interest in contributing to **mentask**! This document covers everything you need to get started: development setup, coding conventions, commit style, and the pull request workflow.

---

## Table of Contents

1. [Development setup](#development-setup)
2. [Project structure](#project-structure)
3. [Running quality checks](#running-quality-checks)
4. [Writing tests](#writing-tests)
5. [Commit conventions](#commit-conventions)
6. [Pull request workflow](#pull-request-workflow)
7. [Code style guide](#code-style-guide)
8. [Reporting issues](#reporting-issues)

---

## Development setup

### Prerequisites

- Python **3.10 or newer**
- [uv](https://github.com/astral-sh/uv) — the project uses uv as its package manager and virtual-environment tool

### First-time setup

```bash
# Clone the repository
git clone https://github.com/julesklord/mentask.py.git
cd mentask.py

# Create a virtual environment and install all dependencies (including dev extras)
uv sync --all-extras

# Verify the installation
uv run mentask --version
```

That's it. The `uv sync` command creates `.venv/` and installs everything listed in `pyproject.toml`, including `pytest`, `ruff`, `mypy`, `bandit`, and `pytest-cov`.

---

## Project structure

```
mentask.py/
├── src/mentask/          # Application source code
│   ├── agent/            # ChatAgent, orchestrator, providers, schema
│   │   ├── chat.py       # Main ChatAgent entry point
│   │   ├── orchestrator.py
│   │   └── core/
│   │       ├── providers/ # Gemini, OpenAI, Ollama, CLIProvider, …
│   │       └── session_manager.py
│   ├── cli/              # CLI entry points and TUI renderer
│   ├── core/             # Infrastructure: config, RAG, MCP, security, …
│   └── tools/            # All built-in tool implementations
├── tests/
│   ├── agent/            # Unit tests for the agent layer
│   ├── cli/              # Unit tests for the CLI
│   ├── core/             # Unit tests for core modules
│   ├── tools/            # Unit tests for tools
│   └── integration/      # Integration tests (require external services)
├── pyproject.toml        # Project metadata, dependencies, tool config
├── Makefile              # Developer shortcuts
└── CONTRIBUTING.md       # ← you are here
```

---

## Running quality checks

All developer workflows are available as `make` targets:

| Command | What it does |
|---------|-------------|
| `make install` | Install all dependencies (including dev) |
| `make lint` | Run `ruff check` (lint) |
| `make format` | Run `ruff format` (auto-format) |
| `make test` | Run unit tests (excludes integration tests) |
| `make test-integration` | Run integration tests (requires Ollama) |
| `make coverage` | Run unit tests + print coverage report |
| `make coverage-html` | Generate HTML coverage report in `htmlcov/` |
| `make typecheck` | Run `mypy` on `src/` |
| `make security` | Run `bandit` + `pip-audit` |
| `make clean` | Remove build artefacts |

**Before submitting a PR**, please ensure all of these pass locally:

```bash
make lint typecheck test
```

---

## Writing tests

### Unit tests

- Lives in `tests/` mirroring the source layout (`tests/core/` for `src/mentask/core/`).
- Use **factory functions** instead of deeply-nested `MagicMock` chains. See `tests/agent/test_chat_agent.py` for reference.
- Each test should assert **one behaviour**.
- Name tests as `test_<unit>_<scenario>_<expected_outcome>`.
- Async tests work out of the box — `asyncio_mode = "auto"` is configured globally, so no `@pytest.mark.asyncio` is needed.

```python
# Good
async def test_setup_api_returns_false_when_session_has_no_key(default_deps):
    default_deps.session.setup_api = AsyncMock(return_value=False)
    agent = ChatAgent(dependencies=default_deps)
    assert await agent.setup_api(interactive=False) is False
```

### Integration tests

Integration tests that require external services (Ollama, real network, etc.) must live in `tests/integration/`.

The `tests/integration/conftest.py` automatically applies `@pytest.mark.integration` to every test in that directory, so they are **skipped** in regular `make test` runs and only executed with `make test-integration`.

### Coverage threshold

The CI enforces a minimum coverage of **75 %**. To check locally:

```bash
make coverage
```

---

## Commit conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

**Types:**

| Type | When to use |
|------|------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `refactor` | Code change that is neither a fix nor a feature |
| `perf` | A performance improvement |
| `test` | Adding or fixing tests |
| `docs` | Documentation only changes |
| `chore` | Build, CI, or dependency changes |
| `security` | Security fixes |

**Examples:**

```
feat(rag): add SQLite persistent cache to avoid re-indexing on startup

fix(mcp): use AsyncExitStack to guarantee connection cleanup on error

test(chat_agent): replace nested MagicMocks with factory fixtures

docs: add CONTRIBUTING.md
```

Keep the subject line ≤72 characters. Use the body to explain *why*, not *what*.

---

## Pull request workflow

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make your changes** following the code style guide below.

3. **Run the full check suite** locally:
   ```bash
   make lint typecheck test
   ```

4. **Push** your branch and open a **Draft PR** early if you want feedback on the approach.

5. Ensure all **CI checks pass**:
   - Lint & Format (ruff)
   - Type Check (mypy)
   - Security (bandit + pip-audit)
   - Tests + Coverage (≥ 75 %)

6. Request a review. At least **one approval** is required before merging.

7. **Squash-merge** is preferred to keep the git history clean.

---

## Code style guide

### General

- **Line length:** 120 characters (configured in `pyproject.toml` via `ruff`).
- **Formatter:** `ruff format` — run `make format` before committing.
- **Linter:** `ruff check` with rules `E, F, W, I, UP, B, SIM`.
- **Type annotations:** All public functions and methods must be fully annotated. Run `make typecheck` to verify.

### Python specifics

- Prefer `pathlib.Path` over `os.path` for filesystem operations.
- Use `logging.getLogger(__name__)` — never `print()` for diagnostic output.
- Use `contextlib.AsyncExitStack` for managing multiple async context managers.
- Add `# pragma: no cover` to branches that are genuinely untestable (e.g. platform-specific guards), not to hide missing tests.

### Docstrings

Use **Google Style** docstrings for all public classes, methods, and functions:

```python
def query(self, query_str: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Finds the most relevant chunks for a query.

    Args:
        query_str: Natural-language query string.
        top_k: Maximum number of results to return.

    Returns:
        List of chunk dicts with keys ``path``, ``content``,
        ``start_line``, ``end_line``, and ``score``.
    """
```

### Security

- Never call `subprocess` with shell=True unless the command is fully hardcoded.
- Use `SafeSubprocess` (in `core/subprocess_safety.py`) for all shell-level commands.
- Validate URLs with `is_safe_url()` (in `core/security.py`) before fetching.
- Raise exceptions from the project hierarchy (`core/exceptions.py`) — not bare `Exception`.

---

## Reporting issues

Please use [GitHub Issues](https://github.com/julesklord/mentask.py/issues) with the appropriate template:

- 🐛 **Bug report** — unexpected behaviour, crash, or regression.
- 💡 **Feature request** — new capability or improvement.
- 🔒 **Security vulnerability** — see [SECURITY.md](SECURITY.md) for the responsible disclosure process.

When filing a bug, always include:
- mentask version (`mentask --version`)
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Expected vs. actual behaviour
