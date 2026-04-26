import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.mentask.agent.orchestrator import AgentOrchestrator
from src.mentask.agent.schema import ToolResult
from src.mentask.agent.tools.base import ToolRegistry


@pytest.mark.asyncio
async def test_lsp_integration_injects_diagnostics():
    # 1. Setup
    client = MagicMock()
    # Mock stream generator to do nothing (we focus on tool execution part)
    client.generate_stream = MagicMock()

    registry = MagicMock(spec=ToolRegistry)
    tool = MagicMock()
    tool.name = "edit_file"
    tool.requires_confirmation = False
    registry.get_tool.return_value = tool

    # Simulate a tool execution that returns success but leaves a broken file
    broken_path = "test_integration_broken.py"
    with open(broken_path, "w", encoding="utf-8") as f:
        f.write("def bad_code()\n    pass")  # Missing colon

    registry.call_tool = AsyncMock(
        return_value=ToolResult(
            tool_call_id="tc-1", content=f"Success: Replaced text in '{broken_path}'.", is_error=False
        )
    )

    orchestrator = AgentOrchestrator(client, registry)
    # The lsp client is now in the executor
    orchestrator.executor.lsp = AsyncMock()
    orchestrator.executor.lsp.check_file.return_value = [
        {
            "severity": 1,
            "message": "Expected `:`",
            "range": {"start": {"line": 0}},
        }
    ]

    # 2. Simulate the tool execution block within run_query logic
    tc = MagicMock()
    tc.id = "tc-1"
    tc.name = "edit_file"
    tc.arguments = {"path": broken_path}

    res = await registry.call_tool("edit_file", "tc-1", tc.arguments)

    # Call it through the executor
    res = await orchestrator.executor.append_lsp_diagnostics(tc, res)

    # 3. Assert
    assert "[LSP DIAGNOSTICS - Syntax/Lint Errors Detected]" in res.content
    assert "Expected `:`" in res.content
    orchestrator.executor.lsp.check_file.assert_awaited_once()

    # Cleanup
    if os.path.exists(broken_path):
        os.remove(broken_path)
