import os
import pytest
from pygemai_cli.security import save_encrypted_api_key, load_decrypted_api_key, save_unencrypted_api_key, load_unencrypted_api_key
from pygemai_cli.ui import ThemeManager
from pygemai_cli.constants import PREDEFINED_THEMES

@pytest.fixture
def theme_manager():
    return ThemeManager(PREDEFINED_THEMES, "Legacy")

def test_encryption_decryption(theme_manager, tmp_path):
    # Mocking config path to use tmp_path
    import pygemai_cli.utils
    original_get_config_path = pygemai_cli.utils.get_config_path
    pygemai_cli.utils.get_config_path = lambda f: str(tmp_path / f)
    
    api_key = "test-api-key-123"
    password = "secure-password-8"
    
    save_encrypted_api_key(api_key, password, theme_manager)
    loaded_key = load_decrypted_api_key(password, theme_manager)
    
    assert loaded_key == api_key
    
    # Test wrong password
    assert load_decrypted_api_key("wrong-password", theme_manager) is None
    
    # Restore original function
    pygemai_cli.utils.get_config_path = original_get_config_path

def test_unencrypted_storage(theme_manager, tmp_path):
    import pygemai_cli.utils
    original_get_config_path = pygemai_cli.utils.get_config_path
    pygemai_cli.utils.get_config_path = lambda f: str(tmp_path / f)
    
    api_key = "plain-api-key"
    save_unencrypted_api_key(api_key, theme_manager)
    loaded_key = load_unencrypted_api_key(theme_manager)
    
    assert loaded_key == api_key
    
    pygemai_cli.utils.get_config_path = original_get_config_path
