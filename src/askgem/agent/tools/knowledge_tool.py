from typing import Any

from ...core.identity_manager import KnowledgeManager
from .base import BaseTool as Tool


class KnowledgeTool(Tool):
    """
    Tool to query the Knowledge Hub.
    Designed for the transition to RAG: currently fetches modules by name,
    but supports a query parameter for future semantic search.
    """

    def __init__(self, manager: KnowledgeManager):
        self.manager = manager

    @property
    def name(self) -> str:
        return "query_knowledge"

    @property
    def description(self) -> str:
        return (
            "Retrieves detailed information from the Knowledge Hub (Standard, Global, or Local rules). "
            "Use this when you need to consult specific project standards, architectural rules, or personal preferences "
            "listed in your Knowledge Index."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
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

    async def execute(self, module_name: str, query: str | None = None) -> str:
        content = self.manager.get_module_content(module_name)
        if not content:
            return f"Error: Knowledge module '{module_name}' not found in the hub."

        return f"### KNOWLEDGE MODULE: {module_name.upper()}\n\n{content}"
