import asyncio
import logging
import os
import time
from collections.abc import AsyncGenerator, Callable
from typing import Any

from ..core.compression import ContextSnapper
from ..core.retry_strategy import TimeoutRecoveryManager
from ..core.summarizer import Summarizer
from .core.classifier import TaskClassifier
from .core.execution import ExecutionManager
from .core.provider import ProviderManager
from .schema import AgentTurnStatus, AssistantMessage, EngineeringLevel, Message, Role
from .tools.base import ToolRegistry

_logger = logging.getLogger("mentask")


class AgentOrchestrator:
    """
    High-level Coordinator for mentask.
    Implements the Thinking -> Action -> Observation loop.
    Now with Proactive Context Snapping and Modular Managers.
    """

    MAX_TURNS = 25  # Prevent infinite loops

    def __init__(self, client, tool_registry: ToolRegistry, config: Any = None):
        self.client = client
        self.tools = tool_registry
        self.config = config
        self.active_status = AgentTurnStatus.IDLE
        self.status_callback: Callable[[str], None] | None = None

        # Specialized Managers
        self.provider = ProviderManager(client)
        self.executor = ExecutionManager(tool_registry)
        self.trust = self.executor.trust
        self.classifier = TaskClassifier(self.provider)

        # Performance & Optimization
        self.snapper = ContextSnapper(client.model_name)
        self.summarizer = Summarizer()

        self.timeout_recovery = TimeoutRecoveryManager()

    def _get_level_instruction(self, level: EngineeringLevel) -> str:
        """Returns specific system instructions based on the engineering level."""
        if level == EngineeringLevel.L0_INQUIRY:
            return (
                "\n\n[MODE: INQUIRY (L0)]\n"
                "This is a purely informational request. No tools or code changes are required. "
                "Answer directly and concisely without using any architectural tools."
            )
        elif level == EngineeringLevel.L1_PRAGMATIC:
            return (
                "\n\n[MODE: PRAGMATIC (L1)]\n"
                "This is a simple task. Avoid over-engineering. Do not perform extensive repository mapping "
                "unless strictly necessary. Prioritize using direct shell commands (run_shell_command) or "
                "simple file tools. If a specialized tool fails or is too complex, FALLBACK to shell commands immediately."
            )
        elif level == EngineeringLevel.L3_ARCHITECT:
            return (
                "\n\n[MODE: ARCHITECT (L3)]\n"
                "This is a high-complexity task. You MUST perform deep analysis of the codebase before making changes. "
                "Map the repository structure, identify dependencies, and create a formal plan in .mentask_plan.md. "
                "Ensure maximum safety and adhere to all architectural standards."
            )
        return ""  # L2 is the standard behavior

    def get_session_report(self) -> dict:
        """Returns observability metrics for the current session."""
        try:
            from ..tools.file_tools import FILE_SESSIONS

            file_sessions_metrics = {path: session.metrics for path, session in FILE_SESSIONS.items()}
        except ImportError:
            file_sessions_metrics = {}

        return {
            "timeout_stats": self.timeout_recovery.get_metrics(),
            "file_sessions": file_sessions_metrics,
        }

    def _report_status(self, message: str) -> None:
        """Internal helper to log and report status via callback."""
        _logger.info(message)
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception as e:
                _logger.error(f"Failed to call status_callback: {e}")

    def _build_plan_context(self, plan_file: str = ".mentask_plan.md") -> str:
        if not os.path.exists(plan_file):
            return ""
        try:
            with open(plan_file, encoding="utf-8") as handle:
                raw_plan = handle.read().strip()
            return f"\n\n## ACTIVE EXECUTION PLAN (from {plan_file}):\n{raw_plan}" if raw_plan else ""
        except FileNotFoundError:
            return ""
        except PermissionError:
            _logger.warning(f"Cannot read plan file (permission denied): {plan_file}")
            return ""
        except Exception as e:
            _logger.error(f"Unexpected error reading plan file: {e}")
            return ""

    def _build_tool_context(self, level: EngineeringLevel) -> str:
        """
        Generates a compact, context-aware summary of available tools for the current session.
        Injected into the system prompt so the LLM knows WHEN and HOW to use each tool,
        not just what its schema is.
        """
        cwd = os.getcwd()
        is_git = os.path.exists(os.path.join(cwd, ".git"))
        has_python = os.path.exists(os.path.join(cwd, "pyproject.toml")) or os.path.exists(
            os.path.join(cwd, "setup.py")
        )
        has_node = os.path.exists(os.path.join(cwd, "package.json"))

        lines = [
            "\n\n## TOOL USAGE GUIDE (read before every action)",
            f"CWD: {cwd}",
        ]

        if is_git:
            lines.append(
                "- **Git Mastery**: You are in a Git repository. Use `analyze_codebase` to see changes and "
                "repository structure. Use `commit_changes` to finalize tasks with structured messages. "
                "Prefer `commit_changes` over raw `git commit` commands."
            )
        if has_python:
            lines.append(
                "PYTHON PROJECT: Use `python_repl` for fast one-off computations, data inspection, "
                "or import checks. Use `run_shell_command` for package ops (uv, pip, pytest)."
            )
        if has_node:
            lines.append(
                "NODE PROJECT: Use `run_shell_command` for npm/yarn/pnpm ops. "
                "Prefer read_file for package.json inspection."
            )

        # Level-specific tool priority hints
        if level == EngineeringLevel.L0_INQUIRY:
            lines.append(
                "INQUIRY MODE: DO NOT call any tools. Answer from memory and context only."
            )
        elif level == EngineeringLevel.L1_PRAGMATIC:
            lines.append(
                "PRAGMATIC MODE: Use the MINIMUM number of tools. One tool call is usually enough. "
                "Avoid list_dir unless you don't know where the file is."
            )
        elif level == EngineeringLevel.L3_ARCHITECT:
            lines.append(
                "ARCHITECT MODE: Map the repo first (list_dir + grep_search), then write a plan. "
                "Never edit files without reading them first. Use glob_find for pattern discovery."
            )
        else:  # L2
            lines.append(
                "STANDARD MODE: Read before writing. Use grep_search to locate symbols before editing. "
                "Prefer edit_file over write_file for partial changes."
            )

        # Always-on tool safety rules
        lines += [
            "TOOL RULES:",
            "  - read_file: use for file content. Do NOT read binary files.",
            "  - edit_file: for partial changes. Only the EXACT lines to change.",
            "  - write_file: only for new files or full rewrites. Destructive.",
            "  - run_shell_command: powerful fallback for anything the specialized tools can't do.",
            "  - python_repl: stateless per call. Variables do NOT persist between calls.",
            "  - ask_user: ONLY when the task is genuinely ambiguous. Do not over-ask.",
        ]

        return "\n".join(lines)

    def _build_turn_config(
        self, config: Any | None, level: EngineeringLevel = EngineeringLevel.L2_STANDARD
    ) -> Any | None:
        plan_context = self._build_plan_context()
        level_instruction = self._get_level_instruction(level)
        tool_context = self._build_tool_context(level)
        extra_instructions = f"{plan_context}{level_instruction}{tool_context}"

        if not extra_instructions or not config:
            return config

        from copy import copy

        turn_config = copy(config)

        if isinstance(turn_config, dict):
            orig = turn_config.get("system_instruction", "")
            turn_config["system_instruction"] = f"{orig}{extra_instructions}"
        elif hasattr(turn_config, "system_instruction"):
            turn_config.system_instruction = f"{turn_config.system_instruction}{extra_instructions}"

        return turn_config

    async def _perform_context_snap(self, history: list[Message], config: Any) -> list[Message]:
        """Summarizes history and resets context without corrupting state."""
        _logger.warning(f"Context Snapping Triggered! Threshold exceeded. Current model: {self.client.model_name}")

        # Use a copy to prevent corrupting history if synthesis fails
        history_copy = [m for m in history]
        summary_prompt = self.summarizer.BASE_SUMMARIZATION_PROMPT
        history_copy.append(Message(role=Role.USER, content=summary_prompt))

        raw_summary = ""
        try:
            async for event in self.provider.stream_turn(history_copy, [], config=config):
                if event["type"] == "text":
                    raw_summary = event["content"]
        except Exception as e:
            _logger.error(f"Context snap synthesis failed: {e}")
            return history

        if raw_summary:
            formatted_summary = self.summarizer.format_summary(raw_summary)
            continuation_msg = self.summarizer.get_user_continuation_message(formatted_summary)
            return [Message(role=Role.USER, content=continuation_msg)]

        return history

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

        # Pre-flight: Task Classification
        self._report_status("Classifying engineering level...")
        level = await self.classifier.classify(str(user_prompt), config=config)
        self._report_status(f"Task classified as {level.value.upper()}")
        yield {"type": "info", "content": f"Engineering Level: {level.value.upper()}"}

        while True:
            turn_id += 1
            if turn_id > self.MAX_TURNS:
                _logger.warning(f"Maximum turns ({self.MAX_TURNS}) reached. Safety break.")
                yield {"type": "error", "content": f"Safety limit reached: Maximum turns ({self.MAX_TURNS}) exceeded."}
                break

            self._report_status(f"--- Agent Turn {turn_id} Start ---")
            await self.executor.initialize()
            yield {"status": AgentTurnStatus.THINKING}

            try:
                turn_start = time.time()
                turn_config = self._build_turn_config(config, level=level)
                async for event in self.provider.stream_turn(history, self.tools.get_all_schemas(), config=turn_config):
                    yield event
                    # Guard: status-only chunks (e.g. {'status': THINKING}) have no 'type' key
                    if event.get("type") == "metrics":
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
            except (TimeoutError, asyncio.TimeoutError) as exc:
                elapsed = time.time() - turn_start
                strategy = self.timeout_recovery.handle_timeout(
                    error=exc,
                    provider=getattr(self.client, "provider", "unknown"),
                    elapsed=elapsed,
                    current_attempt=turn_id,
                )

                if strategy["action"] == "retry_with_backoff":
                    wait_time = strategy["backoff_seconds"]
                    _logger.info(f"Waiting {wait_time}s before retrying due to timeout...")
                    yield {"type": "info", "content": f"Network timeout, retrying in {wait_time}s..."}
                    await asyncio.sleep(wait_time)
                    continue
                elif strategy["action"] == "reduce_context_and_retry":
                    if len(history) > 20:
                        keep = [history[0]] + history[-19:]
                        history.clear()
                        history.extend(keep)
                    _logger.info("Context reduced due to timeout, retrying...")
                    yield {"type": "info", "content": "Reducing context due to model timeout..."}
                    continue
                elif strategy["action"] == "simple_retry":
                    if strategy.get("retries_left", 0) > 0:
                        yield {"type": "info", "content": "Simple retry after timeout..."}
                        continue
                    else:
                        _logger.error(f"Critical error during turn {turn_id}: timeouts exhausted ({exc})")
                        yield {"type": "error", "content": f"Critical model failure: {exc}"}
                        break
            except Exception as exc:
                _logger.error(f"Critical error during turn {turn_id}: {exc}")
                yield {"type": "error", "content": f"Critical model failure: {exc}"}
                break

            if not assistant_msg.tool_calls:
                # If there was an error in the previous turn and now there are no tool calls,
                # we should check if the agent is just giving up.
                last_msgs = [m for m in history[-3:] if m.role == Role.TOOL]
                if last_msgs and any("Error" in m.content for m in last_msgs):
                    _logger.warning("Agent finished without tool calls after a tool error.")

                self.active_status = AgentTurnStatus.COMPLETED
                yield {"status": AgentTurnStatus.COMPLETED}
                break

            # Redundancy detection: check if the same tool calls OR text are being repeated
            current_calls = [(tc.name, tc.arguments) for tc in assistant_msg.tool_calls]
            current_text = str(assistant_msg.content).strip()

            previous_calls = []
            previous_text = ""
            for m in reversed(history[:-1]):
                if isinstance(m, AssistantMessage):
                    if m.tool_calls:
                        previous_calls = [(tc.name, tc.arguments) for tc in m.tool_calls]
                    if m.content:
                        previous_text = str(m.content).strip()
                    break

            # Loop detection: check for identical tool calls or identical text
            is_loop = False
            loop_reason = ""

            if current_calls and current_calls == previous_calls:
                is_loop = True
                loop_reason = "Repeated tool calls"
            elif not current_calls and current_text and current_text.strip() == previous_text.strip():
                # Only flag text loop if no tools are involved, to allow tool-using agents to talk
                is_loop = True
                loop_reason = "Repeated text response"

            if is_loop:
                _logger.warning(f"Loop detected ({loop_reason}). Forcing RESET.")
                reset_prompt = (
                    f"CRITICAL SYSTEM ALERT: Stagnation/Loop detected ({loop_reason}).\n"
                    "You are repeating yourself without taking action. You MUST change strategy NOW:\n"
                    "1. If you were trying to use a complex tool, use 'run_shell_command' instead.\n"
                    "2. Stop explaining and start EXECUTING.\n"
                    "3. If you are stuck, perform a 'list_dir' of the current path to re-orient yourself.\n"
                    "Take a different path immediately."
                )
                history.append(Message(role=Role.SYSTEM, content=reset_prompt))
                yield {"status": AgentTurnStatus.THINKING}
                continue

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
                    "SYSTEM REFLECTION: Tool failure detected. "
                    "STRATEGY CHANGE REQUIRED: If 'write_file' or 'replace' failed due to complexity, "
                    "use 'run_shell_command' to perform the action using standard unix tools (sed, echo, cat). "
                    "Do not repeat the failed tool call with the same arguments."
                )
                history.append(Message(role=Role.SYSTEM, content=critique_prompt))
                yield {"status": AgentTurnStatus.THINKING}
