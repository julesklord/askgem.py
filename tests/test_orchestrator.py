from unittest.mock import AsyncMock, MagicMock

import pytest

from src.askgem.agent.orchestrator import AgentOrchestrator
from src.askgem.agent.schema import AgentTurnStatus, Role, ToolCall, UsageMetrics


class MockToolRegistry:
    def __init__(self):
        self._tools = {}

    def get_all_schemas(self):
        return []

    def get_tool(self, name):
        mock_tool = MagicMock()
        mock_tool.requires_confirmation = False
        return mock_tool

    async def call_tool(self, name, id, args):
        return MagicMock(content=f"Result of {name}", is_error=False, tool_call_id=id)


@pytest.mark.asyncio
async def test_orchestrator_streaming_loop():
    # Setup
    mock_client = MagicMock()
    mock_client.model_name = "gemini-2.0-flash"

    # Define a helper to simulate the stream segments
    async def mock_stream_segments(*args, **kwargs):
        # SEGMENT 1: Thought + Tool Call
        yield {"type": "thought", "content": "Checking files..."}
        yield {"type": "tool_call", "content": ToolCall(id="c1", name="list_dir", arguments={})}
        yield {"type": "metrics", "content": UsageMetrics(input_tokens=10, output_tokens=5)}

        # In the orchestrator, it will wait for tool execution, then call generate_stream AGAIN
        # So we need a side_effect or a way to distinguish turns.
        # But for a simple unit test, let's satisfy one turn logic or mock based on call count.

    # We use a stateful mock for generate_stream to handle multiple turns
    gen_calls = 0

    async def stateful_stream(*args, **kwargs):
        nonlocal gen_calls
        gen_calls += 1
        if gen_calls == 1:
            yield {"type": "thought", "content": "Looking..."}
            yield {"type": "tool_call", "content": ToolCall(id="c1", name="list_dir", arguments={})}
        else:
            yield {"type": "text", "content": "Found it."}
            yield {"type": "metrics", "content": UsageMetrics(input_tokens=20, output_tokens=10)}

    mock_client.generate_stream.side_effect = stateful_stream

    registry = MockToolRegistry()
    orchestrator = AgentOrchestrator(mock_client, registry)
    orchestrator._ensure_lsp_started = AsyncMock()
    orchestrator.lsp = AsyncMock()

    history = []
    events = []
    async for event in orchestrator.run_query("list files", history):
        events.append(event)

    # Assertions
    # 1. USER prompt added
    # 2. Assistant turn 1 (Thought + TC)
    # 3. Tool Result
    # 4. Assistant turn 2 (Text)
    assert len(history) == 4
    assert history[0].role == Role.USER
    assert history[3].content == "Found it."
    assert any(e.get("status") == AgentTurnStatus.THINKING for e in events)
    assert any(e.get("type") == "thought" for e in events)
    assert gen_calls == 2
