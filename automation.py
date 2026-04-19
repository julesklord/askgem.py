import os
import subprocess

pyproject = "G:/DEVELOPMENT/askgem.py/pyproject.toml"
init_file = "G:/DEVELOPMENT/askgem.py/src/askgem/__init__.py"
changelog = "G:/DEVELOPMENT/askgem.py/CHANGELOG.md"

versions = ["0.14.1", "0.14.2", "0.14.3", "0.14.4", "0.14.5", "0.14.6", "0.14.7", "0.14.8", "0.14.9", "0.15.0"]
current_version = "0.14.0"

for v in versions:
    # Edit files
    with open(pyproject, "r", encoding='utf-8') as f:
        content = f.read()
    content = content.replace(f'version = "{current_version}"', f'version = "{v}"')
    with open(pyproject, "w", encoding='utf-8') as f:
        f.write(content)

    with open(init_file, "r", encoding='utf-8') as f:
        content = f.read()
    content = content.replace(f'__version__ = "{current_version}"', f'__version__ = "{v}"')
    with open(init_file, "w", encoding='utf-8') as f:
        f.write(content)

    # Update Changelog
    with open(changelog, "r", encoding='utf-8') as f:
        content = f.read()
    new_entry = f"## [{v}] — 2026-04-19\n\n- release: v{v}\n\n"
    content = content.replace("## [0.14.0]", f"{new_entry}## [0.14.0]")
    with open(changelog, "w", encoding='utf-8') as f:
        f.write(content)

    # Commit and Tag
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"release: v{v}"], check=True)
    subprocess.run(["git", "tag", "-a", f"v{v}", "-m", f"Release v{v}"], check=True)

    current_version = v
