from unittest.mock import AsyncMock, MagicMock

import pytest

from mentask.agent.core.session import SessionManager
from mentask.agent.schema import Message, Role


@pytest.mark.asyncio
async def test_generate_stream_parsing():
    # Setup
    mock_config = MagicMock()
    session = SessionManager(mock_config, "gemini-2.0-flash")
    
    # Mock the provider instead of the client
    session.provider = MagicMock()

    async def internal_gen(*args, **kwargs):
        # Event 1: Thought
        yield {"type": "thought", "content": "Thinking..."}
        # Event 2: Text
        yield {"type": "text", "content": "Hello"}
        # Event 3: Metrics
        yield {"type": "metrics", "content": MagicMock()}

    session.provider.generate_stream = internal_gen

    # Execute
    events = []
    async for event in session.generate_stream(history=[Message(role=Role.USER, content="hi")], tools_schema=[]):
        events.append(event)

    # Assertions
    assert any(e["type"] == "thought" and e["content"] == "Thinking..." for e in events)
    assert any(e["type"] == "text" and e["content"] == "Hello" for e in events)
    assert any(e["type"] == "metrics" for e in events)
