import pytest
from unittest.mock import MagicMock
from rich.console import Console
from mentask.cli.gem_renderer import GemStyleRenderer

@pytest.fixture
def console():
    return Console(force_terminal=True, width=80)

def test_renderer_initialization(console):
    renderer = GemStyleRenderer(console)
    # Check if theme is correctly initialized
    assert renderer.theme is not None
    assert renderer.live_text == ""

def test_renderer_stream_logic(console):
    renderer = GemStyleRenderer(console)
    renderer.start_stream(is_natural=True)
    renderer.update_stream("Hello ")
    renderer.update_stream("Hello world!") # Active renderer expects accumulated text
    # Internal state check
    assert "Hello world!" in renderer.live_text

def test_renderer_tool_call(console):
    renderer = GemStyleRenderer(console)
    # This should not crash
    renderer.print_tool_call("test_tool", {"arg": 1})

def test_renderer_artifact_expansion(console):
    renderer = GemStyleRenderer(console)
    renderer.print_tool_result(True, "Result content", tool_name="test")
    assert len(renderer.artifacts) == 1
    # Expand it
    renderer.expand_artifact(0)
