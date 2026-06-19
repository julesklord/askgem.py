import time
from typing import Any, Optional


class ReadFileConstraint:
    MAX_LINES = 1000

    @staticmethod
    def check_request(
        total_lines: int, existing_line_offset: int = 1, max_lines: Optional[int] = None, chunk_size: int = 500
    ) -> dict[str, Any]:
        """
        Evaluates file size in lines and determines the reading strategy.
        """
        limit = max_lines or ReadFileConstraint.MAX_LINES

        if total_lines > limit:
            return {
                "strategy": "chunked",
                "chunk_size": chunk_size,
                "current_offset": existing_line_offset,
                "next_offset": existing_line_offset + chunk_size,
                "total_size": total_lines,
            }

        return {"strategy": "full", "size": total_lines}


class FileReadingSession:
    """Maintains the state of a progressive line-based file read."""

    def __init__(self, path: str, total_lines: int):
        self.path = path
        self.total_size = total_lines
        self.chunks_read: list[tuple[int, int, str]] = []
        self.current_offset = 1  # 1-indexed lines
        self.read_attempts = 0
        self.metrics: dict[str, Any] = {"total_chunks_read": 0, "total_bytes": 0, "time_started": time.time(), "chunk_timing": []}

    def add_chunk(self, start_line: int, end_line: int, content: str) -> None:
        """Registers a new read chunk."""
        self.chunks_read.append((start_line, end_line, content))
        self.current_offset = end_line + 1
        self.read_attempts = 0

        # Metrics update
        chunk_len = len(content.encode("utf-8")) if content else 0
        self.metrics["total_chunks_read"] += 1
        self.metrics["total_bytes"] += chunk_len
        elapsed = time.time() - self.metrics["time_started"]
        self.metrics["chunk_timing"].append((start_line, end_line, elapsed))

    def should_retry(self) -> bool:
        """Determines if reading should continue to be attempted."""
        return self.read_attempts < 3

    def mark_attempt(self) -> None:
        """Registers a failed or redundant attempt."""
        self.read_attempts += 1

    def is_complete(self) -> bool:
        """Checks if the entire file has been read."""
        return self.current_offset > self.total_size

    def last_chunk_content(self) -> str:
        """Returns the content of the last read chunk."""
        if not self.chunks_read:
            return ""
        return self.chunks_read[-1][2]
