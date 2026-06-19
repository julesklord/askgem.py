"""
constants.py — Centralized configuration, defaults, endpoints, and timeout values.
"""

# Default API and service endpoints
OPENAI_DEFAULT_API_BASE = "https://api.openai.com/v1"
MODELS_DEV_URL = "https://models.dev/api.json"
OLLAMA_DEFAULT_ENDPOINT = "http://localhost:11434"

# Timeout configurations (in seconds)
DEFAULT_REQUEST_TIMEOUT = 60
DEFAULT_HEALTHCHECK_TIMEOUT = 10
DEFAULT_MODEL_DISCOVERY_TIMEOUT = 5
DEFAULT_MODEL_DEV_SYNC_TIMEOUT = 15
DEFAULT_OLLAMA_TIMEOUT = 3
DEFAULT_WEB_SEARCH_TIMEOUT = 10
DEFAULT_GLOBAL_EXECUTION_TIMEOUT = 120

# Cache time-to-live (TTL) configurations (in seconds)
MODELS_HUB_CACHE_TTL = 21600       # 6 hours
MODEL_DISCOVERY_CACHE_TTL = 300     # 5 minutes

# File and resource configurations
MODELS_HUB_CACHE_FILENAME = "models_cache.json"
PERSISTENT_MEMORY_FILENAME = "memory.md"
