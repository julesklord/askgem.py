import logging
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_logger = logging.getLogger("mentask")


class MCPManager:
    """
    Manages connections to external MCP (Model Context Protocol) servers.
    Handles tool discovery and execution from these servers.
    """

    def __init__(self, config=None):
        self.config = config
        self._server_contexts = {}  # name -> (read, write, session)
        self._tools_cache = {}  # tool_name -> server_name

    async def connect_all(self):
        """Connects to all servers defined in the configuration."""
        if not self.config:
            return

        mcp_config = self.config.settings.get("mcp_servers", {})
        for name, params in mcp_config.items():
            cmd = params.get("command")
            args = params.get("args", [])
            await self.connect_stdio(name, cmd, args)

    async def connect_stdio(self, name: str, command: str, args: list[str]):
        """Starts a persistent stdio connection to an MCP server."""
        try:
            params = StdioServerParameters(command=command, args=args, env=None)
            # We store the context manager to keep it alive
            ctx = stdio_client(params)
            read, write = await ctx.__aenter__()
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()

            self._server_contexts[name] = (ctx, session)

            # Cache tools
            tools_result = await session.list_tools()
            for tool in tools_result.tools:
                self._tools_cache[tool.name] = name
                _logger.info(f"Registered MCP tool '{tool.name}' from server '{name}'")

        except Exception as e:
            _logger.error(f"Failed to connect to MCP server {name}: {e}")

    async def get_all_tools(self) -> list[Any]:
        """Returns all tools from all active MCP sessions."""
        all_tools = []
        for name, (ctx, session) in self._server_contexts.items():
            try:
                res = await session.list_tools()
                all_tools.extend(res.tools)
            except Exception:
                pass
        return all_tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Invokes an MCP tool by name."""
        server_name = self._tools_cache.get(tool_name)
        if not server_name:
            return f"Error: MCP tool '{tool_name}' not found."

        _, session = self._server_contexts[server_name]
        try:
            result = await session.call_tool(tool_name, arguments)
            # Convert result to string for Agent
            return "\n".join([str(c.text) for c in result.content if hasattr(c, "text")])
        except Exception as e:
            return f"Error calling MCP tool {tool_name}: {str(e)}"

    async def shutdown(self):
        """Cleanly closes all MCP connections."""
        for name, (ctx, session) in self._server_contexts.items():
            try:
                await session.__aexit__(None, None, None)
                await ctx.__aexit__(None, None, None)
            except Exception:
                pass
