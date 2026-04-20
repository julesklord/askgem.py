import os
import re

path = "src/askgem/core/history_manager.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Ensure logging is imported and logger defined
if "import logging" not in content:
    content = "import logging\n" + content
if "_logger = logging.getLogger" not in content:
    content = content.replace("import json", "import json\n\n_logger = logging.getLogger(\"askgem\")")

# 2. Fix delete_session (silenced pass)
old_delete = """        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception:
            return False"""

new_delete = """        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                _logger.info(f"Deleted session file: {filepath}")
                return True
            return False
        except OSError as e:
            _logger.error(f"Failed to delete session {session_id}: {e}")
            return False"""

content = content.replace(old_delete, new_delete)

# 3. Fix list_sessions
content = content.replace(
    'except Exception:',
    'except OSError as e:\n            _logger.error(f"Failed to list sessions: {e}")'
)

# 4. Replace console prints with logging for internal errors
content = content.replace(
    'self.console.print(f"[dim red]Error saving session history: {e}[/dim red]")',
    '_logger.error(f"Error saving session history: {e}")'
)
content = content.replace(
    'self.console.print(f"[dim red]Error loading session \'{session_id}\': {e}[/dim red]")',
    '_logger.error(f"Error loading session \'{session_id}\': {e}")'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
