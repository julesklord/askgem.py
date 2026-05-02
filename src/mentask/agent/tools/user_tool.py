import logging

from pydantic import BaseModel, Field
from rich.prompt import Prompt

from ...cli.console import console
from ..schema import ToolResult
from .base import BaseTool

_logger = logging.getLogger("mentask")


class AskUserInput(BaseModel):
    question: str = Field(..., description="The question to ask the user to clarify ambiguity or gather preferences.")


class AskUserTool(BaseTool):
    """
    Tool that allows the agent to ask the user a question and wait for a response.
    This is essential for clarifying ambiguous requirements or making decisions.
    """

    name = "ask_user"
    description = "Asks the user a question to gather information, clarify ambiguity, or offer choices. Use this when you are unsure how to proceed."
    input_schema = AskUserInput

    async def execute(self, question: str) -> ToolResult:
        console.print(f"\n[bold yellow]❓ AGENT QUESTION:[/bold yellow] {question}")

        try:
            # Note: In a real async environment, blocking here might be an issue,
            # but for mentask's current CLI loop, it's the intended behavior.
            # Using Electric Indigo (#6366F1) for brand consistency
            response = Prompt.ask("[bold #6366F1]Your Answer[/bold #6366F1]")
            return ToolResult(tool_call_id="", content=response, is_error=False)
        except Exception as e:
            return ToolResult(tool_call_id="", content=f"Error gathering user input: {str(e)}", is_error=True)
