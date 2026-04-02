# Development Guide

Thank you for contributing to AskGem.

## Setting up your Dev Environment

1. Fork the repo and clone.
2. Initialize and bind virtual mappings:

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Testing Protocol

Tests are mapped inside `tests/` leveraging `pytest`.

```bash
pytest tests/
```

Coverage currently ensures isolated paths for:

* `test_config_manager.py` (Mocked data structures)
* `test_file_tools.py` (Isolated tmp_path logic testing block rewrites)
* `test_system_tools.py` (Shell abstractions execution points)

> [!IMPORTANT]
> Because `askgem` is an autonomous tool interacting with hardware endpoints, any integration tools merged **must** handle timeout bounds or test mock restrictions explicitly to avoid rogue executions.

## Contribution Conventions

* **Branches:** `feat/<name>`, `bugfix/<name>`, `refactor/<name>`.
* **Commits:** Prefix formatting (e.g. `feat: add glob search tool`).
* **PR Rules:** Ensure `pytest` completes without assertions failing and `ruff check` passes `100%` on changed blobs.

## Modifying the Architecture

When injecting new tools to `ChatAgent`:

1. Build the bounded generic logic in `src/askgem/tools/`.
2. Ensure strict `str` return output payload formatting.
3. Only bind the tool object list references to `ChatAgent._tools`. DO NOT build the logic natively inside `chat.py`.
