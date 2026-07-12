"""
Tool registry factory for mentask.

Builds and configures the default tool registry with all built-in tools.
Separated from ChatAgent to reduce god-class complexity.
"""

import logging
from typing import TYPE_CHECKING

from .tools.analysis_tools import AnalyzeTool
from .tools.base import ToolRegistry
from .tools.delegation_tools import SubagentTool
from .tools.file_tools import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from .tools.git_tools import GitCommitTool
from .tools.knowledge_tool import KnowledgeTool
from .tools.memory_tool import MemoryTool
from .tools.plan_tool import PlanTool
from .tools.plugin_tools import ForgePluginTool
from .tools.repl_tool import PythonReplTool
from .tools.search_tool import GlobFindTool, GrepSearchTool
from .tools.shell_tools import ShellTool
from .tools.user_tool import AskUserTool
from .tools.web_tool import WebFetchTool, WebSearchTool
from .tools.working_memory_tool import WorkingMemoryTool
from .tools.worktree_tools import EnterWorktreeTool, ExitWorktreeTool

if TYPE_CHECKING:
    from ..core.config_manager import ConfigManager
    from ..core.identity_manager import KnowledgeManager
    from .core.session import SessionManager

_logger = logging.getLogger("mentask.agent.tool_factory")


def build_default_tool_registry(
    config: "ConfigManager",
    identity: "KnowledgeManager",
    session: "SessionManager",
) -> ToolRegistry:
    """Constructs and returns the default ToolRegistry with all built-in tools.

    Args:
        config: Application configuration manager.
        identity: Knowledge/identity manager for project context.
        session: Active session manager for provider access.

    Returns:
        A fully configured ToolRegistry instance.
    """
    registry = ToolRegistry()

    # File operations
    registry.register(ListDirTool())
    registry.register(ReadFileTool(config))
    registry.register(WriteFileTool())
    registry.register(EditFileTool())

    # Execution
    registry.register(ShellTool(config))
    registry.register(PythonReplTool())

    # Memory & Knowledge
    registry.register(MemoryTool())
    registry.register(WorkingMemoryTool())
    registry.register(PlanTool())
    registry.register(KnowledgeTool(identity))

    # Search
    registry.register(GrepSearchTool())
    registry.register(GlobFindTool())

    # Analysis
    registry.register(AnalyzeTool())

    # User interaction
    registry.register(AskUserTool())

    # Git
    registry.register(GitCommitTool())

    # Plugin synthesis
    registry.register(ForgePluginTool(registry))

    # Subagent delegation
    registry.register(SubagentTool(session, registry, config))

    # Worktree management
    registry.register(EnterWorktreeTool())
    registry.register(ExitWorktreeTool())

    # Web tools (conditional)
    if config.settings.get("web_search_enabled", True):
        registry.register(WebSearchTool(config))
        registry.register(WebFetchTool())

    _logger.info("Default tool registry built with %d tools", len(registry._tools))
    return registry
