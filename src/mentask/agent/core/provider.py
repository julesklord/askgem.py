import logging
from collections.abc import AsyncGenerator
from typing import Any

from ..schema import AssistantMessage, Message

_logger = logging.getLogger(__name__)


class ProviderManager:
    """
    Manages interactions with the LLM provider.
    Handles streaming and message formatting.
    """

    def __init__(self, client: Any) -> None:
        self.client = client

    async def stream_turn(
        self, history: list[Message], tool_schemas: list[dict[str, Any]], config: Any | None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Streams an assistant turn from the provider.
        Updates the history with the new AssistantMessage upon successful completion.
        """
        assistant_msg = AssistantMessage(content="", thought=None, tool_calls=[], model=self.client.model_name)

        success = False
        try:
            async for chunk in self.client.generate_stream(history, tool_schemas, config=config):
                try:
                    # Validate chunk structure
                    if not isinstance(chunk, dict):
                        _logger.warning(f"Malformed chunk received (not a dict): {chunk}")
                        continue

                    if "status" in chunk:
                        yield chunk
                        continue

                    if "type" not in chunk or "content" not in chunk:
                        _logger.warning(f"Malformed chunk received: {chunk}")
                        continue

                    chunk_type = chunk["type"]
                    chunk_content = chunk["content"]

                    if chunk_type == "text":
                        assistant_msg.content += chunk_content
                        yield {"type": "text", "content": chunk_content}  # yield delta only, not accumulated
                    elif chunk_type == "thought":
                        if assistant_msg.thought is None:
                            assistant_msg.thought = ""
                        assistant_msg.thought += chunk_content
                        yield {"type": "thought", "content": chunk_content}
                    elif chunk_type == "tool_call":
                        assistant_msg.tool_calls.append(chunk_content)
                        yield {"type": "tool_call", "content": chunk_content}
                    elif chunk_type == "metrics":
                        assistant_msg.usage = chunk_content
                        yield {"type": "metrics", "usage": chunk_content}
                    elif chunk_type == "error" or chunk_type == "info":
                        yield chunk
                    else:
                        _logger.warning(f"Unknown chunk type: {chunk_type}")

                except Exception as chunk_error:
                    _logger.error(f"Error processing chunk: {chunk_error}")
                    # Continue processing other chunks even if one fails
                    continue

            success = True

        except Exception as client_error:
            _logger.error(f"Client streaming error: {client_error}")
            # Yield error chunk to inform the caller
            yield {"type": "error", "content": f"Streaming error: {client_error}"}
            # Don't re-raise - let the caller handle the error gracefully

        finally:
            if success:
                history.append(assistant_msg)
