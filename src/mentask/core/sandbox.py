import abc
import asyncio
import contextlib
import logging
import os

_logger = logging.getLogger("mentask.sandbox")


class BaseSandbox(abc.ABC):
    """Abstract Base Class for Command Execution Sandbox environments."""

    @abc.abstractmethod
    async def execute_command(self, command: str, timeout: float = 60.0) -> tuple[int, str, str]:
        """Executes a command and returns (exit_code, stdout, stderr)."""
        pass


class LocalSandbox(BaseSandbox):
    """Executes commands directly on the host operating system (trusted mode)."""

    async def execute_command(self, command: str, timeout: float = 60.0) -> tuple[int, str, str]:
        _logger.debug("LocalSandbox executing: %s (timeout=%.1fs)", command[:200], timeout)
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            # Register process in the global process tracker
            from .process_tracker import tracker
            tracker.register(proc)

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")
            except asyncio.TimeoutError:
                with contextlib.suppress(Exception):
                    proc.kill()
                await proc.wait()
                return -1, "", "Command timed out."
            finally:
                tracker.unregister(proc)
        except Exception as e:
            _logger.error("LocalSandbox execution failed: %s", e, exc_info=True)
            return -1, "", str(e)


class DockerSandbox(BaseSandbox):
    """Runs commands in an isolated Docker container, mounting the workspace read-write."""

    def __init__(self, image: str = "python:3.11-slim", workspace_mount: str | None = None):
        self.image = image
        self.workspace_mount = workspace_mount or os.getcwd()

    async def execute_command(self, command: str, timeout: float = 60.0) -> tuple[int, str, str]:
        _logger.debug("DockerSandbox executing: %s (image=%s, timeout=%.1fs)", command[:200], self.image, timeout)
        # Mount the host repository directory inside the docker container
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.workspace_mount}:/workspace",
            "-w", "/workspace",
            self.image,
            "sh", "-c", command
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            from .process_tracker import tracker
            tracker.register(proc)

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")
            except asyncio.TimeoutError:
                with contextlib.suppress(Exception):
                    proc.kill()
                await proc.wait()
                return -1, "", "Docker command timed out."
            finally:
                tracker.unregister(proc)
        except Exception as e:
            _logger.error("DockerSandbox execution failed: %s", e, exc_info=True)
            return -1, "", f"Docker execution failed: {e}. Ensure docker is installed, running, and user is in docker group."


class SandboxManager:
    """Manager that dynamically resolves the active sandbox environment based on config."""

    def __init__(self, config=None):
        self.config = config
        mode = "none"
        if config and hasattr(config, "settings"):
            mode = config.settings.get("sandbox_mode", "none")

        if mode == "docker":
            image = config.settings.get("sandbox_image", "python:3.11-slim") if config else "python:3.11-slim"
            self.sandbox = DockerSandbox(image=image)
        else:
            self.sandbox = LocalSandbox()

    async def execute(self, command: str, timeout: float = 60.0) -> tuple[int, str, str]:
        """Delegates execution to the active sandbox backend."""
        return await self.sandbox.execute_command(command, timeout=timeout)
