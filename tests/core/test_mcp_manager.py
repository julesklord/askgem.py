import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from mentask.core.mcp_manager import MCPManager

@pytest.mark.asyncio
async def test_mcp_manager_initialization():
    config = MagicMock()
    config.settings = {
        "mcp_servers": {
            "test_server": {
                "command": "node",
                "args": ["server.js"]
            }
        }
    }
    
    manager = MCPManager(config)
    
    with patch.object(manager, "connect_stdio", new_callable=AsyncMock) as mock_connect:
        await manager.connect_all()
        mock_connect.assert_called_once_with("test_server", "node", ["server.js"])

@pytest.mark.asyncio
async def test_mcp_manager_call_tool_not_found():
    manager = MCPManager()
    result = await manager.call_tool("unknown_tool", {})
    assert "not found" in result

@pytest.mark.asyncio
async def test_mcp_manager_shutdown():
    manager = MCPManager()
    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    
    manager._server_contexts["test"] = (mock_ctx, mock_session)
    
    await manager.shutdown()
    
    mock_session.__aexit__.assert_called_once()
    mock_ctx.__aexit__.assert_called_once()
