import os
import re

def fix_test_file_tools():
    with open('tests/tools/test_file_tools.py', 'r') as f:
        content = f.read()

    # 1. Update imports
    content = content.replace("askgem.tools.file_tools._ensure_safe_path", "askgem.core.security.ensure_safe_path")
    content = content.replace("from askgem.tools.file_tools import _ensure_safe_path, edit_file, read_file", "from askgem.core.security import ensure_safe_path\nfrom askgem.tools.file_tools import edit_file, read_file")
    content = content.replace("_ensure_safe_path", "ensure_safe_path")
    content = content.replace('patch("askgem.tools.file_tools._ensure_safe_path"', 'patch("askgem.tools.file_tools.ensure_safe_path"')
    content = content.replace('patch("askgem.core.security.ensure_safe_path"', 'patch("askgem.tools.file_tools.ensure_safe_path"')

    # 2. Fix backup path checking
    new_test = """    def test_creates_bkp_before_editing(self, tmp_path, monkeypatch):
        # mock get_backups_dir to return a dir inside tmp_path
        monkeypatch.setattr("askgem.tools.file_tools.get_backups_dir", lambda: tmp_path / "backups")
        f = tmp_path / "code.py"
        f.write_text("original content")
        edit_file(str(f), "original content", "new content")

        import glob
        bkp_list = glob.glob(str(tmp_path / "backups" / "*" / "code.py"))
        assert len(bkp_list) > 0
        assert open(bkp_list[0]).read() == "original content"
"""
    content = re.sub(r'    def test_creates_bkp_before_editing\(self, tmp_path\):.*?assert bkp_list\[0\]\)\.read\(\) == "original content"\n', new_test, content, flags=re.DOTALL)
    content = re.sub(r'    def test_creates_bkp_before_editing\(self, tmp_path, monkeypatch\):.*?assert open\(bkp_list\[0\]\)\.read\(\) == "original content"\n', new_test, content, flags=re.DOTALL)

    with open('tests/tools/test_file_tools.py', 'w') as f:
        f.write(content)

def fix_test_security_file_tools():
    with open('tests/tools/test_security_file_tools.py', 'r') as f:
        content2 = f.read()

    content2 = content2.replace("from askgem.tools.file_tools import _ensure_safe_path", "from askgem.core.security import ensure_safe_path")
    content2 = content2.replace("_ensure_safe_path", "ensure_safe_path")

    with open('tests/tools/test_security_file_tools.py', 'w') as f:
        f.write(content2)

def fix_test_registry():
    with open('tests/test_tools_registry.py', 'r') as f:
        content3 = f.read()

    content3 = content3.replace('with patch("askgem.agent.tools_registry.is_command_safe", return_value=False):', 'with patch("askgem.agent.tools_registry.analyze_command_safety") as mock_analyze:\n                import askgem.core.security\n                mock_analyze.return_value.level = askgem.core.security.SafetyLevel.DANGEROUS\n                mock_analyze.return_value.category = "mock"\n                mock_analyze.return_value.description = "mock"')

    with open('tests/test_tools_registry.py', 'w') as f:
        f.write(content3)

fix_test_file_tools()
fix_test_security_file_tools()
try:
    fix_test_registry()
except:
    pass
