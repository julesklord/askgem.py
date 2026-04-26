# Testing Skill: pytest & tox for mentask

## Purpose

This skill provides best practices for writing effective unit and integration tests in the **mentask** codebase using **pytest** and **tox**. It ensures consistent test patterns, proper mocking strategies, and deterministic CI behavior.

---

## When to Use This Skill

✅ Writing new test files for features or bug fixes  
✅ Adding tests to existing modules  
✅ Debugging test failures in CI  
✅ Refactoring tests for clarity and coverage  
✅ Deciding between unit vs. integration tests  

---

## Testing Standard for mentask

### Golden Rules

1. **CLI entrypoints have contract tests** — See `tests/cli/test_cli_main.py`
2. **Orchestration flows have focused unit tests** — See `tests/test_orchestrator.py`
3. **External integrations are isolated from unit tests** — Use mocking where practical
4. **CI prefers deterministic/mocked tests** — No heavy external process boots
5. **When behavior changes, update tests immediately** — Don't tolerate stale coverage

---

## Test File Organization

```
tests/
├── __init__.py
├── test_*.py                 # Top-level tests (orchestrator, session, LSP)
│
├── agent/
│   ├── test_chat_agent.py    # Agent coordination tests
│   ├── test_session_manager.py
│   ├── test_context_manager.py
│   └── test_tools_registry.py
│
├── cli/
│   ├── test_cli_main.py      # CLI contract tests (HIGHEST priority)
│   └── test_dashboard_smoke.py
│
├── core/
│   ├── test_identity_manager.py
│   ├── test_trust.py         # Security validation tests
│   ├── test_security.py      # Path traversal, risk analysis
│   ├── test_config_manager.py
│   ├── test_history_manager.py
│   └── test_i18n.py
│
├── tools/
│   ├── test_file_tools.py
│   ├── test_system_tools.py
│   ├── test_web_tools.py
│   └── test_search_tools.py
│
└── integration/
    ├── test_full_agent_loop.py     # End-to-end flows (use sparingly)
    └── test_workspace_flow.py
```

**Principle:** Mirror `src/` structure; put tests near the code they validate.

---

## Test Patterns by Layer

### 1. CLI Tests (Highest Priority)

**Purpose:** Verify that the user-facing CLI works end-to-end.

```python
import pytest
from mentask.cli.main import run_chatbot

def test_cli_accepts_valid_api_key(monkeypatch, tmp_path):
    """Contract test: CLI initializes with valid Gemini API key."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
    monkeypatch.setenv("mentask_WORKSPACE_ROOT", str(tmp_path))
    
    # The CLI should boot without error
    result = run_chatbot([])  # or however invoked
    assert result is not None

def test_cli_rejects_missing_api_key(monkeypatch, tmp_path):
    """Contract test: CLI fails gracefully without API key."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("mentask_WORKSPACE_ROOT", str(tmp_path))
    
    with pytest.raises(SystemExit):
        run_chatbot([])
```

**Key principles:**
- Test **actual user workflows**, not internal implementation
- Use `monkeypatch` for env vars (not direct assignment)
- Use `tmp_path` fixture for temporary workspaces
- Assert on exit codes, console output, or side effects (files created)
- **Avoid mocking the entire orchestrator** — let it run (unless very slow)

---

### 2. Orchestration Tests (Core Logic)

**Purpose:** Verify the *Thinking → Action → Observation* loop works correctly.

