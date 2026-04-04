import os
from unittest.mock import patch

import pytest

from askgem.core.identity_manager import DEFAULT_IDENTITY_TEMPLATE, IdentityManager


@pytest.fixture
def mock_identity_path(tmp_path):
    identity_file = str(tmp_path / "identity.md")
    with patch("askgem.core.identity_manager.get_config_path") as mock_path:
        mock_path.return_value = identity_file
        yield identity_file


def test_init_creates_identity(mock_identity_path):
    assert not os.path.exists(mock_identity_path)

    IdentityManager()

    assert os.path.exists(mock_identity_path)
    with open(mock_identity_path, encoding="utf-8") as f:
        content = f.read()

    assert content == DEFAULT_IDENTITY_TEMPLATE


def test_init_does_not_overwrite_existing_identity(mock_identity_path):
    test_content = "Existing identity content"
    with open(mock_identity_path, "w", encoding="utf-8") as f:
        f.write(test_content)

    IdentityManager()

    with open(mock_identity_path, encoding="utf-8") as f:
        content = f.read()

    assert content == test_content


def test_read_identity(mock_identity_path):
    manager = IdentityManager()

    test_content = "Some identity content"
    with open(mock_identity_path, "w", encoding="utf-8") as f:
        f.write(test_content)

    result = manager.read_identity()
    assert result == test_content


def test_read_identity_handles_error(mock_identity_path):
    manager = IdentityManager()

    # To trigger the exception in read_identity, we can patch open
    original_open = open

    def mock_open(*args, **kwargs):
        if len(args) > 1 and args[1] == "r":
            raise OSError("Mocked error")
        return original_open(*args, **kwargs)

    with patch("builtins.open", side_effect=mock_open):
        result = manager.read_identity()

    assert result == "Error al leer la identidad."


def test_update_identity(mock_identity_path):
    manager = IdentityManager()

    new_content = "New identity content"
    success = manager.update_identity(new_content)

    assert success is True

    with open(mock_identity_path, encoding="utf-8") as f:
        content = f.read()

    assert content == new_content


def test_update_identity_handles_error(mock_identity_path):
    manager = IdentityManager()

    # To trigger the exception in update_identity, we can patch open
    original_open = open

    def mock_open(*args, **kwargs):
        if len(args) > 1 and args[1] == "w":
            raise OSError("Mocked error")
        return original_open(*args, **kwargs)

    with patch("builtins.open", side_effect=mock_open):
        success = manager.update_identity("Some content")

    assert success is False
