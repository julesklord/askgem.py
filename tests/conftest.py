import logging
import os
import subprocess
import time

import pytest
import requests

_logger = logging.getLogger("mentask_tests")


def is_ollama_running() -> bool:
    """Check if Ollama server is reachable at the default address."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def manage_ollama():
    """Ensures Ollama is running during integration tests that require local models.

    This fixture must be requested explicitly by integration tests; it will NOT
    auto-start Ollama for regular unit tests.

    Usage::

        @pytest.mark.integration
        def test_something(manage_ollama):
            ...
    """
    process = None
    if not is_ollama_running():
        _logger.info("Starting Ollama server for integration tests...")
        try:
            process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(15):
                if is_ollama_running():
                    _logger.info("Ollama server is ready.")
                    break
                time.sleep(1)
            else:
                _logger.warning("Ollama server did not start in time.")
        except FileNotFoundError:
            pytest.skip("Ollama binary not found — skipping integration test.")

    if not is_ollama_running():
        pytest.skip("Ollama is not running — skipping integration test.")

    # Pre-pull the model used in integration tests
    _logger.info("Ensuring qwen3.5 model is available...")
    try:
        subprocess.run(
            ["ollama", "pull", "qwen3.5"],
            capture_output=True,
            check=False,
            timeout=300,
        )
    except FileNotFoundError:
        _logger.warning("Ollama binary not found. Cannot pre-pull models.")
    except subprocess.TimeoutExpired:
        _logger.warning("Model pull timed out.")

    yield

    if process:
        _logger.info("Stopping Ollama server...")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture
def local_model_name() -> str:
    """Returns the local model name used in integration tests."""
    return os.getenv("MENTASK_TEST_MODEL", "ollama:qwen3.5")
