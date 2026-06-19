"""
MCP Server for mentask.
Exposes all mentask tools and integrations via the Model Context Protocol (MCP).
"""

import asyncio
import logging
import sys
from typing import Any

from mcp import types  # type: ignore[import-not-found]
from mcp.server import Server  # type: ignore[import-not-found]
from mcp.server.stdio import stdio_server  # type: ignore[import-not-found]

from ..agent.chat import ChatAgent
from .console import console

# Configure logging to stderr so it does not interfere with stdio JSON-RPC transport
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
_logger = logging.getLogger("mentask-mcp-server")


async def serve() -> None:
    """Runs the MCP server over standard input/output streams."""
    _logger.info("Initializing mentask MCP server...")

    # 1. Initialize the ChatAgent silently.
    # In MCP mode, we don't start the interactive shell loop.
    # We just instantiate ChatAgent to resolve and load all default tools and configuration.
    agent = ChatAgent(local_mode=False)

    # 2. Load dynamic/plugin tools if any are configured
    try:
        agent.tools.load_dynamic_plugins()
    except Exception as e:
        _logger.warning(f"Failed to load dynamic plugins: {e}")

    registry = agent.tools

    # 3. Create the low-level MCP server instance
    server = Server("mentask-mcp-server")

    # 4. Define the list tools handler
    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """Exposes all registered mentask tools to the client."""
        mcp_tools = []
        for t in registry.get_all_schemas():
            mcp_tools.append(
                types.Tool(
                    name=t["name"],
                    description=t["description"],
                    inputSchema=t["parameters"],
                )
            )
        _logger.info(f"Listing {len(mcp_tools)} tools for MCP client")
        return mcp_tools

    # 5. Define the call tool handler
    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        """Routes MCP tool calls to the matching mentask tool in the registry."""
        _logger.info(f"Executing tool: {name} with arguments: {arguments}")

        try:
            # Execute tool with unique identifier
            result = await registry.call_tool(name, "mcp_call", arguments)

            # Map tool output to MCP text content
            content_blocks: list[Any] = [
                types.TextContent(
                    type="text",
                    text=result.content,
                )
            ]

            return types.CallToolResult(
                content=content_blocks,
                isError=result.is_error,
            )
        except Exception as e:
            _logger.error(f"Error executing tool {name}: {e}")
            err_blocks: list[Any] = [
                types.TextContent(type="text", text=f"Error executing tool: {str(e)}")
            ]
            return types.CallToolResult(
                content=err_blocks,
                isError=True,
            )

    # 6. Run the stdio transport server
    async with stdio_server() as (read_stream, write_stream):
        # Redirect stdout of this process to stderr to prevent any printing/console logs
        # from corrupting the JSON-RPC streams.
        sys.stdout = sys.stderr
        console.file = sys.stderr

        _logger.info("mentask MCP server is now running on standard I/O streams.")

        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """CLI entry point for starting the mentask MCP server."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        _logger.info("mentask MCP server shutdown gracefully.")
    except Exception as e:
        _logger.critical(f"Fatal error running mentask MCP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
