import sys
from typing import List, Dict, Any
from google import genai
from google.genai import types
from rich.live import Live
from rich.markdown import Markdown
from rich.prompt import Confirm

from ..ui.console import console
from ..core.config_manager import ConfigManager
from ..tools.system_tools import list_directory, execute_bash

class QueryEngine:
    def __init__(self):
        self.running = False
        self.config = ConfigManager(console)
        self.client = None
        self.chat_session = None
        self.model_name = "gemini-2.5-pro"
        # Autonomous Tools enabled by default
        self._tools = [list_directory, execute_bash]
        
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

    def _execute_tool(self, function_call: types.FunctionCall) -> types.Part:
        """Executes the function requested by the LLM system locally on the machine, and forwards the results."""
        tool_name = function_call.name
        args = function_call.args if function_call.args else {}
        
        console.print(f"[dim italic]⚙ Running autonomous tool: {tool_name}({args})[/dim italic]")
        
        result = None
        # Resolving function mapping manually
        if tool_name == "list_directory":
            # Safe automatic execution
            path = args.get("ruta", ".")
            result = list_directory(path)
        elif tool_name == "execute_bash":
            command = args.get("comando", "")
            # Critical OS tools require human explicit validation to prevent destructive routines
            console.print(f"\n[bold yellow]⚠️ Action Required:[/bold yellow] The model wants to execute the following terminal command: [bold]'{command}'[/bold]")
            if Confirm.ask("Do you allow this code execution?"):
                result = execute_bash(command)
            else:
                result = "System Notice: The human user explicitly denied the permission to execute this command."
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
                # The LLM will assess the new data and formulate the final conversational response that the user awaits.
                if function_responses:
                    self._stream_response(function_responses)
            
        except Exception as e:
            console.print(f"\n[bold red][X] Fatal API Connection Error:[/bold red] {e}")

    def start(self):
        """CLI main execution and lifecycle loop."""
        if not self.setup_api():
            sys.exit(1)
            
        self.running = True
        
        try:
            # Config bootstrap using the latest beta SDK capabilities
            config = types.GenerateContentConfig(
                temperature=0.7,
                tools=self._tools,
            )
            self.chat_session = self.client.chats.create(
                model=self.model_name,
                config=config
            )
        except Exception as e:
            console.print(f"[bold red][X] Critical failure binding the {self.model_name} model:[/bold red] {e}")
            sys.exit(1)
            
        console.print(f"[dim]LLM Main Engine successfully bound natively to [bold]{self.model_name}[/bold].[/dim]")
        console.print("[dim]Modules activated: list_directory, execute_bash[/dim]")
        
        while self.running:
            try:
                user_input = console.input("\n[bold green]You:[/bold green] ").strip()
                if user_input.lower() in ["exit", "quit", "q"]:
                    self.running = False
                    break
                if not user_input:
                    continue
                
                console.print(f"[bold blue]{self.model_name}:[/bold blue]")
                self._stream_response(user_input)
                
            except (KeyboardInterrupt, EOFError):
                self.running = False
                break
        
        console.print("\n[bold yellow]Shutting down. Farewell![/bold yellow]")
