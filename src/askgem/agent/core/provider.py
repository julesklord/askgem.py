from collections.abc import AsyncGenerator
from typing import Any

from ..schema import AssistantMessage, Message


class ProviderManager:
    """
    Manages interactions with the LLM provider.
    Handles streaming and message formatting.
    """

    def __init__(self, client):
        self.client = client

    async def stream_turn(
        self, history: list[Message], tool_schemas: list[dict[str, Any]], config: Any | None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Streams an assistant turn from the provider.
        Updates the history with the new AssistantMessage.
        """
        assistant_msg = AssistantMessage(content="", thought=None, tool_calls=[], model=self.client.model_name)
        history.append(assistant_msg)

        # history[:-1] sends the context without the empty message we just added
        async for chunk in self.client.generate_stream(history[:-1], tool_schemas, config=config):
            chunk_type = chunk["type"]
            chunk_content = chunk["content"]

            if chunk_type == "text":
                assistant_msg.content += chunk_content
                yield {"type": "text", "content": assistant_msg.content}
            elif chunk_type == "thought":
                assistant_msg.thought = chunk_content
                yield {"type": "thought", "content": chunk_content}
            elif chunk_type == "tool_call":
                assistant_msg.tool_calls.append(chunk_content)
            elif chunk_type == "metrics":
                assistant_msg.usage = chunk_content
                yield {"type": "metrics", "usage": chunk_content}
