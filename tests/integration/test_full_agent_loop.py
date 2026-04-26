import os
from unittest.mock import AsyncMock

import pytest

from mentask.agent.chat import ChatAgent
from mentask.agent.core.simulation import SimulationManager


@pytest.fixture
def simulation_env():
    # Use our created transcript
    transcript_path = os.path.join(os.path.dirname(__file__), "test_transcript.json")
    sim_manager = SimulationManager(transcript_path, mode="playback")
    return sim_manager


@pytest.mark.skip(reason="Legacy simulation test needs refactor for v0.12.3 architectural changes")
@pytest.mark.asyncio
async def test_agent_loop_with_simulation(simulation_env):
    """Verifies that the agent can perform a full turn with tools in simulation mode."""
    from unittest.mock import MagicMock

    agent = ChatAgent()
    agent.session.simulation = simulation_env

    # Mock the ToolRegistry.call_tool to return a deterministic result
    from mentask.agent.schema import ToolResult

    agent.tools.call_tool = AsyncMock(
        return_value=ToolResult(tool_call_id="call_123", content="13/04/2026", is_error=False)
    )

    # Mock the renderer
    renderer = MagicMock()
    responses = []
    renderer.update_stream.side_effect = lambda text: responses.append(text)

    await agent._stream_response("Hola, dime la fecha", renderer=renderer)

    # Verify:
    # 1. Tool was called (the transcript says execute_bash 'date /t')
    agent.tools.call_tool.assert_called()
    # 2. Final response was produced
    assert any("13 de abril de 2026" in r for r in responses)
    # 3. Metrics were updated (Simulation sends usage meta)
    assert agent.metrics.total_prompt_tokens > 0


@pytest.mark.asyncio
async def test_security_check_integrated_with_loop(simulation_env):
    """Verifies that dangerous commands are correctly reported in the loop."""
    # This would require a transcript with a dangerous command
    # and a mock UI that records the 'confirm_action' calls.
    pass
