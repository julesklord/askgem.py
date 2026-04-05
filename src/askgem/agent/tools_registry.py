"""
Central tool registry and dispatcher for the AskGem agent.

Decouples the tool execution logic from the main conversational loop.
"""

import asyncio
import functools
import inspect
from typing import TYPE_CHECKING, Callable, List, Optional

from google.genai import types
from rich.markup import escape
from rich.prompt import Confirm
from rich.status import Status

from ..cli.console import console
from ..core.i18n import _
from ..tools.file_tools import delete_file, diff_file, edit_file, list_directory, move_file, read_file
from ..tools.memory_tools import manage_memory, manage_mission
from ..tools.search_tools import glob_find, grep_search
from ..tools.system_tools import execute_bash
from ..tools.web_tools import web_fetch, web_search

if TYPE_CHECKING:
    from ..core.config_manager import ConfigManager



class ToolDispatcher:
    """Handles tool registration and execution routing for the ChatAgent."""

    def __init__(
        self,
        config: 'ConfigManager',
        logger: Optional[Callable[[str], None]] = None,
    ):
        """Initializes the dispatcher with a logger and credentials."""
        self.config = config
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
        """Returns the list of registered tool functions for the Gemini SDK."""
        return self._tools

    async def execute(self, function_call: types.FunctionCall) -> types.Part:
        """Routes and executes a model-requested function call (Async).

        Args:
            function_call (types.FunctionCall): The tool request from the API.

        Returns:
            types.Part: The SDK part response with results.
        """
        tool_name = function_call.name
        args = function_call.args if function_call.args else {}

        console.print()

        # Tool execution UI Wrapper
        with Status(f"[google.blue]{_('tool.spawning')} {tool_name}[/google.blue]", spinner="dots", console=console):
            if self.logger:
                # Escape arguments to prevent MarkupError in case of tools like cat or ping
                arg_summary = escape(str(args))
                self.logger(
                    f"[bold cyan]Tool Call:[/bold cyan] [bold]{escape(tool_name)}[/bold] with args: {arg_summary}"
                )

            result = await self._dispatch(tool_name, args)

            # Limit result size for context safety
            if isinstance(result, str) and len(result) > 10000:
                result = result[:10000] + "\n\n[RESULTADO TRUNCADO POR SEGURIDAD]"

            if self.logger:
                # Escape result to prevent MarkupError
                result_summary = escape(str(result)[:500])
                self.logger(f"[bold green]Tool Result:[/bold green] {result_summary}...")

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
            if self.config.settings.get("edit_mode", "manual") == "manual":
                console.print(f"\n[warning]{_('tool.action_req')}[/warning] ¿Eliminar archivo [bold]'{path}'[/bold]?")
                if not await asyncio.to_thread(Confirm.ask, _("tool.confirm.edit")):
                    return _("tool.denied.edit")
            return await asyncio.to_thread(delete_file, path)

        if tool_name == "move_file":
            source = args.get("source", "")
            destination = args.get("destination", "")
            if self.config.settings.get("edit_mode", "manual") == "manual":
                console.print(
                    f"\n[warning]{_('tool.action_req')}[/warning] ¿Mover [bold]'{source}'[/bold] a [bold]'{destination}'[/bold]?"
                )
                if not await asyncio.to_thread(Confirm.ask, _("tool.confirm.edit")):
                    return _("tool.denied.edit")
            return await asyncio.to_thread(move_file, source, destination)

        if tool_name == "execute_bash":
            command = args.get("command", "")
            console.print(f"\n[warning]{_('tool.action_req')}[/warning] {_('tool.wants_run')} [bold]'{command}'[/bold]")
            if not await asyncio.to_thread(Confirm.ask, _("tool.confirm.cmd")):
                return _("tool.denied.cmd")
            return await execute_bash(command)

        if tool_name == "edit_file":
            path = args.get("path", "")
            find_text = args.get("find_text", "")
            replace_text = args.get("replace_text", "")

            if self.config.settings.get("edit_mode", "manual") == "manual":
                console.print(
                    f"\n[warning]{_('tool.action_req')}[/warning] {_('tool.wants_edit')} [bold]'{path}'[/bold]"
                )
                console.print(
                    f"[dim]--- Replacing ---[/dim]\n{find_text}\n"
                    f"[dim]--- With ---[/dim]\n{replace_text}\n"
                    f"[dim]-----------------[/dim]"
                )
                if not await asyncio.to_thread(Confirm.ask, _("tool.confirm.edit")):
                    return _("tool.denied.edit")
            else:
                console.print(f"[italic success]{_('tool.edit.auto', path=path)}[/italic success]")

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
