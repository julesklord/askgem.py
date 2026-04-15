import pytest
from unittest.mock import AsyncMock, MagicMock
from src.askgem.agent.orchestrator import AgentOrchestrator
from src.askgem.agent.schema import Message, Role, AssistantMessage, ToolCall, AgentTurnStatus, UsageMetrics
from src.askgem.agent.tools.base import ToolRegistry

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
async def test_orchestrator_simple_loop():
    # Setup
    mock_client = AsyncMock()
    # Simulate 1 tool call then 1 final response
    mock_client.generate_response.side_effect = [
        {
            "message": AssistantMessage(
                content="I will check files.",
                thought="Let's list files first.",
                tool_calls=[ToolCall(id="call_1", name="list_dir", arguments={"path": "."})],
                usage=UsageMetrics(input_tokens=10, output_tokens=5)
            )
        },
        {
            "message": AssistantMessage(
                content="I see the files now.",
                tool_calls=[],
                usage=UsageMetrics(input_tokens=20, output_tokens=10)
            )
        }
    ]
    
    registry = MockToolRegistry()
    orchestrator = AgentOrchestrator(mock_client, registry)
    
    history = []
    events = []
    async for event in orchestrator.run_query("hi", history):
        events.append(event)
        
    # Assertions
    assert len(history) == 4 # User -> Assistant (TC) -> Tool Result -> Assistant (Final)
    assert events[0]["status"] == AgentTurnStatus.THINKING
    assert any(e.get("type") == "thought" for e in events)
    assert any(e.get("status") == AgentTurnStatus.EXECUTING for e in events)
    assert history[-1].content == "I see the files now."
    assert mock_client.generate_response.call_count == 2
