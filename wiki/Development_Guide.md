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

Tests are mapped inside `tests/` leveraging `pytest` and the **Simulation Layer** introduced in **v0.10.0**.

```bash
pytest tests/
```

mentask utilizes a `SimulationManager` to allow deterministic testing of agentic loops without incurring API costs. See `tests/integration/test_full_agent_loop.py` for reference.

Coverage ensures logic for:

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
