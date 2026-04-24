import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ...core.trust_manager import TrustManager
from ..schema import ToolResult
from .lsp_client import LSPClient


class ExecutionManager:
    """
    Manages tool execution, security verification, and diagnostic injection.
    """

    def __init__(self, tool_registry):
        self.tools = tool_registry
        self.trust = TrustManager()
        self.lsp: LSPClient | None = None

    async def ensure_lsp_started(self) -> None:
        if self.lsp is None:
            self.lsp = LSPClient(workspace_path=".")
            await self.lsp.start()

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
                if tool_call.name in ("write_file", "edit_file", "replace"):
                    report = analyze_path_safety(str(resolved_path))
                    if report.level != SafetyLevel.SAFE:
                        return f"SECURITY RISK ({report.category}): {report.description}"
            except PermissionError as exc:
                return f"PATH ESCAPE ATTEMPT: {exc}"
            except Exception as exc:
                return f"INVALID PATH: {exc}"
        return ""

    async def initialize(self) -> None:
        """Asynchronously prepares the execution environment."""
        await self.trust.load_trust()
        if self.lsp is None:
            await self.ensure_lsp_started()

    async def confirm_tool_call(
        self,
        tool,
        tool_call,
        confirmation_callback: Callable | None,
        security_warning: str,
    ) -> ToolResult | None:
        is_dir_trusted = self.trust.is_trusted(Path.cwd().resolve())
        force_confirmation = bool(security_warning)

        # 1. If tool doesn't need confirmation or there's no UI to ask, skip
        if not (tool and tool.requires_confirmation and confirmation_callback):
            return None

        # 2. If it's a dangerous command (warning exists), we MUST confirm
        if force_confirmation:
            pass
        # 3. If the directory is trusted, we skip confirmation for non-dangerous tools
        elif is_dir_trusted or tool_call.name == "execute_command":
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
        try:
            return await self.tools.call_tool(tool_call.name, tool_call.id, tool_call.arguments)
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
        except Exception:
            pass
        return result
