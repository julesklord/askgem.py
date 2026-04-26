from pathlib import Path

from .base import BaseTool, ToolResult


class PlanTool(BaseTool):
    """Manage execution plan checkpoints."""

    name = "plan"
    description = (
        "Read, update, or checkpoint the active execution plan. "
        "Mark steps as complete to track progress across sessions."
    )

    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["read", "mark_complete", "clear"]},
            "step_index": {"type": "integer", "description": "Step number (1-indexed) for mark_complete"},
        },
        "required": ["action"],
    }

    def __init__(self):
        super().__init__()
        self.plan_file = Path.cwd() / ".mentask_plan.md"

    async def execute(self, action: str, step_index: int = 0) -> ToolResult:
        if action == "read":
            if not self.plan_file.exists():
                return ToolResult(content="No plan file found.", is_error=False)

            try:
                content = self.plan_file.read_text(encoding="utf-8")
                return ToolResult(content=content, is_error=False)
            except Exception as e:
                return ToolResult(content=f"Error reading plan: {e}", is_error=True)

        elif action == "mark_complete":
            if not self.plan_file.exists():
                return ToolResult(content="No plan file found.", is_error=True)

            try:
                lines = self.plan_file.read_text(encoding="utf-8").splitlines()

                item_count = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith("- [ ]"):
                        item_count += 1
                        if item_count == step_index:
                            lines[i] = line.replace("- [ ]", "- [x]", 1)
                            self.plan_file.write_text("\n".join(lines), encoding="utf-8")
                            return ToolResult(content=f"Marked step {step_index} as complete.", is_error=False)

                return ToolResult(content=f"Pending step {step_index} not found.", is_error=True)
            except Exception as e:
                return ToolResult(content=f"Error updating plan: {e}", is_error=True)

        elif action == "clear":
            if self.plan_file.exists():
                try:
                    self.plan_file.unlink()
                except Exception as e:
                    return ToolResult(content=f"Failed to clear plan: {e}", is_error=True)
            return ToolResult(content="Plan file cleared.", is_error=False)

        return ToolResult(content=f"Unknown action: {action}", is_error=True)
