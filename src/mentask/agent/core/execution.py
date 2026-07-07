import asyncio
import contextlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mentask.core.constants import DEFAULT_GLOBAL_EXECUTION_TIMEOUT

from ...core.execution import BlockingOperationManager, OperationTimeout
from ...core.trust_manager import TrustManager
from ..schema import ToolResult
from .lsp_client import LSPClient, is_ruff_available

_logger = logging.getLogger("mentask")



class ExecutionManager:
    """Manages tool execution, security verification, and diagnostic injection."""

    def __init__(self, tool_registry, config=None):
        self.tools = tool_registry
        self.config = config
        self.trust = TrustManager()
        self.lsp: LSPClient | None = None
        self._lsp_init_task: asyncio.Task | None = None
        self.operation_mgr = BlockingOperationManager(global_timeout=DEFAULT_GLOBAL_EXECUTION_TIMEOUT)

    async def _init_lsp_background(self) -> None:
        if self.lsp is not None:
            return
        if not is_ruff_available():
            self._lsp_init_task = None
            return
        lsp = LSPClient(workspace_path=".")
        try:
            if await lsp.start():
                self.lsp = lsp
            else:
                await lsp.stop()
        except Exception:
            await lsp.stop()
        if self.lsp is None:
            self._lsp_init_task = None
        _logger.debug(f"LSP background init finished — available={self.lsp is not None}")

    def build_security_warning(self, tool_call) -> str:
        if tool_call.name == "execute_command":
            from ...core.security import SafetyLevel, analyze_command_safety

            report = analyze_command_safety(tool_call.arguments.get("command", ""))
            if report.level != SafetyLevel.SAFE:
                return f"DANGEROUS COMMAND DETECTED ({report.category}): {report.description}"

        if tool_call.name in ("read_file", "write_file", "edit_file", "list_dir", "replace"):
            from ...core.security import SafetyLevel, analyze_path_safety, ensure_safe_path

            try:
                raw_path = tool_call.arguments.get("path") or tool_call.arguments.get("file_path", ".")
                resolved_path = Path(raw_path).resolve()

                # 1. Check for Path Escape (Basic Security)
                ensure_safe_path(str(resolved_path))

                # 2. Check for Critical Asset Modification (Intelligent Safety)
                if tool_call.name in ("write_file", "edit_file", "replace", "delete_file", "move_file"):
                    # Check Read-Only Mode
                    if self.config and self.config.settings.get("readonly_mode", False):
                        if tool_call.name in ("delete_file", "move_file"):
                            return f"READ-ONLY MODE: Modification tool '{tool_call.name}' is forbidden."

                        # For write/edit, only allow if the file DOES NOT exist
                        if resolved_path.exists():
                            return f"READ-ONLY MODE: Modification of existing file '{resolved_path.name}' is forbidden."

                    report = analyze_path_safety(str(resolved_path))
                    if report.level != SafetyLevel.SAFE:
                        return f"SECURITY RISK ({report.category}): {report.description}"
            except (PermissionError, OSError, ValueError) as exc:
                return f"PATH SECURITY ERROR: {exc}"
            except Exception as exc:
                return f"UNEXPECTED PATH ERROR: {exc}"
        return ""

    async def initialize(self) -> None:
        """Asynchronously prepares the execution environment."""
        await self.trust.load_trust()

        # Load dynamic plugins with trust context
        try:
            self.tools.load_dynamic_plugins(trust_manager=self.trust)
        except Exception as e:
            from logging import getLogger

            getLogger("mentask").error(f"Failed to load dynamic plugins during execution init: {e}")

        # Fire LSP startup in background — no need to block startup on it
        if self.lsp is None and self._lsp_init_task is None:
            self._lsp_init_task = asyncio.create_task(self._init_lsp_background())

    async def shutdown(self) -> None:
        """Cleans up background resources like LSP."""
        if self._lsp_init_task is not None and not self._lsp_init_task.done():
            self._lsp_init_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._lsp_init_task
            self._lsp_init_task = None
        if self.lsp:
            try:
                await self.lsp.stop()
            except Exception as e:
                from logging import getLogger

                getLogger("mentask").error(f"Error stopping LSP: {e}")
            finally:
                self.lsp = None

    async def confirm_tool_call(
        self,
        tool,
        tool_call,
        confirmation_callback: Callable | None,
        security_warning: str,
    ) -> ToolResult | None:
        is_dir_trusted = self.trust.is_trusted(str(Path.cwd().resolve()))
        force_confirmation = bool(security_warning)

        # Check edit mode
        edit_mode = "manual"
        if hasattr(self, "config") and self.config and hasattr(self.config, "settings"):
            edit_mode = self.config.settings.get("edit_mode", "manual")

        # 1. If tool doesn't need confirmation or there's no UI to ask, skip
        if not (tool and tool.requires_confirmation and confirmation_callback):
            return None

        # 2. In auto mode, we only confirm if it's an explicit DANGEROUS/SECURITY warning
        if edit_mode == "auto":
            if (
                "DANGEROUS" in security_warning
                or "SECURITY ERROR" in security_warning
                or "SECURITY RISK" in security_warning
            ):
                # Force confirmation for severe risks even in auto mode
                pass
            elif is_dir_trusted or tool_call.name == "execute_command":
                # In auto mode, trusted dirs skip confirmation. execute_command also skips if not dangerous.
                return None
        else:
            # Manual mode logic:
            if force_confirmation:
                pass
            elif is_dir_trusted and tool_call.name != "execute_command":
                # In manual mode, we still allow trusted file edits to pass if no warning
                return None

        try:
            allowed = await confirmation_callback(tool_call.name, tool_call.arguments, warning=security_warning)
        except Exception as exc:
            return ToolResult(tool_call_id=tool_call.id, content=f"Error during confirmation: {exc}", is_error=True)

        if not allowed:
            return ToolResult(
                tool_call_id=tool_call.id, content=f"Error: User denied execution of {tool_call.name}.", is_error=True
            )
        return None

    async def call_tool_safely(self, tool_call) -> ToolResult:
        import time

        async def run_tool():
            return await self.tools.call_tool(tool_call.name, tool_call.id, tool_call.arguments)

        try:
            result = await self.operation_mgr.execute_long_operation(
                op_id=f"tool_{tool_call.id}_{time.time()}",
                description=f"Executing tool: {tool_call.name}",
                operation=run_tool,
                timeout_seconds=60,
            )
            if isinstance(result, OperationTimeout):
                return ToolResult(tool_call_id=tool_call.id, content=f"Tool timeout: {result}", is_error=True)
            return result
        except Exception as exc:
            return ToolResult(tool_call_id=tool_call.id, content=f"Tool execution failed: {exc}", is_error=True)

    async def run_batch(
        self, tool_calls: list[Any], confirmation_callback: Callable | None, client: Any = None
    ) -> list[ToolResult]:
        tool_tasks = []
        immediate_results = []

        for tool_call in tool_calls:
            tool = self.tools.get_tool(tool_call.name)
            if tool_call.arguments and "path" in tool_call.arguments and hasattr(client, "update_recent_files"):
                client.update_recent_files(tool_call.arguments["path"])

            security_warning = self.build_security_warning(tool_call)
            confirmation_result = await self.confirm_tool_call(tool, tool_call, confirmation_callback, security_warning)

            if confirmation_result is not None:
                immediate_results.append(confirmation_result)
                continue

            tool_tasks.append(self.call_tool_safely(tool_call))

        results = []
        if tool_tasks:
            results = await asyncio.gather(*tool_tasks)
        return immediate_results + list(results)

    async def append_lsp_diagnostics(self, tool_call, result: ToolResult) -> ToolResult:
        if result.is_error or not result.content.startswith("Success"):
            return result
        if tool_call.name not in ("edit_file", "write_file"):
            return result

        path = tool_call.arguments.get("path", "")
        if not path.endswith(".py") or not self.lsp:
            return result

        try:
            with open(path, encoding="utf-8") as handle:
                code = handle.read()
            diagnostics = await self.lsp.check_file(path, code)
            if diagnostics:
                diag_msg = "\n\n[LSP DIAGNOSTICS - Syntax/Lint Errors Detected]:\n"
                for diagnostic in diagnostics:
                    severity = "ERROR" if diagnostic.get("severity") == 1 else "WARNING"
                    line = diagnostic.get("range", {}).get("start", {}).get("line", 0) + 1
                    diag_msg += f"- [{severity}] line {line}: {diagnostic.get('message')}\n"
                diag_msg += "\n[!] Please fix these errors in your next turn."
                result.content += diag_msg
        except Exception as e:
            _logger.debug(f"Failed to check LSP diagnostics: {e}")
        return result
