from unittest.mock import AsyncMock, MagicMock

import pytest

from src.askgem.agent.core.session import SessionManager
from src.askgem.agent.schema import Message, Role


@pytest.mark.asyncio
async def test_generate_response_parsing():
    # Setup
    mock_config = MagicMock()
    session = SessionManager(mock_config, "gemini-2.0-flash")
    session.client = MagicMock()

    # Mock Gemini response
    mock_response = MagicMock()
    # Pydantic/SDK objects usually have attributes, so we set them
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.candidates_token_count = 50

    # Simulating the SDK parts
    mock_part_text = MagicMock(spec=["text", "thought", "function_call"])
    mock_part_text.text = "Hello world"
    mock_part_text.thought = "Thinking..."
    mock_part_text.function_call = None

    mock_part_call = MagicMock(spec=["text", "thought", "function_call"])
    mock_part_call.text = None
    mock_part_call.thought = None
    fc = MagicMock()
    fc.name = "list_dir"
    fc.args = {"path": "."}
    fc.id = "call_123"
    mock_part_call.function_call = fc

    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part_text, mock_part_call]
    mock_response.candidates = [mock_candidate]

    session.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    # Execute
    result = await session.generate_response(
        history=[Message(role=Role.USER, content="hi")],
        tools_schema=[]
    )

    # Assertions
    msg = result["message"]
    assert msg.content == "Hello world"
    assert msg.thought == "Thinking..."
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0].name == "list_dir"
    assert msg.usage.input_tokens == 100
    assert msg.usage.output_tokens == 50
