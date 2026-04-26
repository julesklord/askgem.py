import os
import re

path = "src/mentask/tools/web_tools.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Ensure logging is imported and logger defined
if "import logging" not in content:
    content = "import logging\n" + content
if "_logger = logging.getLogger" not in content:
    content = content.replace("import asyncio", "import asyncio\n\n_logger = logging.getLogger(\"mentask\")")

# 2. Fix Google Search error (log the error)
content = content.replace(
    'except Exception as e:\n        return f"Error en búsqueda de Google: {str(e)}. Intentando fallback..."',
    'except Exception as e:\n        _logger.error(f"Google Search API failed: {e}")\n        return f"Error en búsqueda de Google: {str(e)}. Intentando fallback..."'
)

# 3. Fix DuckDuckGo fallback
content = content.replace(
    'except Exception as e:\n        return f"Error en búsqueda de DuckDuckGo: {str(e)}"',
    'except Exception as e:\n        _logger.error(f"DuckDuckGo search failed: {e}")\n        return f"Error en búsqueda de DuckDuckGo: {str(e)}"'
)

# 4. Fix web_fetch (log the exception for debug)
content = content.replace(
    'except Exception as e:\n        return f"Error al leer URL {url}: {str(e)}"',
    'except Exception as e:\n        _logger.error(f"web_fetch error for {url}: {e}")\n        return f"Error al leer URL {url}: {str(e)}"'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
