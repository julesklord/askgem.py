import os
from pathlib import Path
from pygemai_cli.utils import get_config_dir, get_config_path

def test_get_config_dir():
    config_dir = get_config_dir()
    assert isinstance(config_dir, Path)
    assert config_dir.name == ".pygemai"
    assert config_dir.exists()

def test_get_config_path():
    filename = "test_file.json"
    path = get_config_path(filename)
    assert os.path.isabs(path)
    assert path.endswith(filename)
    assert ".pygemai" in path
