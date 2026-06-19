from unittest.mock import patch

import pytest

from mentask.agent.tools.user_tool import AskUserTool


@pytest.mark.asyncio
async def test_ask_user_non_tty():
    tool = AskUserTool()
    with patch("sys.stdin.isatty", return_value=False):
        res = await tool.execute("What is your favorite color?")
        assert res.is_error
        assert "Cannot prompt user for input because stdin is not a TTY" in res.content


@pytest.mark.asyncio
async def test_ask_user_tty_success():
    tool = AskUserTool()
    with patch("sys.stdin.isatty", return_value=True), \
         patch("rich.prompt.Prompt.ask", return_value="Blue"):
        res = await tool.execute("What is your favorite color?")
        assert not res.is_error
        assert res.content == "Blue"


@pytest.mark.asyncio
async def test_ask_user_tty_exception():
    tool = AskUserTool()
    with patch("sys.stdin.isatty", return_value=True), \
         patch("rich.prompt.Prompt.ask", side_effect=ValueError("Invalid input")):
        res = await tool.execute("What is your favorite color?")
        assert res.is_error
        assert "Error gathering user input: Invalid input" in res.content
