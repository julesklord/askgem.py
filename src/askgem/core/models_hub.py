import json
import logging
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from askgem.core.paths import get_config_dir

_logger = logging.getLogger("askgem")

MODELS_DEV_URL = "https://models.dev/api.json"
CACHE_FILENAME = "models_cache.json"
CACHE_TTL = 86400  # 24 hours in seconds


class ModelsHub:
    """
    Central registry for AI models, powered by models.dev.
    Provides dynamic pricing, context limits, and capability information.
    """

    _instance = None
    _data: Dict[str, Any] = {}
    _last_sync: float = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelsHub, cls).__new__(cls)
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
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    self._data = cache_data.get("models_data", {})
                    self._last_sync = cache_data.get("last_sync", 0)
            except Exception as e:
                _logger.warning(f"Failed to load models cache: {e}")

    def _save_cache(self):
        """Saves current model data to local cache."""
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"last_sync": self._last_sync, "models_data": self._data},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            _logger.error(f"Failed to save models cache: {e}")

    def sync(self, force: bool = False):
        """
        Synchronizes model data with models.dev.
        
        Args:
            force: If True, bypasses TTL check.
        """
        now = time.time()
        if not force and (now - self._last_sync) < CACHE_TTL:
            return

        _logger.info("Syncing models data from models.dev...")
        try:
            user_agent = "askgem-cli/0.18.0 (https://github.com/julesklord/askgem.py)"
            req = urllib.request.Request(MODELS_DEV_URL, headers={"User-Agent": user_agent})
            
            with urllib.request.urlopen(req, timeout=15) as response:
                self._data = json.load(response)
                self._last_sync = now
                self._save_cache()
                _logger.info("Models data synchronized successfully.")
        except Exception as e:
            _logger.error(f"Failed to sync models from models.dev: {e}")
            if not self._data:
                _logger.warning("No model data available (sync failed and no cache).")

    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Gets details for a specific model.
        Model ID can be direct (e.g. 'gemini-2.0-flash') or scoped ('google:gemini-2.0-flash').
        """
        if not self._data:
            self.sync()

        # Direct match in providers
        for provider_info in self._data.values():
            models = provider_info.get("models", {})
            if model_id in models:
                return models[model_id]
            
            # Scoped match (provider:model)
            for m_id, m_info in models.items():
                scoped_id = f"{provider_info.get('id')}:{m_id}"
                if scoped_id == model_id:
                    return m_info

        return None

    def search(self, query: str = "", provider: str = "", capability: str = "") -> List[Dict[str, Any]]:
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
                        "reasoning": "reasoning"
                    }
                    cap_key = cap_map.get(capability.lower(), capability.lower())
                    if not m_info.get(cap_key):
                        continue

                # Check query in name or id
                if query:
                    q = query.lower()
                    if q not in m_info.get("name", "").lower() and q not in m_id.lower():
                        continue

                # Add extra context
                m_info["_provider"] = p_id
                m_info["_provider_name"] = p_info.get("name")
                results.append(m_info)

        return results

    def get_pricing(self, model_id: str) -> Dict[str, float]:
        """
        Returns pricing info for a model in USD per 1M tokens.
        Default: {'input': 0.0, 'output': 0.0}
        """
        info = self.get_model(model_id)
        if not info:
            return {"input": 0.0, "output": 0.0}
        
        cost = info.get("cost", {})
        return {
            "input": float(cost.get("input", 0.0)),
            "output": float(cost.get("output", 0.0))
        }

# Global instance
hub = ModelsHub()
