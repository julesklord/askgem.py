import json
import logging
import time
import urllib.request
from pathlib import Path
from typing import Any

from mentask.core.paths import get_config_dir
from mentask.core.subprocess_safety import validate_url_scheme

_logger = logging.getLogger("mentask")

MODELS_DEV_URL = "https://models.dev/api.json"
CACHE_FILENAME = "models_cache.json"
CACHE_TTL = 21600  # 6 hours in seconds (fresher data)


class ModelsHub:
    """
    Central registry for AI models, powered by models.dev and local discovery (Ollama).
    Provides dynamic pricing, context limits, and capability information.
    """

    _instance = None
    _data_store: dict[str, Any] = {}
    _flat_models: dict[str, Any] = {}
    _local_models: dict[str, Any] = {}
    _last_sync: float = 0

    @property
    def _data(self):
        return self._data_store

    @_data.setter
    def _data(self, value):
        self._data_store = value
        self._rebuild_index()

    @_data.deleter
    def _data(self):
        self._data_store = {}
        self._rebuild_index()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Ensure we only initialize once
        if not hasattr(self, "initialized"):
            self.cache_path = Path(get_config_dir()) / CACHE_FILENAME
            self._load_cache()
            self.initialized = True

    def _load_cache(self):
        """Loads model data from local cache if available and not expired."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, encoding="utf-8") as f:
                    cache_data = json.load(f)
                    self._data = cache_data.get("models_data", {})
                    self._last_sync = cache_data.get("last_sync", 0)
                    # We don't cache local discovery as it changes often
                    self._rebuild_index()
            except Exception as e:
                _logger.warning(f"Failed to load models cache: {e}")

    def _save_cache(self):
        """Saves current model data to local cache."""
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"last_sync": self._last_sync, "models_data": self._data},
                    f,
                    ensure_ascii=False,
                )
        except Exception as e:
            _logger.error(f"Failed to save models cache: {e}")

    def _rebuild_index(self):
        self._flat_models.clear()

        # 1. Add cloud models from models.dev
        if hasattr(self, "_data") and self._data:
            for p_id, p_info in self._data.items():
                if not isinstance(p_info, dict):
                    continue

                provider_meta = {
                    "id": p_id,
                    "name": p_info.get("name", p_id),
                    "api": p_info.get("api"),
                    "env": p_info.get("env", []),
                }

                models = p_info.get("models", {})
                if not isinstance(models, dict):
                    continue

                for m_id, m_info in models.items():
                    if not isinstance(m_info, dict):
                        continue

                    # Enrich model info with provider metadata
                    m_info["_provider"] = provider_meta

                    # Index by pure model ID
                    self._flat_models[m_id] = m_info
                    # Index by scoped ID (provider:model)
                    self._flat_models[f"{p_id}:{m_id}"] = m_info

        # 2. Add local models (discovered via Ollama)
        for m_id, m_info in self._local_models.items():
            self._flat_models[m_id] = m_info
            self._flat_models[f"ollama:{m_id}"] = m_info

    def sync_local(self, config: Any = None, endpoint: str | None = None):
        """
        Discovers models from a local Ollama instance and local CLI binaries.

        Accepts an optional *config* to resolve the endpoint from settings
        (with WSL fallback) or an explicit *endpoint* URL.
        """
        from mentask.core.ollama_endpoint import fetch_ollama_models, resolve_base_url

        base = endpoint.removesuffix("/api/tags").rstrip("/") if endpoint is not None else resolve_base_url(config)

        _logger.debug("Syncing local models from %s...", base)

        new_local = {}

        # 1. Discover Ollama models
        try:
            models = fetch_ollama_models(base)

            for name in models:
                new_local[name] = {
                    "id": name,
                    "name": f"{name} (Local)",
                    "cost": {"input": 0, "output": 0},
                    "limit": {"context": 32768, "output": 4096},
                    "_provider": {
                        "id": "ollama",
                        "name": "Ollama (Local)",
                        "api": f"{base}/v1",
                        "env": [],
                    },
                }

                _logger.info(f"Discovered {len(new_local)} local Ollama models.")
        except Exception as e:
            _logger.debug(f"Local Ollama sync skipped: {e}")

        # 2. Discover supported CLI agents
        import shutil

        known_clis = {"gemini-cli": "Gemini CLI", "codex": "Codex CLI", "opencode": "OpenCode CLI"}

        cli_count = 0
        for bin_name, display_name in known_clis.items():
            if shutil.which(bin_name):
                # Use cli: as the provider prefix to map to CLIProvider
                new_local[bin_name] = {
                    "id": bin_name,
                    "name": display_name,
                    "cost": {"input": 0, "output": 0},
                    "limit": {"context": 1048576, "output": 8192},  # Assume large contexts for modern CLIs
                    "_provider": {
                        "id": "cli",
                        "name": "CLI Bridge",
                        "api": "local",
                        "env": [],
                    },
                }
                cli_count += 1

        if cli_count > 0:
            _logger.info(f"Discovered {cli_count} local CLI bridges.")

        self._local_models = new_local
        self._rebuild_index()

    def sync(self, force: bool = False, skip_local: bool = False):
        """
        Synchronizes model data with models.dev and local providers.

        Args:
            force: If True, bypasses TTL check.
            skip_local: If True, bypasses Ollama discovery.
        """
        now = time.time()
        if not force and (now - self._last_sync) < CACHE_TTL:
            if not skip_local:
                self.sync_local()
            return

        _logger.info("Syncing models data from models.dev...")
        try:
            user_agent = "mentask-cli/0.29.0 (https://github.com/TropicalDevApps/mentask.py)"
            validate_url_scheme(MODELS_DEV_URL)
            req = urllib.request.Request(MODELS_DEV_URL, headers={"User-Agent": user_agent})

            with urllib.request.urlopen(req, timeout=15) as response:  # nosec B310
                self._data = json.load(response)
                self._last_sync = now
                self._rebuild_index()
                self._save_cache()
                _logger.info("Models data synchronized successfully.")
        except Exception as e:
            _logger.error(f"Failed to sync models from models.dev: {e}")
            if not self._data:
                _logger.warning("No model data available (sync failed and no cache).")

        if not skip_local:
            self.sync_local()

    def get_model(self, model_id: str) -> dict[str, Any] | None:
        """
        Gets details for a specific model.
        Model ID can be direct (e.g. 'gemini-2.0-flash') or scoped ('google:gemini-2.0-flash').
        """
        if not self._data_store:
            self.sync()

        return self._flat_models.get(model_id)

    def search(self, query: str = "", provider: str = "", capability: str = "") -> list[dict[str, Any]]:
        """
        Searches the registry for models matching criteria.
        """
        if not self._data:
            self.sync()

        results = []
        for p_id, p_info in self._data.items():
            if provider and p_id.lower() != provider.lower():
                continue

            for m_id, m_info in p_info.get("models", {}).items():
                # Check capability (e.g. 'vision', 'tool_call', 'reasoning')
                if capability:
                    # Capability mapping
                    cap_map = {
                        "vision": "attachment",  # in models.dev, attachment usually means vision support
                        "tools": "tool_call",
                        "reasoning": "reasoning",
                    }
                    cap_key = cap_map.get(capability.lower(), capability.lower())
                    if not m_info.get(cap_key):
                        continue

                # Check query in name or id
                if query:
                    q = query.lower()
                    if q not in m_info.get("name", "").lower() and q not in m_id.lower():
                        continue

                # Add extra context without mutating the original dictionary
                result_info = m_info.copy()

                # Ensure _provider_name exists in the copy for backward compatibility
                if "_provider" in result_info and isinstance(result_info["_provider"], dict):
                    result_info["_provider_name"] = result_info["_provider"].get("name")
                else:
                    result_info["_provider_name"] = p_info.get("name")

                results.append(result_info)

        return results

    def get_provider_for_model(self, model_id: str) -> dict[str, Any] | None:
        """Returns provider metadata for a given model ID."""
        model_info = self.get_model(model_id)
        if model_info:
            return model_info.get("_provider")
        return None

    def get_pricing(self, model_id: str) -> dict[str, float]:
        """
        Returns pricing info for a model in USD per 1M tokens.
        Default: {'input': 0.0, 'output': 0.0}
        """
        info = self.get_model(model_id)
        if not info:
            return {"input": 0.0, "output": 0.0}

        cost = info.get("cost", {})
        return {"input": float(cost.get("input", 0.0)), "output": float(cost.get("output", 0.0))}


# Global instance
hub = ModelsHub()
