import os
from pathlib import Path

path = "src/mentask/agent/core/execution.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add pathlib import if missing at the top
if "from pathlib import Path" not in content:
    content = "from pathlib import Path\n" + content

# 1. Update build_security_warning
old_warning = """        if tool_call.name in ("read_file", "write_file", "edit_file", "list_dir"):
            from ...core.security import ensure_safe_path
            try:
                ensure_safe_path(tool_call.arguments.get("path", "."))
            except PermissionError as exc:
                return f"PATH ESCAPE ATTEMPT: {exc}\""""

new_warning = """        if tool_call.name in ("read_file", "write_file", "edit_file", "list_dir", "replace"):
            from ...core.security import ensure_safe_path
            try:
                # Use resolve() to get canonical path and prevent bypasses
                raw_path = tool_call.arguments.get("path") or tool_call.arguments.get("file_path", ".")
                resolved_path = Path(raw_path).resolve()
                ensure_safe_path(str(resolved_path))
            except PermissionError as exc:
                return f"PATH ESCAPE ATTEMPT: {exc}"
            except Exception as exc:
                return f"INVALID PATH: {exc}\""""

if old_warning in content:
    content = content.replace(old_warning, new_warning)
else:
    # Fallback search if strings don't match exactly due to formatting
    import re
    content = re.sub(r'if tool_call\.name in \("read_file",.*?\)\s+except PermissionError as exc:\s+return f"PATH ESCAPE ATTEMPT: \{exc\}"', new_warning, content, flags=re.DOTALL)

# 2. Update is_dir_trusted
content = content.replace(
    'is_dir_trusted = self.trust.is_trusted(os.getcwd())',
    'is_dir_trusted = self.trust.is_trusted(Path.cwd().resolve())'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
