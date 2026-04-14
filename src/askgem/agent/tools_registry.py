"""
Central tool registry and dispatcher for the AskGem agent.

Decouples the tool execution logic from the main conversational loop.
It does NOT manage the conversation state or UI rendering.
"""

import asyncio
import functools
import inspect
from typing import TYPE_CHECKING, Callable, List, Optional

from google.genai import types

from ..core.i18n import _
from ..core.security import SafetyLevel, analyze_command_safety
from ..tools.file_tools import delete_file, diff_file, edit_file, list_directory, move_file, read_file
from ..tools.memory_tools import manage_memory, manage_mission
from ..tools.search_tools import glob_find, grep_search
from ..tools.system_tools import execute_bash
from ..tools.web_tools import web_fetch, web_search
from .ui_interface import ToolUIAdapter

if TYPE_CHECKING:
    from ..core.config_manager import ConfigManager



class ToolDispatcher:
    """Handles tool registration and execution routing for the ChatAgent."""

    def __init__(
        self,
        config: 'ConfigManager',
        ui: ToolUIAdapter,
        logger: Optional[Callable[[str], None]] = None,
    ):
        """Initializes the dispatcher with a UI adapter and configuration."""
        self.config = config
        self.ui = ui
        self.logger = logger
        self.modified_files_count = 0

        # Pre-bind keys to the web_search tool
        bound_web_search = functools.partial(
            web_search,
            api_key=self.config.settings.get("google_search_api_key", ""),
            cx_id=self.config.settings.get("google_cx_id", ""),
        )
        # Preserve original docstring for the LLM
        bound_web_search.__doc__ = web_search.__doc__

        self._tools = [
            list_directory,
            execute_bash,
            read_file,
            edit_file,
            delete_file,
            move_file,
            diff_file,
            grep_search,
            glob_find,
            bound_web_search,
            web_fetch,
            manage_memory,
            manage_mission,
        ]

        # Create a name-to-function mapping for fast dispatch
        self._tool_map = {
            getattr(t, "__name__", "web_search" if isinstance(t, functools.partial) else str(t)): t for t in self._tools
        }
        # Special handling for partials where __name__ might not be present
        if "web_search" not in self._tool_map:
            self._tool_map["web_search"] = bound_web_search

    def get_tools_list(self) -> List:
        """Returns the list of registered tool functions for the Gemini SDK.

        Returns:
            List: A list of callable tool functions.
        """
        return self._tools

    async def execute(self, function_call: types.FunctionCall) -> types.Part:
        """Routes and executes a model-requested function call (Async).

        Args:
            function_call (types.FunctionCall): The tool request from the API.

        Returns:
            types.Part: The SDK part response with results.
        """
        tool_name = function_call.name
        if not tool_name:
            return types.Part.from_function_response(
                name="unknown",
                response={"error": "Tool name was missing from function_call"}
            )

        args = function_call.args if function_call.args else {}

        # Log tool call to UI/Logger
        if self.logger:
            self.logger(f"Tool Call: {tool_name} with args: {args}")

        # UI Status indicator (usually a spinner)
        self.ui.log_status(f"{_('tool.spawning')} {tool_name}...", level="info")

        result = await self._dispatch(tool_name, args)

        # Truncate result if it exceeds 10,000 characters
        MAX_CHARS = 10_000
        if isinstance(result, str) and len(result) > MAX_CHARS:
            result = result[:MAX_CHARS] + f"\n\n... [!] Result truncated at {MAX_CHARS} characters to avoid context overflow."

        if self.logger:
            # Note: We should probably move the result logging to the UI adapter too
            result_summary = str(result)[:500]
            self.logger(f"Tool Result: {result_summary}...")

        return types.Part.from_function_response(
            name=tool_name,
            response={"result": result},
        )

    async def _dispatch(self, tool_name: str, args: dict) -> str:
        """Internal async dispatch logic using a mapping and asyncio.to_thread."""

        if tool_name not in self._tool_map:
            return _("tool.unregistered", name=tool_name)

        tool_func = self._tool_map[tool_name]

        # 1. Interactive Tools (Require confirmation and thread-blocking UI)
        if tool_name == "delete_file":
            path = args.get("path", "")
            if self.config.settings.get("edit_mode", "manual") == "manual" and not await self.ui.confirm_action(f"¿Eliminar archivo [bold]'{path}'[/bold]?"):
                return _("tool.denied.edit")
            return await asyncio.to_thread(delete_file, path)

        if tool_name == "move_file":
            source = args.get("source", "")
            destination = args.get("destination", "")
            if self.config.settings.get("edit_mode", "manual") == "manual":
                message = f"¿Mover [bold]'{source}'[/bold] a [bold]'{destination}'[/bold]?"
                if not await self.ui.confirm_action(message):
                    return _("tool.denied.edit")
            return await asyncio.to_thread(move_file, source, destination)

        if tool_name == "execute_bash":
            command = args.get("command", "")

            # Analyze safety report
            report = analyze_command_safety(command)

            if report.level == SafetyLevel.SAFE:
                self.ui.log_status(f"Auto-executing safe command: {command}", level="info")
                return await execute_bash(command)

            # Map SafetyLevel to UI severity string
            sev_map = {
                SafetyLevel.NOTICE: "info",
                SafetyLevel.WARNING: "warning",
                SafetyLevel.DANGEROUS: "error"
            }
            severity = sev_map.get(report.level, "info")

            msg = f"{_('tool.wants_run')} [bold]'{command}'[/bold]"
            detail = f"Safety Analysis: [bold]{report.category}[/bold]\n{report.description}"
            if report.pattern:
                detail += f"\nPattern matched: [dim]{report.pattern}[/dim]"

            if not await self.ui.confirm_action(msg, detail=detail, severity=severity):
                return _("tool.denied.cmd")

            return await execute_bash(command)

        if tool_name == "edit_file":
            path = args.get("path", "")
            find_text = args.get("find_text", "")
            replace_text = args.get("replace_text", "")

            if self.config.settings.get("edit_mode", "manual") == "manual":
                detail = (
                    f"[dim]--- Replacing ---[/dim]\n{find_text}\n"
                    f"[dim]--- With ---[/dim]\n{replace_text}\n"
                    f"[dim]-----------------[/dim]"
                )
                if not await self.ui.confirm_action(f"{_('tool.wants_edit')} [bold]'{path}'[/bold]", detail=detail):
                    return _("tool.denied.edit")
            else:
                self.ui.log_status(_('tool.edit.auto', path=path), level="success")

            res = await asyncio.to_thread(edit_file, path, find_text, replace_text)
            if res.startswith("Success:"):
                self.modified_files_count += 1
            return res

        # 2. Standard Tools (Executed in a thread to avoid blocking the event loop)
        try:
            if inspect.iscoroutinefunction(tool_func):
                return await tool_func(**args)
            return await asyncio.to_thread(tool_func, **args)
        except TypeError:
            # Fallback for tools that might not accept all keyword arguments from Gemini (rare)
            # This is a safety net for bound methods or complex signatures
            return await asyncio.to_thread(tool_func, *args.values())
        except Exception as e:
            return f"Error executing {tool_name}: {e}"
