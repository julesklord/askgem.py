import logging
import os
from collections.abc import AsyncGenerator, Callable
from typing import Any

from ..core.compression import ContextSnapper
from ..core.summarizer import Summarizer
from .core.execution import ExecutionManager
from .core.provider import ProviderManager
from .schema import AgentTurnStatus, Message, Role
from .tools.base import ToolRegistry

_logger = logging.getLogger("askgem")


class AgentOrchestrator:
    """
    High-level Coordinator for AskGem.
    Implements the Thinking -> Action -> Observation loop.
    Now with Proactive Context Snapping and Modular Managers.
    """

    def __init__(self, client, tool_registry: ToolRegistry, config: Any = None):
        self.client = client
        self.tools = tool_registry
        self.config = config
        self.active_status = AgentTurnStatus.IDLE
        self.status_callback: Callable[[str], None] | None = None

        # Specialized Managers
        self.provider = ProviderManager(client)
        self.executor = ExecutionManager(tool_registry)

        # Performance & Optimization
        self.snapper = ContextSnapper(client.model_name)
        self.summarizer = Summarizer()

    def _report_status(self, message: str) -> None:
        """Internal helper to log and report status via callback."""
        _logger.info(message)
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception as e:
                _logger.error(f"Failed to call status_callback: {e}")

    def _build_plan_context(self, plan_file: str = ".askgem_plan.md") -> str:
        if not os.path.exists(plan_file):
            return ""
        try:
            with open(plan_file, encoding="utf-8") as handle:
                raw_plan = handle.read().strip()
            return f"\n\n## ACTIVE EXECUTION PLAN (from {plan_file}):\n{raw_plan}" if raw_plan else ""
        except Exception:
            return ""

    def _build_turn_config(self, config: Any | None) -> Any | None:
        plan_context = self._build_plan_context()
        if not plan_context or not config or not hasattr(config, "system_instruction"):
            return config
        from copy import copy

        turn_config = copy(config)
        turn_config.system_instruction = f"{turn_config.system_instruction}{plan_context}"
        return turn_config

    async def _perform_context_snap(self, history: list[Message], config: Any) -> list[Message]:
        """Summarizes history and resets context."""
        _logger.warning(f"Context Snapping Triggered! Threshold exceeded. Current model: {self.client.model_name}")
        summary_prompt = self.summarizer.BASE_SUMMARIZATION_PROMPT
        history.append(Message(role=Role.USER, content=summary_prompt))

        raw_summary = ""
        async for event in self.provider.stream_turn(history, [], config=config):
            if event["type"] == "text":
                raw_summary = event["content"]

        formatted_summary = self.summarizer.format_summary(raw_summary)
        continuation_msg = self.summarizer.get_user_continuation_message(formatted_summary)
        return [Message(role=Role.USER, content=continuation_msg)]

    def _find_tool_call_name(self, tool_calls: list[Any], tool_call_id: str) -> str:
        for tc in tool_calls:
            if tc.id == tool_call_id:
                return tc.name
        return "unknown"

    async def run_query(
        self,
        user_prompt: str | Any,
        history: list[Message],
        config: Any | None = None,
        confirmation_callback: Callable | None = None,
    ) -> AsyncGenerator[Any, None]:
        history.append(Message(role=Role.USER, content=user_prompt))
        self.active_status = AgentTurnStatus.THINKING
        turn_id = 0

        while True:
            turn_id += 1
            self._report_status(f"--- Agent Turn {turn_id} Start ---")
            await self.executor.initialize()
            yield {"status": AgentTurnStatus.THINKING}

            try:
                turn_config = self._build_turn_config(config)
                async for event in self.provider.stream_turn(history, self.tools.get_all_schemas(), config=turn_config):
                    yield event
                    if event["type"] == "metrics":
                        total_usage = getattr(event["usage"], "input_tokens", 0) + getattr(
                            event["usage"], "output_tokens", 0
                        )
                        if self.snapper.should_snap(total_usage):
                            yield {"type": "info", "content": "🔄 Context Snapping Triggered..."}
                            new_history = await self._perform_context_snap(history, turn_config)
                            history.clear()
                            history.extend(new_history)
                            yield {"type": "info", "content": "✅ Context snapped."}

                assistant_msg = history[-1]
            except Exception as exc:
                _logger.error(f"Critical error during turn {turn_id}: {exc}")
                yield {"type": "error", "content": f"Critical model failure: {exc}"}
                break

            if not assistant_msg.tool_calls:
                self.active_status = AgentTurnStatus.COMPLETED
                yield {"status": AgentTurnStatus.COMPLETED}
                break

            self.active_status = AgentTurnStatus.EXECUTING
            yield {"status": AgentTurnStatus.EXECUTING, "tool_calls": assistant_msg.tool_calls}
            self._report_status(f"Executing {len(assistant_msg.tool_calls)} tools...")

            all_results = await self.executor.run_batch(
                assistant_msg.tool_calls, confirmation_callback, client=self.client
            )

            tool_call_map = {tc.id: tc for tc in assistant_msg.tool_calls}
            for result in all_results:
                tool_call = tool_call_map.get(result.tool_call_id)
                if tool_call:
                    result = await self.executor.append_lsp_diagnostics(tool_call, result)

                tool_name = self._find_tool_call_name(assistant_msg.tool_calls, result.tool_call_id)
                _logger.debug(f"Tool {tool_name} result received (error={result.is_error})")

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
                    "tool_name": tool_name,
                }

            if any(r.is_error for r in all_results):
                critique_prompt = (
                    "SYSTEM REFLECTION: One or more tools returned an error. "
                    "Before proceeding, evaluate:\n"
                    "1. Was the error expected or unexpected?\n"
                    "2. Does this invalidate your current hypothesis?\n"
                    "3. What alternative approach should you try?\n"
                    "Respond with your analysis."
                )
                history.append(Message(role=Role.SYSTEM, content=critique_prompt))
                yield {"status": AgentTurnStatus.THINKING}
