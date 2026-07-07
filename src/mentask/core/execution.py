import asyncio
import contextlib
import inspect
import logging
import time
from collections.abc import Callable
from typing import Any

from rich.progress import Progress, SpinnerColumn, TimeRemainingColumn

logger = logging.getLogger(__name__)


class OperationTimeout(Exception):
    def __init__(self, op_id: str, elapsed: float, timeout: int):
        self.op_id = op_id
        self.elapsed = elapsed
        self.timeout = timeout
        super().__init__(f"Operation {op_id} timed out after {elapsed:.1f}s (limit: {timeout}s)")


class BlockingOperationManager:
    def __init__(self, global_timeout: int = 120):
        self.global_timeout = global_timeout
        self.active_operations: dict[str, Any] = {}

    async def execute_long_operation(
        self, op_id: str, description: str, operation: Callable, timeout_seconds: int | None = None
    ) -> Any:
        timeout = timeout_seconds or self.global_timeout

        self.active_operations[op_id] = {
            "started_at": time.time(),
            "timeout": timeout,
            "status": "running",
            "description": description,
        }

        with Progress(
            SpinnerColumn(), "[progress.description]{task.description}", TimeRemainingColumn(), transient=True
        ) as progress:
            task = progress.add_task(description, total=timeout)

            async def update_progress():
                while not progress.finished:
                    elapsed = time.time() - self.active_operations[op_id]["started_at"]
                    progress.update(task, completed=min(elapsed, timeout))
                    await asyncio.sleep(0.1)

            progress_task = asyncio.create_task(update_progress())
            try:
                result = await asyncio.wait_for(self._run_operation(operation), timeout=timeout)
                self.active_operations[op_id]["status"] = "completed"
                return result
            except asyncio.TimeoutError:
                self.active_operations[op_id]["status"] = "timeout"
                elapsed = time.time() - self.active_operations[op_id]["started_at"]
                logger.error(f"{description} - TIMEOUT after {timeout}s")
                return OperationTimeout(op_id=op_id, elapsed=elapsed, timeout=timeout)
            finally:
                progress_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await progress_task
                progress.update(task, completed=timeout)
                if op_id in self.active_operations:
                    del self.active_operations[op_id]

    async def _run_operation(self, operation: Callable) -> Any:
        if inspect.iscoroutinefunction(operation):
            return await operation()
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, operation)