```python
import pytest
from mentask.agent.orchestrator import AgentOrchestrator
from mentask.agent.core.session import SessionManager
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_orchestrator_extracts_tool_calls():
    """Unit test: Orchestrator correctly extracts tool calls from LLM response."""
    # Setup mocks
    session = AsyncMock(spec=SessionManager)
    session.stream_thinking.return_value = AsyncIterator([
        # Simulated streaming response with tool call
        {"type": "text", "text": "I'll read the file."},
        {
            "type": "tool_use",
            "id": "call_123",
            "name": "read_file",
            "input": {"path": "/workspace/test.py"}
        }
    ])
    
    orchestrator = AgentOrchestrator(session=session)
    result = await orchestrator.run_thinking_phase("Read test.py for me")
    
    assert result["tool_calls"] is not None
    assert result["tool_calls"][0]["name"] == "read_file"

@pytest.mark.asyncio
async def test_orchestrator_handles_api_rate_limit(monkeypatch):
    """Unit test: Orchestrator retries on 429 API error."""
    session = AsyncMock(spec=SessionManager)
    
    # Simulate 429, then success
    session.stream_thinking.side_effect = [
        Exception("429 Rate limit exceeded"),
        AsyncIterator([{"type": "text", "text": "Retry successful"}])
    ]
    
    orchestrator = AgentOrchestrator(session=session)
    result = await orchestrator.run_thinking_phase("Any message")
    
    # Should retry (backoff handled by SessionManager)
    assert result is not None
```

**Key principles:**
- Use `@pytest.mark.asyncio` for async tests
- **Mock external dependencies** (SessionManager, API calls)
- Test **error paths explicitly** (rate limits, malformed responses)
- Verify **retry logic and backoff** for resilience
- Keep tests focused on **one responsibility**

---

### 3. Manager Tests (State & Lifecycle)

**Purpose:** Verify managers handle their domain correctly (session, context, trust).

```python
import pytest
from mentask.core.trust_manager import TrustManager
from mentask.core.security import SecurityCheck
from pathlib import Path

def test_trust_manager_blocks_traversal_attack(tmp_path):
    """Security test: TrustManager prevents directory traversal."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    trusted = TrustManager(workspace_root=workspace)
    
    # Attempt to escape workspace
    malicious_path = workspace / ".." / ".." / "etc" / "passwd"
    
    with pytest.raises(SecurityViolation):
        trusted.validate(malicious_path)

def test_context_manager_discovers_python_project(tmp_path):
    """Blueprint test: ContextManager identifies Python project structure."""
    # Setup a minimal Python project
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")
    
    from mentask.agent.core.context import ContextManager
    context = ContextManager(workspace_root=tmp_path)
    
    blueprint = context.scan_project()
    
    assert blueprint.project_type == "python"
    assert "tests" in blueprint.key_directories
    assert "pyproject.toml" in blueprint.config_files
```

**Key principles:**
- Test **boundary conditions** (missing files, malformed configs)
- Use `tmp_path` for filesystem operations (auto-cleanup)
- For **path validation**, test both **valid and invalid** paths
- For **config parsing**, test **valid and invalid** formats
- Mock **I/O-heavy operations** (file reads, API calls)

---

### 4. Tool Tests (File Operations, Commands)

**Purpose:** Verify tools correctly read, write, and validate.

```python
import pytest
from mentask.tools.file_tools import FileTools

def test_file_tools_reads_existing_file(tmp_path):
    """Integration test: FileTools.read_file works for existing files."""
    test_file = tmp_path / "test.py"
    test_file.write_text("def hello():\n    print('world')")
    
    tools = FileTools(workspace_root=tmp_path, trust_manager=MagicMock())
    content = tools.read_file(str(test_file))
    
    assert "def hello" in content
    assert "print" in content

def test_file_tools_rejects_traversal(tmp_path):
    """Security test: FileTools prevents path traversal attacks."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    tools = FileTools(workspace_root=workspace, trust_manager=TrustManager(workspace))
    
    with pytest.raises(SecurityViolation):
        # Attempt to read outside workspace
        tools.read_file("../../etc/passwd")

def test_file_tools_creates_backup(tmp_path):
    """Side-effect test: FileTools creates .bkp before modifying."""
    test_file = tmp_path / "test.py"
    test_file.write_text("old content")
    
    tools = FileTools(workspace_root=tmp_path, trust_manager=MagicMock())
    tools.edit_file(str(test_file), "new content")
    
    backup = tmp_path / "test.py.bkp"
    assert backup.exists()
    assert backup.read_text() == "old content"
```

**Key principles:**
- Test both **success and failure** paths
- Verify **side effects** (files created, backups made, logs written)
- Test **security boundaries** (path validation, trust checks)
- Use `tmp_path` to isolate tests (no pollution)

