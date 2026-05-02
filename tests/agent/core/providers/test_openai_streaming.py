from unittest.mock import MagicMock, patch

import pytest

from mentask.agent.core.providers.openai import OpenAIProvider


@pytest.mark.asyncio
async def test_fragmented_tool_call_streaming():
    # Mocking the urllib response to simulate chunks
    chunks = [
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "get_weather", "arguments": ""}}]}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\\"lo"}}]}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "cation\\": \\"Lon"}}]}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "don\\"}"}}]}}]}\n',
        b"data: [DONE]\n",
    ]

    provider = OpenAIProvider("gpt-4o", MagicMock())
    provider.api_key = "test-key"

    # Mock urllib.request.urlopen
    mock_response = MagicMock()
    mock_response.__iter__.return_value = iter(chunks)

    # We need to patch asyncio.to_thread to return our mock_response
    with patch("asyncio.to_thread", return_value=mock_response):
        events = []
        async for event in provider.generate_stream([], []):
            events.append(event)

    # Filter tool_call events
    tool_calls = [e for e in events if e["type"] == "tool_call"]

    # Currently, it might fail with json.decoder.JSONDecodeError or emit partial/incorrect calls
    assert len(tool_calls) == 1
    assert tool_calls[0]["content"].name == "get_weather"
    assert tool_calls[0]["content"].arguments == {"location": "London"}


@pytest.mark.asyncio
async def test_interleaved_multiple_tool_calls_streaming():
    # Simulating two tool calls whose chunks are interleaved
    chunks = [
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "get_w", "arguments": ""}}]}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 1, "id": "call_2", "function": {"name": "get_t", "arguments": ""}}]}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"name": "eather", "arguments": "{\\"loc"}}]}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 1, "function": {"name": "ime", "arguments": "{\\"ci"}}]}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "ation\\": \\"Paris\\"}"}}]}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 1, "function": {"arguments": "ty\\": \\"Tokyo\\"}"}}]}}]}\n',
        b"data: [DONE]\n",
    ]

    provider = OpenAIProvider("gpt-4o", MagicMock())
    provider.api_key = "test-key"

    mock_response = MagicMock()
    mock_response.__iter__.return_value = iter(chunks)

    with patch("asyncio.to_thread", return_value=mock_response):
        events = []
        async for event in provider.generate_stream([], []):
            events.append(event)

    tool_calls = [e for e in events if e["type"] == "tool_call"]
    assert len(tool_calls) == 2

    # Tool calls should be in order of index
    assert tool_calls[0]["content"].name == "get_weather"
    assert tool_calls[0]["content"].arguments == {"location": "Paris"}
    assert tool_calls[1]["content"].name == "get_time"
    assert tool_calls[1]["content"].arguments == {"city": "Tokyo"}


@pytest.mark.asyncio
async def test_mixed_text_and_tool_calls_streaming():
    chunks = [
        b'data: {"choices": [{"delta": {"content": "I will check the weather for you.\\n"}}]}\n',
        b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "get_weather", "arguments": "{\\"location\\": \\"Berlin\\"}"}}]}}]}\n',
        b"data: [DONE]\n",
    ]

    provider = OpenAIProvider("gpt-4o", MagicMock())
    provider.api_key = "test-key"

    mock_response = MagicMock()
    mock_response.__iter__.return_value = iter(chunks)

    with patch("asyncio.to_thread", return_value=mock_response):
        events = []
        async for event in provider.generate_stream([], []):
            events.append(event)

    text_events = [e for e in events if e["type"] == "text"]
    tool_calls = [e for e in events if e["type"] == "tool_call"]

    assert len(text_events) > 0
    assert text_events[0]["content"] == "I will check the weather for you.\n"
    assert len(tool_calls) == 1
    assert tool_calls[0]["content"].name == "get_weather"
    assert tool_calls[0]["content"].arguments == {"location": "Berlin"}
