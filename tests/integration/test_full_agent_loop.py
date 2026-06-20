"""Integration tests for the full agent loop.

These tests require external services (Ollama running locally) and are
excluded from regular CI runs. Run them with::

    make test-integration
    # or
    pytest -m integration
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from mentask.agent.chat import ChatAgent
from mentask.agent.core.simulation import SimulationManager


@pytest.fixture
def simulation_env():
    """Provides a SimulationManager in playback mode using a local transcript."""
    transcript_path = os.path.join(os.path.dirname(__file__), "test_transcript.json")
    return SimulationManager(transcript_path, mode="playback")


@pytest.mark.integration
@pytest.mark.skip(reason="Legacy simulation test needs refactor for v0.12.3 architectural changes")
async def test_agent_loop_with_simulation(simulation_env, manage_ollama):
    """Verifies that the agent can perform a full turn with tools in simulation mode."""
    from mentask.agent.schema import ToolResult

    agent = ChatAgent()
    agent.session.simulation = simulation_env

    # Mock the ToolRegistry.call_tool to return a deterministic result
    agent.tools.call_tool = AsyncMock(
        return_value=ToolResult(tool_call_id="call_123", content="13/04/2026", is_error=False)
    )

    # Mock the renderer
    renderer = MagicMock()
    responses: list[str] = []
    renderer.update_stream.side_effect = lambda text: responses.append(text)

    await agent._stream_response("Hola, dime la fecha", renderer=renderer)

    # Verify:
    # 1. Tool was called (the transcript says execute_bash 'date /t')
    agent.tools.call_tool.assert_called()
    # 2. Final response was produced
    assert any("13 de abril de 2026" in r for r in responses)
    # 3. Metrics were updated (Simulation sends usage meta)
    assert agent.metrics.total_prompt_tokens > 0


@pytest.mark.integration
async def test_security_check_integrated_with_loop(simulation_env, manage_ollama):
    """Verifies that dangerous commands are correctly reported in the loop.

    TODO: Requires a transcript with a dangerous command and a mock UI that
    records the 'confirm_action' calls.
    """
    pass
