"""
Unit tests for the ContextManager module.
Verifies system instruction building. Summarization logic moved to SessionManager in v0.13.2.
"""

from mentask.agent.core.context import ContextManager


def test_context_manager_build_system_instruction():
    """Verifies that the system instruction contains expected core directives."""
    manager = ContextManager()
    instruction = manager.build_system_instruction()

    assert "mentask" in instruction
    # Check for core agent identity keywords
    assert "autonomous" in instruction.lower() or "agent" in instruction.lower()
    assert "identity" in instruction.lower() or "context" in instruction.lower()
