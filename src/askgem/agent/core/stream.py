"""
Streaming interaction module for AskGem.

Handles real-time token accumulation, unique function call extraction, and usage metadata tracking.
"""

import logging
from typing import Callable, List, Optional, Tuple

from google.genai import types

_logger = logging.getLogger("askgem")


class StreamProcessor:
    """Handles the complexity of streaming responses and tool detection."""

    def __init__(self, metrics_tracker):
        self.metrics = metrics_tracker
        self.interrupted = False

    def _extract_function_calls(self, chunk: types.Part, seen_calls: set) -> List[types.FunctionCall]:
        """Extracts unique function calls from a streaming response chunk."""
        found = []

        # Primary detection
        try:
            for fc in chunk.function_calls or []:
                key = (fc.name, str(sorted(fc.args.items()) if fc.args else []))
                if key not in seen_calls:
                    seen_calls.add(key)
                    found.append(fc)
        except (AttributeError, TypeError) as _sdk_err:
            _logger.debug("SDK function_calls property not present: %s", _sdk_err)

        # Fallback detection
        try:
            for candidate in chunk.candidates or []:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", []) or []
                for part in parts:
                    fc = getattr(part, "function_call", None)
                    if fc and getattr(fc, "name", None):
                        key = (fc.name, str(sorted(fc.args.items()) if fc.args else []))
                        if key not in seen_calls:
                            seen_calls.add(key)
                            found.append(fc)
        except (AttributeError, TypeError) as _candidate_err:
            _logger.debug("Candidate parts traversal failed: %s", _candidate_err)

        return found

    async def process_async_stream(
        self, chat_session, user_input: any, callback: Optional[Callable[[str], None]]
    ) -> Tuple[str, List[types.FunctionCall]]:
        """Processes the generator stream, updating UI and collecting function calls."""
        full_text = ""
        seen_calls: set = set()
        function_calls_received: List[types.FunctionCall] = []
        self.interrupted = False
        async for chunk in await chat_session.send_message_stream(message=user_input):
            if self.interrupted:
                if callback:
                    callback("\n\n[bold red][INTERRUPTED BY USER][/bold red]")
                break

            if chunk.text and callback:
                callback(chunk.text)
            if chunk.text:
                full_text += chunk.text

            # Metadata & Tool extraction
            new_calls = self._extract_function_calls(chunk, seen_calls)
            function_calls_received.extend(new_calls)

            if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                self.metrics.add_usage(
                    chunk.usage_metadata.prompt_token_count, chunk.usage_metadata.candidates_token_count
                )
        return full_text, function_calls_received
