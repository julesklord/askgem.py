import json
import logging
import subprocess
import urllib.request
from typing import Any

from mentask.core.constants import DEFAULT_OLLAMA_TIMEOUT, OLLAMA_DEFAULT_ENDPOINT

from .subprocess_safety import safe_run, validate_url_scheme

_logger = logging.getLogger("mentask")


def _get_wsl_ips() -> list[str]:
    """Attempts to get WSL VM IP addresses (Windows only)."""
    try:
        result = safe_run(
            ["wsl.exe", "--", "hostname", "-I"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            return [ip for ip in result.stdout.strip().split() if ip.count(".") == 3]
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        _logger.debug(f"WSL IP detection failed: {e}")
    return []


def resolve_base_url(config: Any | None = None) -> str:
    """
    Returns the Ollama base URL (without path) to use for API calls and discovery.

    Priority:
      1. Custom ``ollama_endpoint`` from settings (strips trailing ``/v1`` if present)
      2. ``http://localhost:11434``
      3. WSL-detected IP on Windows (fallback if localhost fails later)
    """
    if config:
        custom = config.settings.get("ollama_endpoint")
        if custom:
            base = custom.rstrip("/")
            if base.endswith("/v1"):
                base = base[:-3]
            return base
    return OLLAMA_DEFAULT_ENDPOINT


def fetch_ollama_models(base_url: str, timeout: int = DEFAULT_OLLAMA_TIMEOUT) -> list[str]:
    """Fetch model names from an Ollama ``/api/tags`` endpoint."""
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        validate_url_scheme(url)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            data = json.load(resp)
            return [m["name"] for m in data.get("models", []) if m.get("name")]
    except Exception as e:
        _logger.debug("Failed to fetch Ollama models from %s: %s", url, e, exc_info=True)
        return []
