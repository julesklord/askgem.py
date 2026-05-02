from unittest.mock import MagicMock, patch

import pytest

from mentask.agent.tools.base import ToolRegistry
from mentask.core.plugin_loader import PluginLoader


@pytest.mark.asyncio
async def test_plugin_loader_loads_from_untrusted_workspace(tmp_path):
    # Setup: a "workspace" with a .mentask/plugins/ directory
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    plugins_dir = workspace / ".mentask" / "plugins"
    plugins_dir.mkdir(parents=True)

    plugin_file = plugins_dir / "malicious.py"
    plugin_file.write_text("""
from mentask.agent.tools.base import BaseTool
from mentask.agent.schema import ToolResult

class MaliciousTool(BaseTool):
    name = "malicious_tool"
    description = "A malicious tool"
    async def execute(self, **kwargs):
        return ToolResult(tool_call_id="", content="pwned")
""")

    registry = ToolRegistry()
    # Mock os.getcwd and Path.cwd to return the workspace
    with (
        patch("os.getcwd", return_value=str(workspace)),
        patch("pathlib.Path.cwd", return_value=workspace),
        patch("mentask.core.paths.get_config_dir", return_value=workspace / ".mentask"),
    ):
        loader = PluginLoader(registry)
        loader.discover_and_load()

    # CURRENT BEHAVIOR: It loads it regardless of trust
    assert registry.get_tool("malicious_tool") is not None


@pytest.mark.asyncio
async def test_plugin_loader_requires_trust_after_fix(tmp_path):
    workspace = tmp_path / "workspace_secure"
    workspace.mkdir()
    plugins_dir = workspace / ".mentask" / "plugins"
    plugins_dir.mkdir(parents=True)

    plugin_file = plugins_dir / "secure_tool.py"
    plugin_file.write_text("""
from mentask.agent.tools.base import BaseTool
from mentask.agent.schema import ToolResult

class SecureTool(BaseTool):
    name = "secure_tool"
    description = "A secure tool"
    async def execute(self, **kwargs):
        return ToolResult(tool_call_id="", content="safe")
""")

    registry = ToolRegistry()
    mock_trust_manager = MagicMock()

    # CASE 1: Untrusted
    mock_trust_manager.is_trusted.return_value = False

    with (
        patch("os.getcwd", return_value=str(workspace)),
        patch("pathlib.Path.cwd", return_value=workspace),
        patch("mentask.core.paths.get_config_dir", return_value=workspace / ".mentask"),
    ):
        loader = PluginLoader(registry, trust_manager=mock_trust_manager)
        loader.discover_and_load()

    assert registry.get_tool("secure_tool") is None

    # CASE 2: Trusted
    mock_trust_manager.is_trusted.return_value = True

    with (
        patch("os.getcwd", return_value=str(workspace)),
        patch("pathlib.Path.cwd", return_value=workspace),
        patch("mentask.core.paths.get_config_dir", return_value=workspace / ".mentask"),
    ):
        loader = PluginLoader(registry, trust_manager=mock_trust_manager)
        loader.discover_and_load()

    assert registry.get_tool("secure_tool") is not None


@pytest.mark.asyncio
async def test_plugin_loader_rejects_missing_basetool(tmp_path):
    workspace = tmp_path / "workspace_basetool"
    workspace.mkdir()
    plugins_dir = workspace / ".mentask" / "plugins"
    plugins_dir.mkdir(parents=True)

    plugin_file = plugins_dir / "invalid_tool.py"
    plugin_file.write_text("""
class NotATool:
    pass
""")

    registry = ToolRegistry()
    mock_trust_manager = MagicMock()
    mock_trust_manager.is_trusted.return_value = True  # Trusted for this test

    with (
        patch("os.getcwd", return_value=str(workspace)),
        patch("pathlib.Path.cwd", return_value=workspace),
        patch("mentask.core.paths.get_config_dir", return_value=workspace / ".mentask"),
    ):
        loader = PluginLoader(registry, trust_manager=mock_trust_manager)
        loader.discover_and_load()

    assert len(registry._tools) == 0
