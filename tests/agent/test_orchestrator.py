from unittest.mock import AsyncMock, MagicMock

import pytest

from mentask.agent.orchestrator import AgentOrchestrator
from mentask.agent.schema import AgentTurnStatus, EngineeringLevel, Role, ToolCall, UsageMetrics


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

    def load_dynamic_plugins(self, trust_manager=None):
        pass


@pytest.mark.asyncio
async def test_orchestrator_streaming_loop():
    # Setup
    mock_client = MagicMock()
    mock_client.model_name = "gemini-2.0-flash"

    # We use a stateful mock for generate_stream to handle multiple turns
    gen_calls = 0

    async def stateful_stream(messages, *args, **kwargs):
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
    orchestrator.executor.ensure_lsp_started = AsyncMock()
    orchestrator.executor.lsp = AsyncMock()
    orchestrator.classifier.classify = AsyncMock(return_value=EngineeringLevel.L2_STANDARD)

    history = []
    events = []
    async for event in orchestrator.run_query("list files", history):
        events.append(event)

    # Assertions
    # In the current implementation, history has:
    # 1. USER prompt
    # 2. Assistant turn 1 (Message with tool_calls)
    # 3. TOOL result message
    # 4. Assistant turn 2 (Message with "Found it.")
    assert len(history) == 4
    assert history[0].role == Role.USER
    assert history[3].content == "Found it."
    assert any(e.get("status") == AgentTurnStatus.THINKING for e in events)
    assert any(e.get("type") == "thought" for e in events)
    assert gen_calls == 2
