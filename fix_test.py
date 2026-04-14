import re

with open('tests/tools/test_file_tools.py', 'r') as f:
    content = f.read()

# Replace the assertion to check for backups in the .askgem directory
# because _create_backup was changed to save centrally
new_test = """    def test_creates_bkp_before_editing(self, tmp_path, monkeypatch):
        # mock get_backups_dir to return a dir inside tmp_path
        monkeypatch.setattr("askgem.core.paths.get_backups_dir", lambda: tmp_path / "backups")
        f = tmp_path / "code.py"
        f.write_text("original content")
        edit_file(str(f), "original content", "new content")

        import glob
        bkp_list = glob.glob(str(tmp_path / "backups" / "*" / "code.py"))
        assert len(bkp_list) > 0
        assert open(bkp_list[0]).read() == "original content"
"""

content = re.sub(r'    def test_creates_bkp_before_editing\(self, tmp_path\):.*?assert bkp.read_text\(\) == "original content"\n', new_test, content, flags=re.DOTALL)

with open('tests/tools/test_file_tools.py', 'w') as f:
    f.write(content)