---

## Mocking Strategy

### When to Mock

✅ **Mock these:**
- External APIs (Gemini, web searches) → Use `AsyncMock`
- File I/O in unit tests → Use `tmp_path` or `monkeypatch`
- System calls (`subprocess.run`) → Use `MagicMock`
- Time-dependent logic (`datetime.now`) → Use `monkeypatch`

❌ **Don't mock these:**
- Pydantic models (validate types directly)
- Manager composition (let dependencies be real if fast)
- CLI entrypoints (run them end-to-end)
- Your own code (test behavior, not mocks)

### Mock Patterns

```python
from unittest.mock import AsyncMock, MagicMock, patch

# Pattern 1: AsyncMock for async methods
@pytest.mark.asyncio
async def test_with_async_mock():
    mock_api = AsyncMock()
    mock_api.call_api.return_value = {"status": "ok"}
    
    result = await mock_api.call_api()
    assert result["status"] == "ok"

# Pattern 2: side_effect for sequences
@pytest.mark.asyncio
async def test_retry_on_error():
    mock_api = AsyncMock()
    mock_api.call_api.side_effect = [
        Exception("Rate limited"),
        {"status": "ok"}  # Retry succeeds
    ]
    
    # Your retry logic should eventually succeed

# Pattern 3: patch for imports
def test_with_patch():
    with patch("mentask.tools.system_tools.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="output")
        # Test code using subprocess

# Pattern 4: monkeypatch for env vars & attributes
def test_with_monkeypatch(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-123")
    monkeypatch.setattr("mentask.core.paths.HOME", "/tmp/home")
    # Test code using those values
```

---

## Running Tests Locally

### Full Suite (Before Pushing)

```bash
# All Python versions (3.10–3.13)
tox

# Or single environment (faster for iteration)
pytest tests/ -v

# Lint + tests
ruff check .
pytest tests/
```

### Targeted Testing

```bash
# CLI only
pytest tests/cli -q

# Specific test
pytest tests/agent/test_chat_agent.py::test_agent_handles_api_error -v

# With coverage report
pytest tests/ --cov=src/mentask --cov-report=html
```

### Debugging Failed Tests

```bash
# Verbose output with print statements
pytest tests/test_orchestrator.py -v -s

# Stop at first failure
pytest tests/ -x

# Run last 3 tests that failed
pytest tests/ --lf --last-failed -n 3

# Drop into debugger on failure
pytest tests/ --pdb
```

---

## Test Data & Fixtures

### Reusable Fixtures

```python
# conftest.py (shared fixtures)
import pytest
from pathlib import Path

@pytest.fixture
def workspace_root(tmp_path):
    """Provides a temporary workspace root."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "src").mkdir()
    return workspace

@pytest.fixture
def mock_session(mocker):
    """Provides a mocked SessionManager."""
    session = mocker.AsyncMock()
    session.stream_thinking.return_value = AsyncIterator([
        {"type": "text", "text": "Testing"}
    ])
    return session

@pytest.fixture
def trust_manager(workspace_root):
    """Provides a TrustManager for the workspace."""
    from mentask.core.trust_manager import TrustManager
    return TrustManager(workspace_root=workspace_root)
```

Use these in tests:

```python
def test_something(workspace_root, trust_manager):
    """Test using fixtures."""
    assert trust_manager.workspace_root == workspace_root
```

---

## Common Test Mistakes

### ❌ Mistake 1: Tests that Depend on Execution Order

```python
# BAD: test_b depends on test_a's state
def test_a():
    global counter
    counter = 0

def test_b():
    assert counter == 0  # Breaks if test_a doesn't run first
```

**Fix:** Each test is independent.

```python
# GOOD: Each test sets up its own state
def test_a():
    counter = 0
    assert counter == 0

def test_b():
    counter = 0
    assert counter == 0
```

---

### ❌ Mistake 2: Over-Mocking

