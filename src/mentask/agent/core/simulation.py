"""
Simulation and Recording layer for mentask.
Allows deterministic execution by replaying or recording API interactions.
"""

import json
import logging
import os
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass
from typing import Any

_logger = logging.getLogger("mentask.simulation")


@dataclass
class SimulatedChunk:
    text: str
    function_calls: list[dict[str, Any]]
    usage: dict[str, int]


class SimulationSession:
    """Mocks OR records the behavior of genai.ChatSession."""

    def __init__(self, manager: "SimulationManager", real_session: Any | None = None):
        self.manager = manager
        self.real_session = real_session
        self.history = []

    async def send_message_stream(self, message: Any = None, **kwargs):
        """Returns an async iterator (matching SDK signature)."""
        return self._stream_generator(message, **kwargs)

    async def _stream_generator(self, message: Any = None, **kwargs):
        """Yields chunks from playback or records real chunks."""
        # Use message if provided, else look into kwargs for backward compatibility
        content = message if message is not None else kwargs.get("content")
        if self.manager.mode == "playback":
            async for chunk in self.manager.get_playback_stream(content):
                yield chunk
        elif self.manager.mode == "record" and self.real_session:
            # Wrap real session and save chunks
            recorded_chunks = []
            async for chunk in await self.real_session.send_message_stream(content):
                # Clean and save chunk data
                c_data = SimulatedChunk(
                    text=chunk.text or "",
                    function_calls=[asdict(fc) for fc in chunk.function_calls]
                    if hasattr(chunk, "function_calls")
                    else [],
                    usage={
                        "prompt_token_count": chunk.usage_metadata.prompt_token_count,
                        "candidates_token_count": chunk.usage_metadata.candidates_token_count,
                    }
                    if getattr(chunk, "usage_metadata", None)
                    else {},
                )
                recorded_chunks.append(c_data)
                yield chunk
            # Save the full turn to the transcript
            self.manager.record_turn(str(content), recorded_chunks)
        else:
            # Fallback for just passthrough
            if self.real_session:
                async for chunk in await self.real_session.send_message_stream(content):
                    yield chunk

    def get_history(self):
        if self.real_session:
            # SDK v0.2.0+ uses .history attribute
            return getattr(self.real_session, "history", [])
        return self.history


class SimulationManager:
    """Manages the lifecycle of agent simulations."""

    def __init__(self, transcript_path: str, mode: str = "playback"):
        """
        Args:
            transcript_path: Path to the .json transcript file.
            mode: 'playback' or 'record'.
        """
        self.transcript_path = transcript_path
        self.mode = mode
        self.transcripts: dict[str, list[list[SimulatedChunk]]] = {}
        self.current_indices: dict[str, int] = {}
        if mode == "playback" and os.path.exists(transcript_path):
            self.load()

    def load(self):
        """Loads transcripts from disk."""
        try:
            with open(self.transcript_path, encoding="utf-8") as f:
                data = json.load(f)
                # Convert dict to dataclass objects
                for key, turns in data.items():
                    self.transcripts[key] = [[SimulatedChunk(**chunk) for chunk in turn] for turn in turns]
        except Exception as e:
            _logger.error(f"Failed to load simulation transcript: {e}")

    def save(self):
        """Saves current transcripts to disk."""
        try:
            os.makedirs(os.path.dirname(self.transcript_path), exist_ok=True)
            serializable = {k: [[asdict(c) for c in turn] for turn in turns] for k, turns in self.transcripts.items()}
            with open(self.transcript_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
        except Exception as e:
            _logger.error(f"Failed to save simulation transcript: {e}")

    def record_turn(self, key: str, chunks: list[SimulatedChunk]):
        """Records a new turn into the transcript."""
        if key not in self.transcripts:
            self.transcripts[key] = []
        self.transcripts[key].append(chunks)
        self.save()  # Auto-save for now

    async def get_playback_stream(self, user_input: str) -> AsyncIterator[Any]:
        """Provides simulated chunks for a given input."""
        # For simplicity, we use the user_input as a lookup key part
        # In a real scenario, this would be more complex (history hash)
        key = str(user_input)
        if key not in self.transcripts:
            _logger.warning(f"No simulation found for key: {key}")
            return

        index = self.current_indices.get(key, 0)
        if index < len(self.transcripts[key]):
            chunks = self.transcripts[key][index]
            self.current_indices[key] = index + 1
            for c in chunks:
                # We mock a mini-object that compatible with genai.Chunk
                mock_chunk = type(
                    "Chunk",
                    (),
                    {
                        "text": c.text,
                        "function_calls": [type("FC", (), fc) for fc in c.function_calls],
                        "usage_metadata": type("Usage", (), c.usage) if c.usage else None,
                        "candidates": [],
                    },
                )
                yield mock_chunk
        else:
            _logger.warning(f"Exhausted simulation turns for key: {key}")


def create_mock_chunk(text: str = "", function_calls: list[dict] = None) -> SimulatedChunk:
    """Helper to manually define chunks for tests."""
    return SimulatedChunk(
        text=text, function_calls=function_calls or [], usage={"prompt_token_count": 0, "candidates_token_count": 0}
    )
