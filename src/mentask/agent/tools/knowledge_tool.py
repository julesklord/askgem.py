from ...core.identity_manager import KnowledgeManager
from .base import BaseTool as Tool
from .base import ToolResult


class KnowledgeTool(Tool):
    """
    Tool to query the Knowledge Hub.
    Designed for the transition to RAG: currently fetches modules by name,
    but supports a query parameter for future semantic search.
    """

    name = "query_knowledge"
    description = (
        "Retrieves detailed information from the Knowledge Hub (Standard, Global, or Local rules). "
        "Use this when you need to consult specific project standards, architectural rules, or personal preferences "
        "listed in your Knowledge Index."
    )
    parameters = {
        "type": "object",
        "properties": {
            "module_name": {
                "type": "string",
                "description": "The name of the module to retrieve from the index (e.g., 'RULES', 'ROLE', 'PROJECT_SPEC').",
            },
            "query": {
                "type": "string",
                "description": "Specific question or topic to search for within the knowledge hub (Future-proofing for RAG).",
            },
        },
        "required": ["module_name"],
    }

    def __init__(self, manager: KnowledgeManager):
        self.manager = manager

    async def execute(self, module_name: str, query: str | None = None) -> ToolResult:
        content = self.manager.get_module_content(module_name)
        if not content:
            return ToolResult(
                tool_call_id="",
                content=f"Error: Knowledge module '{module_name}' not found in the hub.",
                is_error=True,
            )

        return ToolResult(
            tool_call_id="", content=f"### KNOWLEDGE MODULE: {module_name.upper()}\n\n{content}", is_error=False
        )
