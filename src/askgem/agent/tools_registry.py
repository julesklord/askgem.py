"""
Central tool registry and dispatcher for the AskGem agent.

Decouples the tool execution logic from the main conversational loop.
"""

from typing import List

from google.genai import types
from rich.prompt import Confirm
from rich.status import Status

from ..cli.console import console
from ..core.i18n import _
from ..tools.file_tools import diff_file, edit_file, read_file
from ..tools.search_tools import glob_find, grep_search
from ..tools.system_tools import execute_bash, list_directory


class ToolDispatcher:
    """Handles tool registration and execution routing for the ChatAgent."""

    def __init__(self, edit_mode: str = "manual"):
        """Initializes the dispatcher with a specific edit mode."""
        self.edit_mode = edit_mode
        self._tools = [
            list_directory,
            execute_bash,
            read_file,
            edit_file,
            diff_file,
            grep_search,
            glob_find
        ]

    def get_tools_list(self) -> List:
        """Returns the list of registered tool functions for the Gemini SDK."""
        return self._tools

    def execute(self, function_call: types.FunctionCall) -> types.Part:
        """Routes and executes a model-requested function call.

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
            result = self._dispatch(tool_name, args)

        return types.Part.from_function_response(
            name=tool_name,
            response={"result": result},
        )

    def _dispatch(self, tool_name: str, args: dict) -> str:
        """Internal dispatch logic for registered tools."""

        # 1. System/Filesystem Tools
        if tool_name == "list_directory":
            return list_directory(args.get("path", "."))

        elif tool_name == "execute_bash":
            command = args.get("command", "")
            console.print(
                f"\n[warning]{_('tool.action_req')}[/warning] "
                f"{_('tool.wants_run')} [bold]'{command}'[/bold]"
            )
            if Confirm.ask(_('tool.confirm.cmd')):
                return execute_bash(command)
            return _('tool.denied.cmd')

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
                    f"\n[warning]{_('tool.action_req')}[/warning] "
                    f"{_('tool.wants_edit')} [bold]'{path}'[/bold]"
                )
                console.print(
                    f"[dim]--- Replacing ---[/dim]\n{find_text}\n"
                    f"[dim]--- With ---[/dim]\n{replace_text}\n"
                    f"[dim]-----------------[/dim]"
                )
                if Confirm.ask(_('tool.confirm.edit')):
                    return edit_file(path, find_text, replace_text)
                return _('tool.denied.edit')

            console.print(f"[italic success]{_('tool.edit.auto', path=path)}[/italic success]")
            return edit_file(path, find_text, replace_text)

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
                args.get("case_sensitive", False)
            )

        elif tool_name == "glob_find":
            return glob_find(
                args.get("pattern", ""),
                args.get("path", ".")
            )

        return _('tool.unregistered', name=tool_name)
