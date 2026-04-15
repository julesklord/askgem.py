import pytest

from askgem.core.security import ensure_safe_path as _ensure_safe_path


def test_path_traversal_prefix_bypass(tmp_path, monkeypatch):
    """
    Test that _ensure_safe_path correctly blocks access to paths that
    happen to share a string prefix with the current working directory
    but are actually outside of it.
    """
    # Setup:
    # /tmp/pytest-of-user/pytest-0/test_path_traversal_prefix_bypass0/app
    # /tmp/pytest-of-user/pytest-0/test_path_traversal_prefix_bypass0/app_secret

    base_dir = tmp_path / "app"
    secret_dir = tmp_path / "app_secret"
    base_dir.mkdir()
    secret_dir.mkdir()

    secret_file = secret_dir / "secret.txt"
    secret_file.write_text("sensitive data")

    # Change CWD to the app directory
    monkeypatch.chdir(base_dir)

    # This path is OUTSIDE the CWD, but its absolute path starts with CWD as a string.
    # Vulnerable code: abs_path.startswith(cwd)
    # /.../app_secret/secret.txt starts with /.../app
    malicious_path = str(secret_file)

    # This should RAISE PermissionError.
    # If the vulnerability is present, it will NOT raise.
    with pytest.raises(PermissionError) as excinfo:
        _ensure_safe_path(malicious_path)

    assert "outside the allowed directory" in str(excinfo.value)

def test_ensure_safe_path_normal_behavior(tmp_path, monkeypatch):
    """Ensure that legitimate paths are still allowed."""
    base_dir = tmp_path / "app"
    base_dir.mkdir()

    file_in_base = base_dir / "valid.txt"
    file_in_base.write_text("safe content")

    monkeypatch.chdir(base_dir)

    # Relative path
    assert _ensure_safe_path("valid.txt") == str(file_in_base)

    # Absolute path
    assert _ensure_safe_path(str(file_in_base)) == str(file_in_base)

    # Subdirectory
    sub_dir = base_dir / "subdir"
    sub_dir.mkdir()
    file_in_sub = sub_dir / "sub.txt"
    file_in_sub.write_text("more safe content")

    assert _ensure_safe_path("subdir/sub.txt") == str(file_in_sub)
