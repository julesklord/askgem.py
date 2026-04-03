"""
Central tool registry and dispatcher for the AskGem agent.

Decouples the tool execution logic from the main conversational loop.
"""

import functools
from typing import Callable, List, Optional

from google.genai import types
from rich.markup import escape
from rich.prompt import Confirm
from rich.status import Status

from ..cli.console import console
from ..core.i18n import _
from ..tools.file_tools import diff_file, edit_file, read_file
from ..tools.search_tools import glob_find, grep_search
from ..tools.system_tools import execute_bash, list_directory
from ..tools.memory_tools import manage_memory, manage_mission
from ..tools.web_tools import web_fetch, web_search


class ToolDispatcher:
    """Handles tool registration and execution routing for the ChatAgent."""

    def __init__(
        self,
        edit_mode: str = "manual",
        search_api_key: str = "",
        search_cx_id: str = "",
        logger: Optional[Callable[[str], None]] = None,
    ):
        """Initializes the dispatcher with a logger and credentials."""
        self.edit_mode = edit_mode
        self.logger = logger
        self.modified_files_count = 0

        # Pre-bind keys to the web_search tool
        bound_web_search = functools.partial(web_search, api_key=search_api_key, cx_id=search_cx_id)
        # Preserve original docstring for the LLM
        bound_web_search.__doc__ = web_search.__doc__

        self._tools = [
            list_directory,
            execute_bash,
            read_file,
            edit_file,
            diff_file,
            grep_search,
            glob_find,
            bound_web_search,
            web_fetch,
            manage_memory,
            manage_mission,
        ]

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
                self.logger(f"[bold cyan]Tool Call:[/bold cyan] [bold]{escape(tool_name)}[/bold] with args: {arg_summary}")

            result = await self._dispatch(tool_name, args)

            if self.logger:
                # Escape result to prevent MarkupError
                result_summary = escape(str(result)[:500])
                self.logger(f"[bold green]Tool Result:[/bold green] {result_summary}...")

        return types.Part.from_function_response(
            name=tool_name,
            response={"result": result},
        )

    async def _dispatch(self, tool_name: str, args: dict) -> str:
        """Internal async dispatch logic for registered tools."""

        # 1. System/Filesystem Tools
        if tool_name == "list_directory":
            return list_directory(args.get("path", "."))

        elif tool_name == "execute_bash":
            command = args.get("command", "")
            console.print(f"\n[warning]{_('tool.action_req')}[/warning] {_('tool.wants_run')} [bold]'{command}'[/bold]")
            if Confirm.ask(_("tool.confirm.cmd")):
                return execute_bash(command)
            return _("tool.denied.cmd")

        # 2. CRUD File Tools
        elif tool_name == "read_file":
            return read_file(
                args.get("path", ""),
                args.get("start_line"),
                args.get("end_line"),
            )

        elif tool_name == "edit_file":
            path = args.get("path", "")
            find_text = args.get("find_text", "")
            replace_text = args.get("replace_text", "")

            if self.edit_mode == "manual":
                console.print(
                    f"\n[warning]{_('tool.action_req')}[/warning] {_('tool.wants_edit')} [bold]'{path}'[/bold]"
                )
                console.print(
                    f"[dim]--- Replacing ---[/dim]\n{find_text}\n"
                    f"[dim]--- With ---[/dim]\n{replace_text}\n"
                    f"[dim]-----------------[/dim]"
                )
                if Confirm.ask(_("tool.confirm.edit")):
                    res = edit_file(path, find_text, replace_text)
                    if res.startswith("Success:"):
                        self.modified_files_count += 1
                    return res
                return _("tool.denied.edit")

            console.print(f"[italic success]{_('tool.edit.auto', path=path)}[/italic success]")
            res = edit_file(path, find_text, replace_text)
            if res.startswith("Success:"):
                self.modified_files_count += 1
            return res

        elif tool_name == "diff_file":
            return diff_file(
                args.get("path", ""),
                args.get("find_text", ""),
                args.get("replace_text", ""),
            )

        # 3. Advanced Search Tools (Milestone 2)
        elif tool_name == "grep_search":
            return grep_search(
                args.get("pattern", ""),
                args.get("path", "."),
                args.get("is_regex", False),
                args.get("case_sensitive", False),
            )

        elif tool_name == "glob_find":
            return glob_find(args.get("pattern", ""), args.get("path", "."))

        elif tool_name == "manage_memory":
            return manage_memory(
                args.get("action", "read"),
                args.get("content", ""),
                args.get("category", "Lessons Learned & Facts"),
            )

        elif tool_name == "manage_mission":
            return manage_mission(
                args.get("action", "read"),
                args.get("task", ""),
            )

        return _("tool.unregistered", name=tool_name)
