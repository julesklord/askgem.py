"""MCP (Model Context Protocol) connection manager for mentask.

Each MCP server is started as a subprocess via ``stdio_client``.  This module
owns the full lifecycle of those connections:

- **Connect**: ``connect_all()`` / ``connect_stdio()``
- **Use**: ``get_all_tools()`` / ``call_tool()``
- **Disconnect**: ``shutdown()`` — guaranteed to run even if an error occurs,
  because the connection pairs are managed inside ``contextlib.AsyncExitStack``
  rather than raw ``__aenter__`` / ``__aexit__`` calls.
"""

import logging
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_logger = logging.getLogger("mentask.core.mcp")


class MCPManager:
    """Manages connections to external MCP (Model Context Protocol) servers.

    Handles tool discovery and execution from those servers.

    Resource safety
    ---------------
    Each ``(stdio_client, ClientSession)`` pair is entered via an
    ``AsyncExitStack``.  This guarantees that ``__aexit__`` is called for
    every context manager in reverse order regardless of whether an exception
    is raised during operation or shutdown.
    """

    def __init__(self, config: Any = None) -> None:
        self.config = config
        # name -> (exit_stack, session)
        self._server_contexts: dict[str, tuple[AsyncExitStack, ClientSession]] = {}
        # tool_name -> server_name
        self._tools_cache: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect_all(self) -> None:
        """Connects to all MCP servers defined in the configuration."""
        if not self.config:
            return

        mcp_config: dict[str, Any] = self.config.settings.get("mcp_servers", {})
        for name, params in mcp_config.items():
            cmd: str | None = params.get("command")
            args: list[str] = params.get("args", [])
            if not cmd:
                _logger.warning("MCP server '%s' has no 'command' configured, skipping.", name)
                continue
            await self.connect_stdio(name, cmd, args)

    async def connect_stdio(self, name: str, command: str, args: list[str]) -> None:
        """Starts a persistent stdio connection to an MCP server.

        Uses ``AsyncExitStack`` so both the transport and the session context
        managers are properly cleaned up on ``shutdown()``, even if the
        initialization fails partway through.
        """
        stack = AsyncExitStack()
        try:
            params = StdioServerParameters(command=command, args=args, env=None)

            # Enter the transport context manager via the stack
            read, write = await stack.enter_async_context(stdio_client(params))

            # Enter the session context manager via the same stack
            session: ClientSession = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            self._server_contexts[name] = (stack, session)

            # Discover and cache the tools this server provides
            tools_result = await session.list_tools()
            for tool in tools_result.tools:
                self._tools_cache[tool.name] = name
                _logger.info("Registered MCP tool '%s' from server '%s'", tool.name, name)

        except Exception as exc:
            _logger.error("Failed to connect to MCP server '%s': %s", name, exc)
            # Clean up any partially-entered context managers
            try:
                await stack.aclose()
            except Exception as cleanup_exc:
                _logger.debug("Error during MCP stack cleanup for '%s': %s", name, cleanup_exc)

    # ------------------------------------------------------------------
    # Tool operations
    # ------------------------------------------------------------------

    async def get_all_tools(self) -> list[Any]:
        """Returns all tools from all active MCP sessions."""
        all_tools: list[Any] = []
        for name, (_stack, session) in self._server_contexts.items():
            try:
                res = await session.list_tools()
                all_tools.extend(res.tools)
            except Exception as exc:
                _logger.warning("Failed to list tools from MCP server '%s': %s", name, exc)
        return all_tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Invokes an MCP tool by name.

        Returns the text output of the tool, or an error string if the tool
        is not found or the call fails.
        """
        server_name = self._tools_cache.get(tool_name)
        if not server_name:
            return f"Error: MCP tool '{tool_name}' not found."

        _stack, session = self._server_contexts[server_name]
        try:
            result = await session.call_tool(tool_name, arguments)
            return "\n".join(str(c.text) for c in result.content if hasattr(c, "text"))
        except Exception as exc:
            _logger.error("Error calling MCP tool '%s': %s", tool_name, exc)
            return f"Error calling MCP tool '{tool_name}': {exc}"

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def shutdown(self) -> None:
        """Cleanly closes all MCP connections in reverse-registration order.

        Each server's ``AsyncExitStack`` handles both the session and the
        transport teardown, guaranteeing cleanup even if one of the servers
        raises during ``__aexit__``.
        """
        for name, (stack, _session) in reversed(list(self._server_contexts.items())):
            try:
                await stack.aclose()
                _logger.debug("MCP server '%s' disconnected.", name)
            except Exception as exc:
                _logger.warning("Error while disconnecting MCP server '%s': %s", name, exc)

        self._server_contexts.clear()
        self._tools_cache.clear()
