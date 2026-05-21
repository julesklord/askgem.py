import logging
from typing import Any

from pydantic import BaseModel, Field

from ..blueprints import BLUEPRINTS
from ..orchestrator import AgentOrchestrator
from ..schema import ToolResult
from .base import BaseTool, ToolRegistry

_logger = logging.getLogger("mentask")


class SubagentInput(BaseModel):
    mission_name: str = Field(..., description="A short descriptive name for the sub-task")
    specialist_type: str = Field(
        ..., description="The type of specialist to spawn. Valid values: 'explorer', 'verifier', 'generalist'"
    )
    prompt: str = Field(..., description="The specific objective, context, and expected output for the subagent")


class SubagentTool(BaseTool):
    """
    Tool to spawn specialized sub-agents based on reference_code patterns.
    Delegates research or verification tasks to a separate agent instance.
    """

    name = "delegate_mission"
    description = (
        "Spawns a specialized subagent (Explorer, Verifier, or Generalist) to handle a sub-task autonomously. "
        "The subagent will perform its mission and return a final comprehensive report. "
        "Use 'explorer' for deep research, 'verifier' for adversarial testing of changes, "
        "and 'generalist' for complex tasks that require file modification."
    )
    input_schema = SubagentInput

    def __init__(self, session_manager: Any, tool_registry: ToolRegistry, config: Any):
        self.session = session_manager
        self.tools = tool_registry
        self.config = config

    def _filter_tools(self, specialist_type: str) -> ToolRegistry:
        """Creates a restricted tool registry for the specialist."""
        new_registry = ToolRegistry()

        if specialist_type == "generalist":
            # Generalist gets access to everything
            for _name, tool in self.tools.get_all_tools().items():
                new_registry.register(tool)
            return new_registry

        # Base tools allowed for everyone (read-only + communication)
        allowed_base = {
            "list_dir",
            "read_file",
            "grep_search",
            "glob_find",
            "query_knowledge",
            "working_memory",
            "analyze_codebase",
            "web_search",
            "web_fetch",
        }

        if specialist_type == "explorer":
            # Explorer is strictly read-only
            pass
        elif specialist_type == "verifier":
            # Verifier needs to run tests
            allowed_base.update({"execute_command", "python_repl"})

        for name in allowed_base:
            tool = self.tools.get_tool(name)
            if tool:
                new_registry.register(tool)

        return new_registry

    async def execute(self, mission_name: str, specialist_type: str, prompt: str) -> ToolResult:
        blueprint = BLUEPRINTS.get(specialist_type.lower())
        if not blueprint:
            return ToolResult(
                tool_call_id="",
                content=f"Error: Unknown specialist type '{specialist_type}'. Valid: {list(BLUEPRINTS.keys())}",
                is_error=True,
            )

        _logger.info(f"Spawned Subagent [{specialist_type.upper()}] for mission: {mission_name}")

        # Restricted tool registry for the subagent
        restricted_tools = self._filter_tools(specialist_type)

        # Create a new orchestrator for the subagent
        sub_orchestrator = AgentOrchestrator(self.session, restricted_tools, self.config)

        # Use mission_name for status reporting if a callback exists
        if sub_orchestrator.status_callback:
            orig_callback = sub_orchestrator.status_callback
            sub_orchestrator.status_callback = lambda msg: orig_callback(f"[{mission_name}] {msg}")

        # Override system instruction for this run
        sub_config = self.config.settings.copy()
        sub_config["system_instruction"] = blueprint

        history = []
        report_chunks = []

        try:
            # Run the subagent loop until completion
            # We wrap the user prompt to give clear instructions to the subagent instance
            sub_prompt = f"YOUR MISSION: {mission_name}\n\nOBJECTIVE:\n{prompt}"

            async for event in sub_orchestrator.run_query(sub_prompt, history, config=sub_config):
                if event.get("type") == "text":
                    report_chunks.append(event["content"])
                elif event.get("type") == "metrics":
                    # Add subagent usage to main session metrics
                    usage = event["usage"]
                    if hasattr(self.session, "metrics") and self.session.metrics:
                        self.session.metrics.add_usage(usage.input_tokens, usage.output_tokens)
                elif event.get("type") == "error":
                    return ToolResult(tool_call_id="", content=f"Subagent Error: {event['content']}", is_error=True)

            final_report = "".join(report_chunks)
            verdict = self._extract_verdict(final_report)

            formatted_report = (
                f"### MISSION COMPLETE: {mission_name.upper()}\n"
                f"**Specialist**: {specialist_type.capitalize()}\n"
                f"**Verdict**: {verdict}\n\n"
                f"{final_report}"
            )

            _logger.info(f"Subagent mission '{mission_name}' finished with verdict: {verdict}")
            return ToolResult(tool_call_id="", content=formatted_report, is_error=False)

        except Exception as e:
            _logger.exception(f"Critical failure in subagent mission {mission_name}")
            return ToolResult(content=f"Subagent mission failed: {str(e)}", is_error=True)

    def _extract_verdict(self, text: str) -> str:
        if "VERDICT: PASS" in text:
            return "PASS"
        if "VERDICT: FAIL" in text:
            return "FAIL"
        if "VERDICT: PARTIAL" in text:
            return "PARTIAL"
        return "N/A (Informational)"
