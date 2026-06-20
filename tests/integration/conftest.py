"""Conftest for integration tests.

Automatically applies the ``integration`` marker to every test collected from
this directory so they are skipped during regular unit test runs.
"""

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Add the ``integration`` marker to all tests under this directory."""
    integration_dir = __file__.replace("conftest.py", "")
    for item in items:
        if str(item.fspath).startswith(integration_dir):
            item.add_marker(pytest.mark.integration)
