import asyncio
import os
from collections.abc import AsyncGenerator, Callable
from copy import copy
from typing import Any

from ..core.trust_manager import TrustManager
from .core.lsp_client import LSPClient
from .schema import AgentTurnStatus, AssistantMessage, Message, Role, ToolResult
from .tools.base import ToolRegistry


class AgentOrchestrator:
    """
    Core reasoning loop for AskGem.
    Manages the Thinking -> Action -> Observation cycle.
    """

    def __init__(self, client, tool_registry: ToolRegistry, config: Any = None):
        self.client = client
        self.tools = tool_registry
        self.config = config
        self.active_status = AgentTurnStatus.IDLE
        self.trust = TrustManager()
        self.lsp: LSPClient | None = None

    async def _ensure_lsp_started(self) -> None:
        if self.lsp is None:
            self.lsp = LSPClient(workspace_path=".")
            await self.lsp.start()

    def _build_plan_context(self, plan_file: str = ".askgem_plan.md") -> str:
        if not os.path.exists(plan_file):
            return ""

        try:
            with open(plan_file, encoding="utf-8") as handle:
                raw_plan = handle.read().strip()
        except Exception:
            return ""

        if not raw_plan:
            return ""

        return (
            f"\n\n## ACTIVE EXECUTION PLAN (from {plan_file}):\n"
            "You are currently executing the following multi-turn plan. "
            "Reference this to maintain state and know your next steps:\n"
            f"```markdown\n{raw_plan}\n```"
        )

    def _build_turn_config(self, config: Any | None) -> Any | None:
        plan_context = self._build_plan_context()
        if not plan_context or not config or not hasattr(config, "system_instruction"):
            return config

        turn_config = copy(config)
        instruction = turn_config.system_instruction or ""
        turn_config.system_instruction = f"{instruction}{plan_context}"
        return turn_config

    async def _stream_assistant_turn(
        self, history: list[Message], config: Any | None
    ) -> AsyncGenerator[dict[str, Any], None]:
        assistant_msg = AssistantMessage(content="", thought=None, tool_calls=[], model=self.client.model_name)
        history.append(assistant_msg)

        async for chunk in self.client.generate_stream(history[:-1], self.tools.get_all_schemas(), config=config):
            chunk_type = chunk["type"]
            chunk_content = chunk["content"]

            if chunk_type == "text":
                assistant_msg.content += chunk_content
                yield {"type": "text", "content": chunk_content}
            elif chunk_type == "thought":
                assistant_msg.thought = chunk_content
                yield {"type": "thought", "content": chunk_content}
            elif chunk_type == "tool_call":
                assistant_msg.tool_calls.append(chunk_content)
            elif chunk_type == "metrics":
                assistant_msg.usage = chunk_content
                yield {"type": "metrics", "usage": chunk_content}

    def _build_tool_security_warning(self, tool_call) -> str:
        if tool_call.name == "execute_command":
            from ..core.security import SafetyLevel, analyze_command_safety

            report = analyze_command_safety(tool_call.arguments.get("command", ""))
            if report.level != SafetyLevel.SAFE:
                return f"DANGEROUS COMMAND DETECTED ({report.category}): {report.description}"

        if tool_call.name in ("read_file", "write_file", "edit_file", "list_dir"):
            from ..core.security import ensure_safe_path

            try:
                ensure_safe_path(tool_call.arguments.get("path", "."))
            except PermissionError as exc:
                return f"PATH ESCAPE ATTEMPT: {exc}"

        return ""

    async def _confirm_tool_call(
        self,
        tool,
        tool_call,
        confirmation_callback: Callable | None,
        security_warning: str,
    ) -> ToolResult | None:
        is_dir_trusted = self.trust.is_trusted(os.getcwd())
        force_confirmation = bool(security_warning)

        if not (
            tool
            and tool.requires_confirmation
            and confirmation_callback
            and (not is_dir_trusted or force_confirmation)
        ):
            return None

        try:
            allowed = await confirmation_callback(tool_call.name, tool_call.arguments, warning=security_warning)
        except Exception as exc:
            return ToolResult(tool_call_id=tool_call.id, content=f"Error during confirmation: {exc}", is_error=True)

        if allowed:
            return None

        return ToolResult(
            tool_call_id=tool_call.id,
            content=f"Error: User denied execution of {tool_call.name}.",
            is_error=True,
        )

    async def _call_tool_safely(self, tool_call) -> ToolResult:
        try:
            return await self.tools.call_tool(tool_call.name, tool_call.id, tool_call.arguments)
        except Exception as exc:
            return ToolResult(tool_call_id=tool_call.id, content=f"Tool execution failed: {exc}", is_error=True)

    async def _execute_tool_calls(
        self, tool_calls: list[Any], confirmation_callback: Callable | None
    ) -> list[ToolResult]:
        tool_tasks = []
        immediate_results = []

        for tool_call in tool_calls:
            tool = self.tools.get_tool(tool_call.name)

            if tool_call.arguments and "path" in tool_call.arguments and hasattr(self.client, "update_recent_files"):
                self.client.update_recent_files(tool_call.arguments["path"])

            security_warning = self._build_tool_security_warning(tool_call)
            confirmation_result = await self._confirm_tool_call(
                tool, tool_call, confirmation_callback, security_warning
            )
            if confirmation_result is not None:
                immediate_results.append(confirmation_result)
                continue

            tool_tasks.append(self._call_tool_safely(tool_call))

        results = []
        if tool_tasks:
            results = await asyncio.gather(*tool_tasks)

        return immediate_results + list(results)

    async def _append_lsp_diagnostics(self, tool_call, result: ToolResult) -> ToolResult:
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
        except Exception:
            return result

        if not diagnostics:
            return result

        diag_msg = "\n\n[LSP DIAGNOSTICS - Syntax/Lint Errors Detected]:\n"
        for diagnostic in diagnostics:
            severity = "ERROR" if diagnostic.get("severity") == 1 else "WARNING"
            message = diagnostic.get("message")
            line = diagnostic.get("range", {}).get("start", {}).get("line", 0) + 1
            diag_msg += f"- [{severity}] line {line}: {message}\n"
        diag_msg += "\n[!] Please fix these errors in your next turn."
        result.content += diag_msg
        return result

    def _find_tool_call_name(self, tool_calls: list[Any], tool_call_id: str) -> str:
        for tool_call in tool_calls:
            if tool_call.id == tool_call_id:
                return tool_call.name
        return "unknown"

    async def run_query(
        self,
        user_prompt: str | Any,
        history: list[Message],
        config: Any | None = None,
        confirmation_callback: Callable | None = None,
    ) -> AsyncGenerator[Any, None]:
        """
        Runs the agentic loop. Yields events for the UI.
        """
        # 1. Preparar Turno
        history.append(Message(role=Role.USER, content=user_prompt))
        self.active_status = AgentTurnStatus.THINKING

        while True:
            await self._ensure_lsp_started()

            yield {"status": AgentTurnStatus.THINKING}

            try:
                turn_config = self._build_turn_config(config)
                async for event in self._stream_assistant_turn(history, turn_config):
                    yield event
                assistant_msg = history[-1]
            except Exception as exc:
                yield {"type": "error", "content": f"Critical model failure: {exc}"}
                break

            if not assistant_msg.tool_calls:
                self.active_status = AgentTurnStatus.COMPLETED
                yield {"status": AgentTurnStatus.COMPLETED}
                break

            self.active_status = AgentTurnStatus.EXECUTING
            yield {"status": AgentTurnStatus.EXECUTING, "tool_calls": assistant_msg.tool_calls}

            all_results = await self._execute_tool_calls(assistant_msg.tool_calls, confirmation_callback)

            tool_call_map = {tool_call.id: tool_call for tool_call in assistant_msg.tool_calls}
            for result in all_results:
                tool_call = tool_call_map.get(result.tool_call_id)
                if tool_call is not None:
                    result = await self._append_lsp_diagnostics(tool_call, result)
                tool_name = self._find_tool_call_name(assistant_msg.tool_calls, result.tool_call_id)

                history.append(
                    Message(
                        role=Role.TOOL,
                        content=result.content,
                        metadata={"tool_call_id": result.tool_call_id, "tool_name": tool_name},
                    )
                )
                yield {
                    "type": "tool_result", 
                    "content": result.content, 
                    "is_error": result.is_error,
                    "tool_name": tool_name
                }
