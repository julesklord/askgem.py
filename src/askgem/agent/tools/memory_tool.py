from pydantic import BaseModel, Field

from ..schema import ToolResult
from .base import BaseTool


class ManageMemoryInput(BaseModel):
    action: str = Field(
        description="Action to perform: 'add' to remember a fact, 'read' to view memory, 'reset' to wipe it."
    )
    content: str = Field(default="", description="The fact or information to remember (required for 'add').")
    category: str = Field(
        default="Lessons Learned & Facts",
        description="The markdown section header (e.g., 'Project Patterns', 'User Preferences').",
    )
    scope: str = Field(
        default="local",
        description="Where to store/read: 'local' for project-specific knowledge (.askgem_knowledge.md), 'global' for user preferences (memory.md), or 'all' to read both.",
    )


class MemoryTool(BaseTool):
    name = "manage_memory"
    description = "Manage your long-term persistent memory and project knowledge. Use this to 'learn' new patterns or preferences."
    input_schema = ManageMemoryInput

    async def execute(
        self, action: str, content: str = "", category: str = "Lessons Learned & Facts", scope: str = "local"
    ) -> ToolResult:
        try:
            # We call the core function from memory_tools.py
            # But wait, managing scope should be handled correctly.
            # I'll directly use the singleton _memory from memory_tools but I need to make sure
            # the legacy function supports 'scope'.
            # Actually, I'll bypass the legacy function and use MemoryManager directly for cleaner logic.
            from ...tools.memory_tools import _memory

            if action == "add":
                if not content:
                    return ToolResult(
                        tool_call_id="", content="Error: content is required for 'add' action.", is_error=True
                    )
                if _memory.add_fact(content, category, scope=scope):
                    return ToolResult(
                        tool_call_id="", content=f"Success: Fact remembered in '{category}' (scope={scope})."
                    )
                return ToolResult(tool_call_id="", content="Error: Failed to update memory.", is_error=True)

            elif action == "read":
                result = _memory.read_memory(scope=scope)
                return ToolResult(tool_call_id="", content=result)

            elif action == "reset":
                _memory.reset_memory(scope=scope)
                return ToolResult(tool_call_id="", content=f"Success: Memory reset (scope={scope}).")

            return ToolResult(tool_call_id="", content=f"Error: Unknown action '{action}'.", is_error=True)

        except Exception as e:
            return ToolResult(tool_call_id="", content=f"Error managing memory: {str(e)}", is_error=True)
