"""
core/model_discovery.py — Dynamic model discovery per provider source.

Discovers models from:
  - External CLI binaries (gemini-cli, codex, claude, opencode, aider)
  - Local Ollama instance
  - Cloud APIs (via Google AI REST API for Gemini, curated fallbacks for others)

Usage in /model command:
  /model gemini-cli:gemini-2.5-pro
  /model codex:gpt-4.1
  /model ollama:qwen3
  /model gemini-2.5-pro        (direct API)
  /model openai:gpt-4o         (scoped API)
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
import urllib.request
from typing import Any

from mentask.core.constants import DEFAULT_MODEL_DISCOVERY_TIMEOUT, MODEL_DISCOVERY_CACHE_TTL

from .subprocess_safety import validate_url_scheme

_logger = logging.getLogger("mentask.core.model_discovery")


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────


def _resolve_binary(aliases: list[str]) -> str | None:
    """Returns the full path to the first found binary alias, or None."""
    for alias in aliases:
        path = shutil.which(alias)
        if path:
            return path
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Curated fallback model lists (used when CLI/API listing is unavailable)
# ─────────────────────────────────────────────────────────────────────────────

_GEMINI_FALLBACK_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

_CLAUDE_FALLBACK_MODELS = [
    "claude-opus-4-5",
    "claude-sonnet-4-5",
    "claude-haiku-4-5",
    "claude-3-7-sonnet-latest",
    "claude-3-5-haiku-latest",
]

_CODEX_FALLBACK_MODELS = [
    "gpt-4.1",
    "gpt-4.1-mini",
    "o4-mini",
    "o3",
]


# ─────────────────────────────────────────────────────────────────────────────
# Per-CLI model fetchers
# ─────────────────────────────────────────────────────────────────────────────


def _fetch_gemini_api_models() -> list[str]:
    """
    Fetches available Gemini models from the Google AI REST API.
    Falls back to the curated list if no API key is available.
    """
    import os

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        # Try reading from mentask local settings
        try:
            from pathlib import Path

            settings_path = Path.cwd() / ".mentask" / "settings.json"
            if settings_path.exists():
                with open(settings_path, encoding="utf-8") as f:
                    data = json.load(f)
                    api_key = data.get("google_api_key") or data.get("gemini_api_key", "")
        except (OSError, json.JSONDecodeError):  # nosec B110
            pass

    if not api_key:
        return _GEMINI_FALLBACK_MODELS

    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=100"
        validate_url_scheme(url)
        req = urllib.request.Request(url, headers={"X-Goog-Api-Key": api_key, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=DEFAULT_MODEL_DISCOVERY_TIMEOUT) as resp:  # nosec B310
            data = json.load(resp)
            models = []
            for m in data.get("models", []):
                name = m.get("name", "")
                # Only models that support content generation
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    # name format: 'models/gemini-2.5-pro' → extract ID
                    model_id = name.split("/")[-1] if "/" in name else name
                    models.append(model_id)
            return models if models else _GEMINI_FALLBACK_MODELS
    except Exception as e:
        _logger.debug(f"model_discovery: Gemini API fetch failed: {e}")
        return _GEMINI_FALLBACK_MODELS


def _parse_opencode_models(stdout: str) -> list[str]:
    """Parse `opencode models` output."""
    return [line.strip() for line in stdout.splitlines() if line.strip() and not line.startswith("#")]


def _parse_aider_models(stdout: str) -> list[str]:
    """Parse `aider --list-models` output (lines with '/' in them are model IDs)."""
    return [line.strip() for line in stdout.splitlines() if line.strip() and "/" in line]


# ─────────────────────────────────────────────────────────────────────────────
# CLI Descriptor Table
# ─────────────────────────────────────────────────────────────────────────────
# Each entry defines how to discover models and pass a model name to the binary.
#
# Keys:
#   aliases      - binary names to try (in order)
#   list_args    - argv to list models (None = use fetch_models instead)
#   parse        - callable(stdout) -> list[str]  (used when list_args is set)
#   fetch_models - callable() -> list[str]        (used when list_args is None)
#   model_flag   - CLI flag to select a specific model (e.g. '--model')
#   display      - human-readable name

_CLI_DESCRIPTORS: dict[str, dict[str, Any]] = {
    "gemini-cli": {
        "aliases": ["gemini-cli", "gemini"],
        # gemini-cli has no stable --list-models; use Google AI API instead
        "list_args": None,
        "fetch_models": _fetch_gemini_api_models,
        "model_flag": "--model",
        "display": "Gemini CLI",
    },
    "claude": {
        "aliases": ["claude"],
        # claude CLI has no stable --list-models flag
        "list_args": None,
        "fetch_models": lambda: _CLAUDE_FALLBACK_MODELS,
        "model_flag": "--model",
        "display": "Claude CLI",
    },
    "codex": {
        "aliases": ["codex"],
        # codex CLI has no --list-models in current stable
        "list_args": None,
        "fetch_models": lambda: _CODEX_FALLBACK_MODELS,
        "model_flag": "--model",
        "display": "Codex CLI",
    },
    "opencode": {
        "aliases": ["opencode"],
        "list_args": ["models"],
        "parse": _parse_opencode_models,
        "fetch_models": None,
        "model_flag": "--model",
        "display": "OpenCode CLI",
    },
    "aider": {
        "aliases": ["aider"],
        "list_args": ["--list-models", "gpt"],  # aider needs a filter arg
        "parse": _parse_aider_models,
        "fetch_models": None,
        "model_flag": "--model",
        "display": "Aider",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Discovery cache
# ─────────────────────────────────────────────────────────────────────────────

_DISCOVERY_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_TTL = MODEL_DISCOVERY_CACHE_TTL  # 5 minutes


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def discover_cli_models(cli_key: str, force: bool = False) -> list[str]:
    """
    Returns a list of model IDs available from a specific CLI binary.
    Uses fetch_models() for CLIs without a --list-models flag.
    Results are cached for _CACHE_TTL seconds.
    """
    desc = _CLI_DESCRIPTORS.get(cli_key)
    if not desc:
        return []

    cached = _DISCOVERY_CACHE.get(cli_key)
    if not force and cached and (time.time() - cached["ts"]) < _CACHE_TTL:
        return cached["models"]

    binary = _resolve_binary(desc["aliases"])
    if not binary:
        _logger.debug(f"model_discovery: CLI '{cli_key}' not found in PATH")
        return []

    models: list[str] = []

    # Path A: use a callable fetcher (e.g. REST API, curated list)
    fetch_fn = desc.get("fetch_models")
    if fetch_fn is not None:
        try:
            models = fetch_fn() or []
        except Exception as e:
            _logger.debug(f"model_discovery: fetch_models for '{cli_key}' failed: {e}")
        _DISCOVERY_CACHE[cli_key] = {"models": models, "binary": binary, "ts": time.time()}
        _logger.info(f"model_discovery: '{cli_key}' → {len(models)} models (via fetch)")
        return models

    # Path B: run the binary with list_args and parse stdout
    list_args = desc.get("list_args") or ["--list-models"]
    args = [binary] + [a for a in list_args if a]
    parse_fn = desc.get("parse", lambda s: [line.strip() for line in s.splitlines() if line.strip()])

    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=8)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0 and not stdout:
            _logger.debug(f"model_discovery: '{cli_key} {list_args}' failed ({result.returncode}): {stderr[:200]}")
        else:
            models = parse_fn(stdout or stderr)

        if not models:
            _logger.debug(f"model_discovery: '{cli_key}' returned no models. stdout={stdout[:200]}")

    except subprocess.TimeoutExpired:
        _logger.debug(f"model_discovery: timeout listing models for '{cli_key}'")
    except Exception as e:
        _logger.debug(f"model_discovery: unexpected error for '{cli_key}': {e}")

    _DISCOVERY_CACHE[cli_key] = {"models": models, "binary": binary, "ts": time.time()}
    _logger.info(f"model_discovery: '{cli_key}' → {len(models)} models (via subprocess)")
    return models


def discover_ollama_models(config: Any = None, endpoint: str | None = None) -> list[str]:
    """
    Returns a list of model names from a local Ollama instance.

    Accepts an optional *config* object (uses ``ollama_endpoint`` setting
    with WSL fallback) or an explicit *endpoint* URL.  If neither is given,
    falls back to ``http://localhost:11434/api/tags``.
    """
    from mentask.core.ollama_endpoint import fetch_ollama_models, resolve_base_url

    base = endpoint.removesuffix("/api/tags").rstrip("/") if endpoint is not None else resolve_base_url(config)
    return fetch_ollama_models(base)


def get_installed_cli_binaries() -> list[str]:
    """Returns the list of CLI descriptor keys whose binaries are installed."""
    return [key for key, desc in _CLI_DESCRIPTORS.items() if _resolve_binary(desc["aliases"]) is not None]


def get_model_flag(cli_key: str) -> str | None:
    """Returns the flag used by a CLI to select a model (e.g. '--model')."""
    desc = _CLI_DESCRIPTORS.get(cli_key)
    return desc.get("model_flag") if desc else None