```python
# BAD: Mocking your own code defeats the purpose
def test_orchestrator():
    orchestrator = MagicMock()  # This tests nothing!
    orchestrator.run.return_value = {"result": "ok"}
    assert orchestrator.run() == {"result": "ok"}
```

**Fix:** Test real code, mock dependencies.

```python
# GOOD: Mock SessionManager, test OrchestrationManager
@pytest.mark.asyncio
async def test_orchestrator(mocker):
    mock_session = mocker.AsyncMock()
    orchestrator = AgentOrchestrator(session=mock_session)
    
    result = await orchestrator.run_thinking_phase("Test")
    assert result is not None  # Tests real orchestrator logic
```

---

### ❌ Mistake 3: Flaky Tests (Non-Deterministic)

```python
# BAD: Test depends on system time or random values
def test_api_response_time():
    start = time.time()
    result = call_api()
    elapsed = time.time() - start
    assert elapsed < 1.0  # Fails on slow systems
```

**Fix:** Mock time or avoid time-dependent assertions.

```python
# GOOD: Mock time or test logic independently
def test_api_response_parsing():
    response = '{"status": "ok"}'
    result = parse_api_response(response)
    assert result["status"] == "ok"  # Deterministic
```

---

### ❌ Mistake 4: Bloated Test Setup

```python
# BAD: 50 lines of setup for a 5-line test
def test_something():
    # ... 40 lines of setup ...
    assert result == "ok"
```

**Fix:** Use fixtures or break into smaller tests.

```python
# GOOD: Fixtures + focused test
def test_something(workspace_root, mock_session):
    # Already set up, just test one thing
    assert result == "ok"
```

---

## Integration Tests (Use Sparingly)

**Integration tests** exercise multiple layers together. Use **only when necessary**:

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_agent_loop_with_file_read(tmp_path):
    """Integration test: Agent reads a file via orchestrator."""
    # Setup real workspace
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')")
    
    # Real orchestrator, real managers, mocked Gemini API
    session = SessionManager(api_key="test")
    session.mock_responses = [
        {"tool_use": {"name": "read_file", "input": {"path": str(test_file)}}}
    ]
    
    orchestrator = AgentOrchestrator(session=session)
    result = await orchestrator.run_turn("Read test.py")
    
    assert "hello" in result["observations"]
```

**Key principle:** Integration tests are **slow** and **fragile**. Prefer unit tests with mocks.

---

## Continuous Integration (CI)

### Pre-Push Checklist

```bash
# 1. Lint
ruff check src/ tests/

# 2. Format (optional)
ruff format src/ tests/

# 3. Run tests locally
pytest tests/ -v

# 4. Run across all Python versions
tox

# 5. No secrets in git history
git log --all -S GEMINI_API_KEY
```

### If CI Fails

1. **Lint failure?** → `ruff check .` locally, fix, retry
2. **Test failure?** → `pytest tests/ -v` locally, reproduce, fix
3. **Audit failure?** → `pip-audit` locally, review CVE, update deps

---

## Summary: Testing Checklist

- [ ] Test is **independent** (no setup from other tests)
- [ ] Test **mocks external dependencies** (APIs, file I/O, system calls)
- [ ] Test is **deterministic** (no flakiness)
- [ ] Test has a **clear name** (`test_noun_verb_expectation`)
- [ ] Test **passes locally** before pushing
- [ ] Test **covers both success and failure** paths
- [ ] Test uses **fixtures** for reusable setup
- [ ] Test **avoids over-mocking** your own code
- [ ] CI passes: `ruff check` + `pytest` + `pip-audit`

---

## References

- **pytest docs:** [docs.pytest.org](https://docs.pytest.org)
- **tox docs:** [tox.wiki](https://tox.wiki)
- **pytest-asyncio:** [pytest-asyncio.readthedocs.io](https://pytest-asyncio.readthedocs.io)
- **unittest.mock:** [docs.python.org/3/library/unittest.mock.html](https://docs.python.org/3/library/unittest.mock.html)
- **mentask tests:** [tests/](../tests/) directory
- **AGENTS.md:** [Testing Standard](../AGENTS.md#testing-standard)
