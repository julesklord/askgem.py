from unittest.mock import patch

import pytest

from askgem.core.paths import get_config_dir, get_history_dir


@pytest.fixture
def mock_env(tmp_path):
    """Sets up a mock environment with a fake HOME and a fake CWD."""
    home_dir = tmp_path / "home"
    project_dir = tmp_path / "project"

    home_dir.mkdir()
    project_dir.mkdir()

    # Mock home and CWD to avoid touching real user files
    with patch("pathlib.Path.home", return_value=home_dir), patch("pathlib.Path.cwd", return_value=project_dir):
        yield {"home": home_dir, "project": project_dir}


def test_workspace_isolation_flow(mock_env):
    """Tests the full transition from global to local workspace."""
    home = mock_env["home"]
    project = mock_env["project"]

    # 1. Initially, it should point to global home
    assert get_config_dir() == home / ".askgem"
    assert get_history_dir() == str(home / ".askgem" / "history")

    # 2. Simulate workspace initialization (creating .askgem in project)
    local_ws = project / ".askgem"
    local_ws.mkdir()

    # 3. Now, get_config_dir should point to the PROJECT directory
    active_config = get_config_dir()
    assert active_config == local_ws
    assert active_config != home / ".askgem"

    # 4. History and other paths should follow the project root
    active_history = get_history_dir()
    assert active_history == str(local_ws / "history")
    assert "project" in active_history.lower()


def test_memory_isolation(mock_env):
    """Verifies that memory files are also isolated by workspace."""
    from askgem.core.paths import get_memory_path

    project = mock_env["project"]

    # Before local WS
    assert ".askgem" in get_memory_path()

    # After local WS
    (project / ".askgem").mkdir()

    # Local knowledge is always in CWD, but config dir paths
    # (like memory.md which is global/personal info) follow the active root if in a workspace?
    # Actually, memory.md is usually global, but if we are in a Workspace,
    # we might want a local override. Our current paths.py redirects ALL config_dir calls.

    assert str(project) in get_memory_path()
    assert str(project) in get_history_dir()
