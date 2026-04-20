import os
from pathlib import Path
from unittest.mock import patch

import pytest

from askgem.core.trust_manager import TrustManager


@pytest.fixture
def mock_global_config(tmp_path):
    """Mocks the global config directory to use a temp path."""
    with patch("askgem.core.trust_manager.get_global_config_dir", return_value=tmp_path):
        yield tmp_path


def test_trust_manager_init(mock_global_config):
    """Verifies that the manager starts empty and creates no file initially."""
    tm = TrustManager()
    assert len(tm.trusted_paths) == 0
    assert not (mock_global_config / "trusted.json").exists()


def test_add_trust(mock_global_config):
    """Verifies adding a path to the trusted list."""
    tm = TrustManager()
    path = str(Path("/tmp/my_project").absolute())
    tm.add_trust(path)

    assert tm.is_trusted(path)
    assert (mock_global_config / "trusted.json").exists()


def test_trust_persistence(mock_global_config):
    """Verifies that trust is saved and loaded correctly across instances."""
    tm1 = TrustManager()
    path = str(Path("/tmp/persistent_project").absolute())
    tm1.add_trust(path)

    # New instance should load the same data
    tm2 = TrustManager()
    assert tm2.is_trusted(path)


def test_is_trusted_recursive(mock_global_config):
    """Verifies that subdirectories of a trusted path are also trusted."""
    tm = TrustManager()
    base_path = str(Path("/work").absolute())
    tm.add_trust(base_path)

    # Direct match
    assert tm.is_trusted(base_path)
    # Subdirectory match
    assert tm.is_trusted(os.path.join(base_path, "sub", "dir"))
    # Unrelated path
    assert not tm.is_trusted(str(Path("/other").absolute()))


def test_remove_trust(mock_global_config):
    """Verifies removing a path from the trusted list."""
    tm = TrustManager()
    path = str(Path("/to_remove").absolute())
    tm.add_trust(path)
    assert tm.is_trusted(path)

    tm.remove_trust(path)
    assert not tm.is_trusted(path)
