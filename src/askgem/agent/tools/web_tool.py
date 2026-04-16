from pydantic import BaseModel, Field

from ...tools.web_tools import web_fetch, web_search
from ..schema import ToolResult
from .base import BaseTool


class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query to look up on the internet.")

class WebSearchTool(BaseTool):
    """Search the web for information using Google or DuckDuckGo."""
    name = "web_search"
    description = (
        "Search the internet for real-time information, documentation, or news. "
        "Returns a list of titles and snippets from top search results."
    )
    input_schema = WebSearchInput
    requires_confirmation = False

    def __init__(self, config=None):
        self.config = config

    async def execute(self, query: str) -> ToolResult:
        api_key = None
        cx_id = None
        if self.config:
            api_key = self.config.settings.get("google_search_api_key")
            cx_id = self.config.settings.get("google_cx_id")

        result = await web_search(query, api_key, cx_id)
        return ToolResult(tool_call_id="", content=result)

class WebFetchInput(BaseModel):
    url: str = Field(..., description="The URL of the page to fetch and read.")

class WebFetchTool(BaseTool):
    """Fetches and cleans the text content of a URL."""
    name = "web_fetch"
    description = (
        "Download and read the text content of a webpage. Useful for reading "
        "online documentation or articles. Content is cleaned (minified) to save tokens."
    )
    input_schema = WebFetchInput
    requires_confirmation = False

    async def execute(self, url: str) -> ToolResult:
        result = await web_fetch(url)
        return ToolResult(tool_call_id="", content=result)
