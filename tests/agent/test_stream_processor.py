"""
Unit tests for the StreamProcessor module.
Verifies chunk processing, function call extraction and usage tracking.
"""

from unittest.mock import MagicMock

import pytest

from askgem.agent.core.stream import StreamProcessor


@pytest.fixture
def mock_metrics():
    return MagicMock()


@pytest.mark.asyncio
async def test_stream_processor_basic_text(mock_metrics):
    """Verifies that text chunks are correctly accumulated and passed to callback."""
    processor = StreamProcessor(mock_metrics)
    mock_session = MagicMock()

    # Define mock chunks
    chunk1 = MagicMock()
    chunk1.text = "Hello "
    chunk1.usage_metadata = None
    chunk2 = MagicMock()
    chunk2.text = "world"
    chunk2.usage_metadata = None

    # mock_session.send_message_stream returns an async generator
    async def mock_generator(*args, **kwargs):
        yield chunk1
        yield chunk2

    mock_session.send_message_stream.return_value = mock_generator()

    chunks_received = []

    def callback(text):
        chunks_received.append(text)

    full_text, f_calls = await processor.process_async_stream(mock_session, "hi", callback)

    assert full_text == "Hello world"
    assert chunks_received == ["Hello ", "world"]
    assert len(f_calls) == 0


@pytest.mark.asyncio
async def test_stream_processor_usage_tracking(mock_metrics):
    """Verifies that usage metadata is correctly passed to the metrics tracker."""
    processor = StreamProcessor(mock_metrics)
    mock_session = MagicMock()

    chunk = MagicMock()
    chunk.text = "test"
    chunk.usage_metadata = MagicMock()
    chunk.usage_metadata.prompt_token_count = 10
    chunk.usage_metadata.candidates_token_count = 5

    async def mock_generator(*args, **kwargs):
        yield chunk

    mock_session.send_message_stream.return_value = mock_generator()

    await processor.process_async_stream(mock_session, "hi", callback=None)

    mock_metrics.add_usage.assert_called_once_with(10, 5)


@pytest.mark.asyncio
async def test_stream_processor_function_calls(mock_metrics):
    """Verifies that function calls are correctly extracted from chunks."""
    processor = StreamProcessor(mock_metrics)
    mock_session = MagicMock()

    chunk = MagicMock()
    chunk.text = ""
    fc = MagicMock()
    fc.name = "get_weather"
    fc.args = {"city": "Madrid"}
    chunk.function_calls = [fc]
    chunk.usage_metadata = None

    async def mock_generator(*args, **kwargs):
        yield chunk

    mock_session.send_message_stream.return_value = mock_generator()

    full_text, f_calls = await processor.process_async_stream(mock_session, "weather?", callback=None)

    assert len(f_calls) == 1
    assert f_calls[0].name == "get_weather"
    assert f_calls[0].args == {"city": "Madrid"}
