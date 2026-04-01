import sys
import os
import platform
from typing import List, Dict, Any

from google import genai
from google.genai import types
from rich.live import Live
from rich.markdown import Markdown
from rich.prompt import Confirm

from ..ui.console import console
from ..core.config_manager import ConfigManager
from ..tools.system_tools import list_directory, execute_bash
from ..tools.file_tools import read_file, edit_file

class QueryEngine:
    def __init__(self):
        self.running = False
        self.config = ConfigManager(console)
        self.client = None
        self.chat_session = None
        
        # Load settings from config
        self.model_name = self.config.settings.get("model_name", "gemini-2.5-pro")
        self.edit_mode = self.config.settings.get("edit_mode", "manual")
        
        # Autonomous Tools enabled by default
        self._tools = [list_directory, execute_bash, read_file, edit_file]
        
    def setup_api(self) -> bool:
        """Configures and validates the Google API Token natively using the new SDK."""
        api_key = self.config.load_api_key()
        
        if not api_key:
            console.print("\n[bold red]No valid API Key found.[/bold red]")
            api_key = console.input("[bold cyan]Please enter your Google API Key:[/bold cyan] ").strip()
            
            if not api_key:
                console.print("[red][X] The API Key is required to continue. Shutting down.[/red]")
                return False
                
            guardar = console.input("Would you like to save it locally for future uses? (Y/n): ").strip().lower()
            if guardar != 'n':
                self.config.save_api_key(api_key)
                
        # Initialize Google GenAI client instance
        self.client = genai.Client(api_key=api_key)
        return True

    def _build_config(self) -> types.GenerateContentConfig:
        """Dynamically assembles the configuration and OS context."""
        sys_context = (
            f"You are PyGemAi, an advanced autonomous AI agentic developer in the CLI. "
            f"You are currently running on: {platform.system()} {platform.release()}. "
            f"The absolute path of the current working directory is: {os.getcwd()}. "
            f"Use your tools to read the file structures, gather information, and edit appropriately. "
            f"When editing files, you must use read_file first to know the exact characters spacing for the 'find_text' argument."
        )
        
        return types.GenerateContentConfig(
            temperature=0.7,
            tools=self._tools,
            system_instruction=sys_context
        )

    def _execute_tool(self, function_call: types.FunctionCall) -> types.Part:
        """Executes the function requested by the LLM system locally on the machine, and forwards the results."""
        tool_name = function_call.name
        args = function_call.args if function_call.args else {}
        
        console.print(f"[dim italic]⚙ Running autonomous tool: {tool_name}[/dim italic]")
        
        result = None
        
        if tool_name == "list_directory":
            path = args.get("path", ".")  # Fallback to arguments the API might generate
            if "ruta" in args: path = args["ruta"]
            result = list_directory(path)
            
        elif tool_name == "execute_bash":
            command = args.get("command", "")
            if "comando" in args: command = args["comando"]
            # Critical OS tools require human explicit validation to prevent destructive routines
            console.print(f"\n[bold yellow]⚠️ Action Required:[/bold yellow] The model wants to execute the following terminal command: [bold]'{command}'[/bold]")
            if Confirm.ask("Do you allow this code execution?"):
                result = execute_bash(command)
            else:
                result = "System Notice: The human user explicitly denied the permission to execute this command."
                
        elif tool_name == "read_file":
            path = args.get("path", "")
            start_line = args.get("start_line", None)
            end_line = args.get("end_line", None)
            result = read_file(path, start_line, end_line)
            
        elif tool_name == "edit_file":
            path = args.get("path", "")
            find_text = args.get("find_text", "")
            replace_text = args.get("replace_text", "")
            
            if self.edit_mode == "manual":
                console.print(f"\n[bold yellow]⚠️ Action Required:[/bold yellow] The model wants to MODIFY the file: [bold]'{path}'[/bold]")
                console.print(f"[dim]--- Replacing Block ---[/dim]\n{find_text}\n[dim]--- With Block ---[/dim]\n{replace_text}\n[dim]-----------------------[/dim]")
                if Confirm.ask("Do you allow this file modification?"):
                    result = edit_file(path, find_text, replace_text)
                else:
                    result = "System Notice: The human user explicitly denied the permission to edit this file."
            else:
                console.print(f"[italic green]=> Auto-approving file edit for '{path}'...[/italic green]")
                result = edit_file(path, find_text, replace_text)
                
        else:
            result = f"Error: Tool '{tool_name}' is not registered or implemented in the local client context."
            
        # Format the system response matching OpenAPI schema bounds to bounce it back
        return types.Part.from_function_response(
            name=tool_name,
            response={"result": result}
        )

    def _stream_response(self, user_input: str | types.Part):
        """Dispatches the prompt to the model, intercepts automatic function calling loops, and handles progressive UI markdown chunking."""
        try:
            # Deliver the user prompt directly (or the returned payload from an autonomous Tool iteration)
            response_stream = self.chat_session.send_message_stream(user_input)
            
            full_text = ""
            function_calls_received: List[types.FunctionCall] = []
            
            with Live(Markdown(""), console=console, refresh_per_second=15) as live:
                for chunk in response_stream:
                    # Capture actual conversational payload directed to the human user
                    if chunk.text:
                        full_text += chunk.text
                        live.update(Markdown(full_text))
                    
                    # Intercept underlying system routines (function calls) to perform agentic loops
                    if chunk.function_calls:
                        function_calls_received.extend(chunk.function_calls)
            
            console.print("") 
            
            # If the model intended to use tools, we iterate over them recursively underneath the UI
            if function_calls_received:
                function_responses = []
                for fn_call in function_calls_received:
                    part_response = self._execute_tool(fn_call)
                    function_responses.append(part_response)
                
                # Feedback loop: Bounce the system responses back implicitly
                if function_responses:
                    self._stream_response(function_responses)
            
        except Exception as e:
            console.print(f"\n[bold red][X] Fatal API Connection Error:[/bold red] {e}")

    def _process_slash_command(self, user_input: str):
        """Parses and acts on mid-conversation chat commands."""
        parts = user_input.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if command == "/model":
            if not args:
                console.print(f"[bold yellow]Current active model: {self.model_name}[/bold yellow]")
                try:
                    console.print("[dim]Fetching available generation models from your API Key...[/dim]")
                    available = []
                    for model_obj in self.client.models.list():
                        if "generateContent" in model_obj.supported_actions:
                            clean_name = model_obj.name.replace("models/", "")
                            if "gemini" in clean_name.lower():
                                available.append(clean_name)
                                
                    if available:
                        console.print("\n[bold]Available Gemini models:[/bold]")
                        for m in sorted(available):
                            console.print(f"  • [cyan]{m}[/cyan]")
                except Exception as e:
                    console.print(f"[dim](Could not retrieve dynamic model list from Google API: {e})[/dim]")
                    
                console.print("\n[dim]Usage: /model <model_name> (e.g., /model gemini-2.5-flash)[/dim]")
                return
            new_model = args[0]
            self.model_name = new_model
            self.config.settings["model_name"] = new_model
            self.config.save_settings()
            
            # Recreate session mapping existing history if available
            current_history = None
            if self.chat_session:
                try: 
                    # General extraction (if properties exist in the object map)
                    current_history = getattr(self.chat_session, "history", None)
                    if not current_history and hasattr(self.chat_session, "get_history"):
                        current_history = self.chat_session.get_history()
                except Exception:
                    current_history = None
            
            try:
                # Reboot chat with the newly stored config and maintain context
                self.chat_session = self.client.chats.create(
                    model=self.model_name,
                    config=self._build_config(),
                    history=current_history
                )
                console.print(f"[bold green]Switched context seamlessly to:[/bold green] {self.model_name}")
            except Exception as e:
                console.print(f"[bold red]Failed to switch model:[/bold red] {e}")
                
        elif command == "/mode":
            if not args or args[0].lower() not in ["auto", "manual"]:
                console.print(f"[bold yellow]Current edit mode: {self.edit_mode}[/bold yellow]")
                console.print("[dim]Usage: /mode auto  --- OR ---  /mode manual[/dim]")
                return
            new_mode = args[0].lower()
            self.edit_mode = new_mode
            self.config.settings["edit_mode"] = new_mode
            self.config.save_settings()
            console.print(f"[bold green]File edit confirmation mode set to:[/bold green] {self.edit_mode}")
            
        else:
            console.print(f"[yellow]Unknown command:[/yellow] {command}")


    def start(self):
        """CLI main execution and lifecycle loop."""
        if not self.setup_api():
            sys.exit(1)
            
        self.running = True
        
        try:
            self.chat_session = self.client.chats.create(
                model=self.model_name,
                config=self._build_config()
            )
        except Exception as e:
            console.print(f"[bold red][X] Critical failure binding the {self.model_name} model:[/bold red] {e}")
            sys.exit(1)
            
        console.print(f"[dim]LLM Main Engine successfully bound natively to [bold]{self.model_name}[/bold].[/dim]")
        
        # Draw dynamic capabilities notice matching the config
        t_names = ", ".join([t.__name__ for t in self._tools])
        console.print(f"[dim]Modules activated: {t_names}[/dim]")
        console.print(f"[dim]Edit Mode: {self.edit_mode}  | Use commands /model or /mode to change settings mid-chat.[/dim]")
        
        while self.running:
            try:
                user_input = console.input("\n[bold green]You:[/bold green] ").strip()
                if not user_input:
                    continue
                    
                if user_input.lower() in ["exit", "quit", "q"]:
                    self.running = False
                    break
                
                # Trap slash configurations
                if user_input.startswith("/"):
                    self._process_slash_command(user_input)
                    continue
                
                console.print(f"[bold blue]{self.model_name}:[/bold blue]")
                self._stream_response(user_input)
                
            except (KeyboardInterrupt, EOFError):
                self.running = False
                break
        
        console.print("\n[bold yellow]Shutting down. Farewell![/bold yellow]")
