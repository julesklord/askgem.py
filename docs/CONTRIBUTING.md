# Contributing to mentask

This guide provides instructions for development, testing, and change submission.

## Prerequisites

* **Python:** 3.10 or higher.
* **Git:** Required for version control.
* **Environment:** Use a virtual environment (`venv`, `conda`, or `uv`).

## Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/julesklord/mentask.git
cd mentask.py

# 2. Initialize environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Verify
mentask --help
```

## Repository Structure

| Path           | Purpose                  | Guidelines                              |
| -------------- | ------------------------ | --------------------------------------- |
| `src/mentask/` | Source code              | Maintain architectural boundaries.      |
| `tests/`       | Unit & integration tests | Maintain high coverage and determinism. |
| `scratch/`     | Experiments              | Safe to delete.                         |
| `docs/`        | User documentation       | Link to code; avoid duplication.        |
| `wiki/`        | Technical reference      | Architecture and API specifications.    |

## Pre-implementation

### 1. Architecture

Review [README.md](../) for the 4-layer architecture overview:

* **CLI**: Terminal interface.
* **Orchestration**: Think-Act-Observe loop.
* **Managers**: State and context management.
* **Safety**: Path validation and security.

### 2. Roadmap

Align new features with project priorities in [ROADMAP.md](https://github.com/TropicalDevApps/mentask.py/blob/main/ROADMAP.md).

### 3. Issues

Open an issue to discuss significant changes before implementation to ensure architectural alignment.

## Development Workflow

### Branching

1. Start from `main`.
2. Create a feature branch: `feat/feature-name` or `fix/bug-name`.

### Coding Standards

* **Style**: Enforced via Ruff.
* **Models**: Use Pydantic for internal communication.
* **Imports**: Use absolute imports (`from src.mentask...`).
* **Async**: Use `async/await` for I/O operations.
* **DI**: Use explicit dependency injection in manager classes.

### Testing

* **CLI**: `tests/cli/test_cli_main.py`.
* **Orchestration**: `tests/test_orchestrator.py`.
* **Integrations**: Mock external services in unit tests.

Execute tests locally:

```bash
pytest tests/ -v
tox  # Run across supported versions
```

### Commits

Write atomic commits with standard prefixes: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `ci:`. Keep the first line under 50 characters.

## Security

1. **Credentials**: Use `keyring` for API keys and tokens. Never commit secrets.
2. **Validation**: Route file operations through `TrustManager`.
3. **APIs**: Adhere to `SessionManager` retry patterns.

Refer to [SECURITY.md](../SECURITY.md) for the threat model.

## Pull Requests

### Submission Checklist

1. Execute the full test suite via `tox`.
2. Verify linting with `ruff check src/ tests/`.
3. Update documentation for behavioral changes.

### PR Requirements

* Clear title following commit conventions.
* Link to related issues.
* Summary of technical changes.
* Description of testing coverage.

## Post-merge

Updates follow semantic versioning. Refer to [ROADMAP.md](https://github.com/TropicalDevApps/mentask.py/blob/main/ROADMAP.md) for the release schedule.

## FAQ

* **Adding Tools**: Place in `src/mentask/tools/` and register in `src/mentask/agent/tools_registry.py`.
* **I18n**: Add strings to `src/mentask/locales/`.
* **System Prompts**: Modified via the Knowledge Hub markdown files.
* **CI Failures**: Check workflow logs in `.github/workflows/`.

## Code of Conduct

Maintain a professional and constructive environment.

Maintainer: [@julesklord](https://github.com/julesklord)
