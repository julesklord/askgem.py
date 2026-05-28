import json
import logging
from typing import Any

from ...schema import Message, Role
from .ollama import OllamaProvider

_logger = logging.getLogger("mentask")


class GemmaProvider(OllamaProvider):
    """
    Provider specialized for Google's Gemma models (2, 3, 4).
    Gemma models are sensitive to role naming and often prefer system instructions
    to be part of the first user message or use a specific 'developer' role.
    Runs through Ollama by default when prefixed with ollama:.
    """

    def __init__(self, model_name: str, config: Any):
        super().__init__(model_name, config)
        self.display_name = f"Gemma ({model_name})"

    def _build_messages(self, history: list[Message], system_instruction: str | None) -> list[dict[str, Any]]:
        """
        Custom message formatting for Gemma.
        Merges system instructions into the first user message if 'system' role is not well-supported.
        """
        formatted = []
        from ....core.compression import ContextCompressor

        # Gemma models often work better if the system prompt is prepended to the first user message.
        pending_system = system_instruction or ""

        for i, msg in enumerate(history):
            role = "user" if msg.role in (Role.USER, Role.TOOL) else "assistant"
            content = ContextCompressor.smart_compress(str(msg.content))

            if i == 0 and pending_system:
                if msg.role == Role.USER:
                    # Prepend system instruction to first user message
                    content = f"{pending_system}\n\n{content}"
                    pending_system = ""
                else:
                    # If first message is not user, insert system message as user first
                    formatted.append({"role": "user", "content": pending_system})
                    pending_system = ""

            msg_dict: dict[str, Any] = {"role": role, "content": content}

            if msg.role == Role.TOOL:
                # Gemma tool result format: often prefers a clear header
                tool_name = msg.metadata.get("tool_name", "tool")
                msg_dict["content"] = f"[TOOL_RESULT: {tool_name}]\n{content}"
                msg_dict["role"] = "user"  # Tool role is often mapped to user in local providers

            # Handle assistant tool calls (same as OpenAI but ensure content is handled)
            from ...schema import AssistantMessage

            if isinstance(msg, AssistantMessage) and msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                            if isinstance(tc.arguments, dict)
                            else str(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
                if not content:
                    msg_dict["content"] = None

            formatted.append(msg_dict)

        # If we still have a pending system prompt (no history), add it
        if pending_system:
            formatted.append({"role": "user", "content": pending_system})

        return formatted
