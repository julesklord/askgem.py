"""Unit tests for ChatAgent.

Uses factory fixtures to eliminate nested MagicMock chains.
Dependencies are injected via ``ChatAgentDependencies`` so the tests
exercise real ``ChatAgent`` logic in full isolation.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mentask.agent.chat import ChatAgent, ChatAgentDependencies


# ---------------------------------------------------------------------------
# Reusable fixture factories
# ---------------------------------------------------------------------------


def make_config(
    model_name: str = "test-model",
    edit_mode: str = "manual",
    theme: str = "indigo",
) -> MagicMock:
    """Return a minimal ConfigManager mock."""
    mock = MagicMock(name="ConfigManager")
    mock.settings = MagicMock()
    mock.settings.get.side_effect = lambda key, default=None: {
        "model_name": model_name,
        "edit_mode": edit_mode,
        "theme": theme,
    }.get(key, default)
    # Default: no API key
    mock.load_api_key.return_value = None
    return mock


def make_context(system_instruction: str = "Mocked system context") -> MagicMock:
    """Return a minimal ContextManager mock."""
    mock = MagicMock(name="ContextManager")
    mock.build_system_instruction.return_value = system_instruction
    return mock


def make_knowledge(identity: str = "Mocked identity") -> MagicMock:
    """Return a minimal KnowledgeManager mock."""
    mock = MagicMock(name="KnowledgeManager")
    mock.read_identity.return_value = identity
    return mock


def make_session() -> MagicMock:
    """Return a minimal SessionManager mock."""
    mock = MagicMock(name="SessionManager")
    mock.metrics = MagicMock()
    mock.setup_api = AsyncMock(return_value=True)
    return mock


def make_deps(**overrides: object) -> ChatAgentDependencies:
    """Build a ``ChatAgentDependencies`` with sensible defaults.

    Pass keyword arguments to override individual components::

        deps = make_deps(config=my_custom_config)
    """
    return ChatAgentDependencies(
        config=overrides.get("config", make_config()),
        history=overrides.get("history", MagicMock(name="HistoryManager")),
        identity=overrides.get("identity", make_knowledge()),
        context=overrides.get("context", make_context()),
        session=overrides.get("session", make_session()),
        tools=overrides.get("tools", MagicMock(name="ToolRegistry")),
    )


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def default_deps() -> ChatAgentDependencies:
    """Pre-built deps with default values — usable in most tests."""
    return make_deps()


@pytest.fixture()
def agent(default_deps: ChatAgentDependencies) -> ChatAgent:
    """ChatAgent wired with default mocked deps."""
    return ChatAgent(dependencies=default_deps)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_agent_initializes_with_injected_deps(default_deps: ChatAgentDependencies) -> None:
    """ChatAgent should expose the exact objects that were injected."""
    a = ChatAgent(dependencies=default_deps)

    assert a.config is default_deps.config
    assert a.history is default_deps.history
    assert a.identity is default_deps.identity
    assert a.context is default_deps.context
    assert a.session is default_deps.session
    assert a.tools is default_deps.tools


async def test_agent_reads_model_name_from_config(agent: ChatAgent) -> None:
    """Agent should expose model_name sourced from its config."""
    assert agent.model_name == "test-model"


async def test_agent_reads_edit_mode_from_config(agent: ChatAgent) -> None:
    """Agent should expose edit_mode sourced from its config."""
    assert agent.edit_mode == "manual"


async def test_agent_starts_with_empty_message_history(agent: ChatAgent) -> None:
    """A fresh agent should have no messages in its in-memory history."""
    assert len(agent.messages) == 0


async def test_setup_api_returns_false_when_no_key_and_non_interactive(
    default_deps: ChatAgentDependencies,
) -> None:
    """setup_api(interactive=False) should return False when session reports no key."""
    # setup_api is a pure proxy to session.setup_api, so we mock the session
    default_deps.session.setup_api = AsyncMock(return_value=False)
    a = ChatAgent(dependencies=default_deps)
    result = await a.setup_api(interactive=False)
    assert result is False
    default_deps.session.setup_api.assert_awaited_once_with(False)


async def test_setup_api_returns_true_when_key_provided(
    default_deps: ChatAgentDependencies,
) -> None:
    """setup_api should succeed when session reports a valid API key."""
    # setup_api is a pure proxy to session.setup_api
    default_deps.session.setup_api = AsyncMock(return_value=True)
    a = ChatAgent(dependencies=default_deps)
    result = await a.setup_api(interactive=True)
    assert result is True
    default_deps.session.setup_api.assert_awaited_once_with(True)


async def test_custom_model_name_propagates(default_deps: ChatAgentDependencies) -> None:
    """Verify that overriding the model in config is reflected in the agent."""
    custom_config = make_config(model_name="gemini-2.5-pro")
    deps = make_deps(config=custom_config)
    a = ChatAgent(dependencies=deps)
    assert a.model_name == "gemini-2.5-pro"
