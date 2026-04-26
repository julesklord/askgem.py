"""
Advanced search tools for the mentask agent.

Provides grep-like text searching and glob-based file discovery using standard libraries.
"""

import io
import re
from pathlib import Path


def _is_searchable_file(p: Path, exclude_dirs: set[str]) -> bool:
    """Checks if a file is suitable for text searching (not binary, not excluded)."""
    if not exclude_dirs.isdisjoint(p.parts):
        return False
    if not p.is_file():
        return False

    # Binary check
    try:
        with open(p, "rb") as f:
            if b"\x00" in f.read(1024):
                return False
    except OSError:
        return False

    return True


def grep_search(pattern: str, path: str = ".", is_regex: bool = False, case_sensitive: bool = False) -> str:
    """Recursively searches for a text pattern within files in a directory.

    Args:
        pattern (str): The text or regex pattern to search for.
        path (str): The root directory to start searching from. Defaults to ".".
        is_regex (bool): If True, treats pattern as a regular expression. Defaults to False.
        case_sensitive (bool): If True, performs case-sensitive matching. Defaults to False.

    Returns:
        str: A formatted list of matches (file:line:content) or a 'no matches' message.
    """
    root = Path(path)
    if not root.is_dir():
        return f"[!] Error: '{path}' is not a valid directory."

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags) if is_regex else re.compile(re.escape(pattern), flags)
    except re.error as e:
        return f"[!] Error: Invalid regex pattern: {e}"

    results = []
    # Skip binary/meta directories
    exclude_dirs = {".git", "node_modules", "__pycache__", ".venv", ".mentask"}

    total_matches = 0
    max_matches = 50

    try:
        for p in root.rglob("*"):
            if not exclude_dirs.isdisjoint(p.parts):
                continue
            if not p.is_file():
                continue

            try:
                with open(p, "rb") as f:
                    # Binary check
                    if b"\x00" in f.read(1024):
                        continue

                    f.seek(0)
                    # Use TextIOWrapper to read the same file handle as text
                    with io.TextIOWrapper(f, encoding="utf-8", errors="ignore") as tf:
                        for i, line in enumerate(tf, 1):
                            if regex.search(line):
                                rel_path = p.relative_to(root).as_posix()
                                results.append(f"{rel_path}:{i}:{line.strip()}")
                                total_matches += 1
                                if total_matches >= max_matches:
                                    results.append(f"\n[i] Showing first {max_matches} matches...")
                                    return "\n".join(results)
            except OSError:
                continue

    except Exception as e:
        return f"[!] Error during search: {e}"

    if not results:
        return f"No matches found for '{pattern}' in '{path}'."

    return "\n".join(results)


def glob_find(pattern: str, path: str = ".") -> str:
    """Finds files matching a glob pattern recursively.

    Args:
        pattern (str): The glob pattern (e.g., '*.py', '**/tests/*.md').
        path (str): The root directory to search. Defaults to ".".

    Returns:
        str: A newline-separated list of found file paths.
    """
    root = Path(path)
    if not root.is_dir():
        return f"[!] Error: '{path}' is not a valid directory."

    results = []
    exclude_dirs = {".git", "node_modules", "__pycache__", ".venv"}

    try:
        for p in root.rglob(pattern):
            if not exclude_dirs.isdisjoint(p.parts):
                continue
            if p.is_file():
                results.append(p.relative_to(root).as_posix())
    except Exception as e:
        return f"[!] Error during glob: {e}"

    if not results:
        return f"No files found matching '{pattern}' in '{path}'."

    return "\n".join(sorted(results))
