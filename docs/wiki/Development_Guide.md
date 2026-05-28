# Development Guide

Thank you for contributing to mentask.

## Setting up your Dev Environment

1. Fork the repo and clone.
2. Initialize and bind virtual mappings:

```bash
python -m venv venv
# On Windows: venv\Scripts\activate
source venv/bin/activate
pip install -e ".[dev]"
```

## Testing Protocol

Tests are mapped inside `tests/` leveraging `pytest` and the **Simulation Layer**.

### Local LLM Testing (Standard)

As of **v0.25.0**, all tests involving local models **MUST** use **Ollama** with the **qwen3.5** model. 

The test suite includes a session-wide fixture (`tests/conftest.py`) that:

1. Automatically starts the Ollama server if it's not running.
2. Pulls the mandated `qwen3.5` model.
3. Shuts down the server after the tests finish.

To run tests locally:
```bash
pytest tests/
```

### Coverage ensures logic for:

* **Core Managers:** `test_session_manager.py`, `test_context_manager.py`, `test_stream_processor.py`.
* **Security:** `test_security.py` (Risk analysis and pattern matching).
* **Tools:** `test_file_tools.py`, `test_system_tools.py`.

> [!IMPORTANT]
> Because `mentask` is an autonomous tool interacting with hardware endpoints, any integration tools merged **must** handle timeout bounds or test mock restrictions explicitly to avoid rogue executions.

## Contribution Conventions

* **Branches:** `feat/<name>`, `bugfix/<name>`, `refactor/<name>`.
* **Commits:** Prefix formatting (e.g. `feat: add glob search tool`).
* **PR Rules:** Ensure `pytest` completes without assertions failing and `ruff check` passes `100%` on changed blobs.

## Modifying the Architecture

As of version **0.10.0**, the Cognitive Layer is decentralized. When injecting new logic:

1. **New Tools:** Build bounded generic logic in `src/mentask/tools/` and bind them to `ToolDispatcher`.
2. **State Logic:** Place specialized management logic inside `src/mentask/agent/core/`.
3. **Safety Logic:** Update `src/mentask/core/security.py` if adding tools that interact with sensitive OS resources.
