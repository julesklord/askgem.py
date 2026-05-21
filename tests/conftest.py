import logging
import os
import subprocess
import time

import pytest
import requests

_logger = logging.getLogger("mentask_tests")


def is_ollama_running():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def manage_ollama():
    """
    Ensures Ollama is running during tests that require local models.
    """
    # Check if we should use local models (env var or default)
    use_local = os.getenv("MENTASK_TEST_LOCAL", "true").lower() == "true"
    if not use_local:
        yield
        return

    process = None
    if not is_ollama_running():
        _logger.info("Starting Ollama server...")
        try:
            # Start ollama in background
            process = subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Wait for server to be ready
            for _ in range(10):
                if is_ollama_running():
                    break
                time.sleep(1)
        except FileNotFoundError:
            _logger.warning("Ollama binary not found. Skipping local model management.")

    # Pre-pull the mandated model
    if is_ollama_running():
        _logger.info("Ensuring qwen3.5 is available...")
        try:
            subprocess.run(["ollama", "pull", "qwen3.5"], capture_output=True, check=False)
        except FileNotFoundError:
            _logger.warning("Ollama binary not found in PATH. Cannot pre-pull models.")

    yield

    if process:
        _logger.info("Stopping Ollama server...")
        process.terminate()
        process.wait()

@pytest.fixture
def local_model_name():
    return "ollama:qwen3.5"
