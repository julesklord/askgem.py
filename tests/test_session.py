from unittest.mock import AsyncMock, MagicMock

import pytest

from askgem.agent.core.session import SessionManager
from askgem.agent.schema import Message, Role


@pytest.mark.asyncio
async def test_generate_stream_parsing():
    # Setup
    mock_config = MagicMock()
    session = SessionManager(mock_config, "gemini-2.0-flash")
    session.client = MagicMock()

    # The SDK requires: async for chunk in await client.aio.models.generate_content_stream(...)
    # So the mock must be a regular function (or coro) that returns an AsyncGenerator.

    async def internal_gen():
        # Chunk 1: Thought
        chunk1 = MagicMock()
        chunk1.candidates = [MagicMock()]
        part1 = MagicMock()
        part1.text = None
        part1.thought = "Thinking..."
        part1.function_call = None
        chunk1.candidates[0].content.parts = [part1]
        yield chunk1

        # Chunk 2: Text
        chunk2 = MagicMock()
        chunk2.candidates = [MagicMock()]
        part2 = MagicMock()
        part2.text = "Hello"
        part2.thought = None
        part2.function_call = None
        chunk2.candidates[0].content.parts = [part2]
        chunk2.usage_metadata.prompt_token_count = 10
        chunk2.usage_metadata.candidates_token_count = 5
        yield chunk2

    # We mock it as an AsyncMock that returns our generator when awaited
    session.client.aio.models.generate_content_stream = AsyncMock(return_value=internal_gen())

    # Execute
    events = []
    async for event in session.generate_stream(history=[Message(role=Role.USER, content="hi")], tools_schema=[]):
        events.append(event)

    # Assertions
    assert any(e["type"] == "thought" and e["content"] == "Thinking..." for e in events)
    assert any(e["type"] == "text" and e["content"] == "Hello" for e in events)
    assert any(e["type"] == "metrics" for e in events)
