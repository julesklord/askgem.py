import pytest
from rich.console import Console

from mentask.agent.core.providers import get_provider
from mentask.core.config_manager import ConfigManager


@pytest.mark.asyncio
async def test_cli_provider_stream():
    config = ConfigManager(Console())
    p = get_provider("cli:python", config)

    # We will use 'python tests/agent/core/providers/dummy_cli.py' as the binary to test.
    p.cli_command = "python tests/agent/core/providers/dummy_cli.py"  # type: ignore

    events = []
    async for chunk in p.generate_stream([], [], {"system_instruction": "Test"}):
        events.append(chunk)

    tool_calls = [e for e in events if e.get("type") == "tool_call"]
    assert len(tool_calls) == 1
    assert tool_calls[0]["content"].name == "read_file"


@pytest.mark.asyncio
async def test_cli_provider_jsonl_stream():
    from unittest.mock import AsyncMock, patch
    from mentask.agent.schema import AgentTurnStatus

    config = ConfigManager(Console())
    p = get_provider("cli:codex", config)

    # Mock subprocess
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.wait = AsyncMock(return_value=0)
    mock_process.stdin = None

    # Mock stdout stream reader with JSONL event lines
    mock_stdout = AsyncMock()
    jsonl_lines = [
        '{"type":"thread.started","thread_id":"123"}\n',
        '{"type":"turn.started"}\n',
        'Preceding text on same line{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"Hello world!\\n```json\\n{\\"mentask_tool_call\\": {\\"name\\": \\"list_dir\\", \\"arguments\\": {\\"DirectoryPath\\": \\"/foo\\"}}}\\n```\\nDone"}}\n',
        '{"type":"turn.completed","usage":{"input_tokens":100,"output_tokens":50}}\n',
        ''  # EOF
    ]
    mock_stdout.readline.side_effect = [line.encode("utf-8") for line in jsonl_lines]

    mock_stderr = AsyncMock()
    mock_stderr.readline.return_value = b""  # EOF immediately

    mock_process.stdout = mock_stdout
    mock_process.stderr = mock_stderr

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        events = []
        async for chunk in p.generate_stream([], [], {"system_instruction": "Test"}):
            events.append(chunk)

    # Verify status is emitted
    statuses = [e for e in events if e.get("status") == AgentTurnStatus.THINKING]
    assert len(statuses) == 1

    # Verify text chunks are parsed
    texts = [e["content"] for e in events if e.get("type") == "text"]
    assert "Preceding text on same line" in texts
    assert "Hello world!\n" in texts
    assert "Done" in texts

    # Verify tool calls are extracted
    tool_calls = [e for e in events if e.get("type") == "tool_call"]
    assert len(tool_calls) == 1
    assert tool_calls[0]["content"].name == "list_dir"
    assert tool_calls[0]["content"].arguments == {"DirectoryPath": "/foo"}

    # Verify metrics are extracted
    metrics = [e["content"] for e in events if e.get("type") == "metrics"]
    assert len(metrics) == 1
    assert metrics[0].input_tokens == 100
    assert metrics[0].output_tokens == 50


@pytest.mark.asyncio
async def test_cli_provider_opencode_jsonl_stream():
    from unittest.mock import AsyncMock, patch
    from mentask.agent.schema import AgentTurnStatus

    config = ConfigManager(Console())
    p = get_provider("cli:opencode", config)

    # Mock subprocess
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.wait = AsyncMock(return_value=0)
    mock_process.stdin = None

    # Mock stdout stream reader with OpenCode JSONL event lines
    mock_stdout = AsyncMock()
    jsonl_lines = [
        '{"type":"step_start"}\n',
        '{"type":"text","part":{"text":"Hello opencode!\\n```json\\n{\\"mentask_tool_call\\": {\\"name\\": \\"glob_find\\", \\"arguments\\": {\\"Pattern\\": \\"*.py\\"}}}\\n```\\nFinished"}}\n',
        '{"type":"step_finish","tokens":{"input":200,"output":150}}\n',
        ''  # EOF
    ]
    mock_stdout.readline.side_effect = [line.encode("utf-8") for line in jsonl_lines]

    mock_stderr = AsyncMock()
    mock_stderr.readline.return_value = b""

    mock_process.stdout = mock_stdout
    mock_process.stderr = mock_stderr

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        events = []
        async for chunk in p.generate_stream([], [], {"system_instruction": "Test"}):
            events.append(chunk)

    # Verify status is emitted
    statuses = [e for e in events if e.get("status") == AgentTurnStatus.THINKING]
    assert len(statuses) == 1

    # Verify text chunks are parsed
    texts = [e["content"] for e in events if e.get("type") == "text"]
    assert "Hello opencode!\n" in texts
    assert "Finished" in texts

    # Verify tool calls are extracted
    tool_calls = [e for e in events if e.get("type") == "tool_call"]
    assert len(tool_calls) == 1
    assert tool_calls[0]["content"].name == "glob_find"
    assert tool_calls[0]["content"].arguments == {"Pattern": "*.py"}

    # Verify metrics are extracted
    metrics = [e["content"] for e in events if e.get("type") == "metrics"]
    assert len(metrics) == 1
    assert metrics[0].input_tokens == 200
    assert metrics[0].output_tokens == 150


@pytest.mark.asyncio
async def test_cli_provider_gemini_jsonl_stream():
    from unittest.mock import AsyncMock, MagicMock, patch
    from mentask.agent.schema import AgentTurnStatus

    config = ConfigManager(Console())
    p = get_provider("cli:gemini", config)

    # Mock subprocess
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.wait = AsyncMock(return_value=0)
    mock_process.stdin = MagicMock()
    mock_process.stdin.drain = AsyncMock()

    # Mock stdout stream reader with Gemini JSONL event lines
    mock_stdout = AsyncMock()
    jsonl_lines = [
        '{"type":"init"}\n',
        '{"type":"message","role":"user","content":"..."}\n',
        '{"type":"message","role":"assistant","content":"Hello gemini!\\n```json\\n{\\"mentask_tool_call\\": {\\"name\\": \\"web_search\\", \\"arguments\\": {\\"query\\": \\"antigravity\\"}}}\\n```\\nDone"}\n',
        '{"type":"result","stats":{"input_tokens":300,"output_tokens":250}}\n',
        ''  # EOF
    ]
    mock_stdout.readline.side_effect = [line.encode("utf-8") for line in jsonl_lines]

    mock_stderr = AsyncMock()
    mock_stderr.readline.return_value = b""

    mock_process.stdout = mock_stdout
    mock_process.stderr = mock_stderr

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        events = []
        async for chunk in p.generate_stream([], [], {"system_instruction": "Test"}):
            events.append(chunk)

    # Verify status is emitted
    statuses = [e for e in events if e.get("status") == AgentTurnStatus.THINKING]
    assert len(statuses) == 1

    # Verify text chunks are parsed
    texts = [e["content"] for e in events if e.get("type") == "text"]
    assert "Hello gemini!\n" in texts
    assert "Done" in texts

    # Verify tool calls are extracted
    tool_calls = [e for e in events if e.get("type") == "tool_call"]
    assert len(tool_calls) == 1
    assert tool_calls[0]["content"].name == "web_search"
    assert tool_calls[0]["content"].arguments == {"query": "antigravity"}

    # Verify metrics are extracted
    metrics = [e["content"] for e in events if e.get("type") == "metrics"]
    assert len(metrics) == 1
    assert metrics[0].input_tokens == 300
    assert metrics[0].output_tokens == 250


