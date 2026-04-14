import re

with open('tests/tools/test_file_tools.py', 'r') as f:
    content = f.read()

content = content.replace("askgem.tools.file_tools._ensure_safe_path", "askgem.core.security.ensure_safe_path")
content = content.replace("from askgem.tools.file_tools import _ensure_safe_path, edit_file, read_file", "from askgem.core.security import ensure_safe_path\nfrom askgem.tools.file_tools import edit_file, read_file")
content = content.replace("_ensure_safe_path", "ensure_safe_path")

with open('tests/tools/test_file_tools.py', 'w') as f:
    f.write(content)

with open('tests/tools/test_security_file_tools.py', 'r') as f:
    content2 = f.read()

content2 = content2.replace("from askgem.tools.file_tools import _ensure_safe_path", "from askgem.core.security import ensure_safe_path")
content2 = content2.replace("_ensure_safe_path", "ensure_safe_path")

with open('tests/tools/test_security_file_tools.py', 'w') as f:
    f.write(content2)
