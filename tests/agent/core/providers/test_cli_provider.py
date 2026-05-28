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
