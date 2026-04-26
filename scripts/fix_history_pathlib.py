import os
import re

path = "src/mentask/core/history_manager.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add pathlib import if missing
if "from pathlib import Path" not in content:
    content = "from pathlib import Path\n" + content

# Refactor save_session to use pathlib
old_save = """        filepath = os.path.join(self.history_dir, f"{self.current_session_id}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:"""
            
new_save = """        file_p = Path(self.history_dir) / f"{self.current_session_id}.json"
        try:
            with open(file_p, "w", encoding="utf-8") as f:"""

content = content.replace(old_save, new_save)

# Refactor load_session to use Path.resolve() for safety
old_load = """        filepath = os.path.abspath(os.path.join(self.history_dir, f"{session_id}.json"))
        base_dir = os.path.abspath(self.history_dir)

        if os.path.commonpath([base_dir, filepath]) != base_dir:
            return None

        if not os.path.exists(filepath):"""

new_load = """        base_dir = Path(self.history_dir).resolve()
        file_p = (base_dir / f"{session_id}.json").resolve()

        # Secure check: ensure the file is inside the history directory
        if base_dir not in file_p.parents:
            _logger.error(f"Security: Attempted access outside history dir: {file_p}")
            return None

        if not file_p.exists():"""

content = content.replace(old_load, new_load)

# Clean up os.path usage in delete_session as well
content = content.replace('if os.path.exists(filepath):', 'if Path(filepath).exists():')
content = content.replace('os.remove(filepath)', 'Path(filepath).unlink(missing_ok=True)')

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
