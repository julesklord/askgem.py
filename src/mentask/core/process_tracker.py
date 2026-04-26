"""
core/process_tracker.py — Global subprocess tracking and cleanup.
Ensures that all background processes spawned by tools (like execute_command)
are properly terminated when the agent shuts down.
"""

import asyncio
import logging
import weakref
from typing import Set

_logger = logging.getLogger("mentask")

class ProcessTracker:
    """
    Global singleton (effectively) to track active subprocesses.
    Uses weak references to avoid preventing GC of finished processes,
    but keeps a strong list for the duration of the execution.
    """
    _instance = None
    _active_processes: Set[asyncio.subprocess.Process] = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProcessTracker, cls).__new__(cls)
        return cls._instance

    def register(self, process: asyncio.subprocess.Process):
        """Registers a process for tracking."""
        self._active_processes.add(process)
        # We can also add a callback to remove it when done
        _logger.debug(f"Process registered: {process.pid}")

    def unregister(self, process: asyncio.subprocess.Process):
        """Unregisters a process (e.g., when it finishes normally)."""
        if process in self._active_processes:
            self._active_processes.remove(process)

    async def kill_all(self):
        """Kills all currently registered processes."""
        if not self._active_processes:
            return

        _logger.info(f"Shutting down {len(self._active_processes)} active processes...")
        
        # Create a copy to iterate while modifying
        to_kill = list(self._active_processes)
        
        for proc in to_kill:
            try:
                if proc.returncode is None:
                    _logger.debug(f"Killing process {proc.pid}")
                    proc.kill()
                    # Wait a bit for it to die
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        _logger.warning(f"Process {proc.pid} did not exit gracefully after kill.")
            except Exception as e:
                _logger.error(f"Error killing process: {e}")
            finally:
                self.unregister(proc)

        self._active_processes.clear()

# Singleton instance
tracker = ProcessTracker()
