"""
Analysis logic module for repository exploration and token estimation.
"""

import os
import subprocess
from pathlib import Path


def get_git_diff_stat(base_ref: str = "HEAD") -> str:
    """Executes git diff --stat to see modified files and magnitude of changes."""
    try:
        result = subprocess.run(["git", "diff", "--stat", base_ref], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return f"Error: Git diff failed (maybe not a git repo?). {result.stderr}"
        return result.stdout or "No changes detected via git diff."
    except Exception as e:
        return f"Error executing git: {e}"


def get_repo_structure(max_depth: int = 2) -> str:
    """Generates a shallow tree of the repository to understand structure."""
    try:
        # Use git ls-files if available, otherwise fallback to os.walk
        result = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            files = result.stdout.splitlines()
            # Basic tree-like grouping for the first max_depth levels
            tree = {}
            for f in files:
                parts = Path(f).parts[: max_depth + 1]
                curr = tree
                for p in parts:
                    if p not in curr:
                        curr[p] = {}
                    curr = curr[p]

            def render_tree(t, indent=0):
                lines = []
                for k in sorted(t.keys()):
                    lines.append("  " * indent + f"- {k}")
                    lines.extend(render_tree(t[k], indent + 1))
                return lines

            return "\n".join(render_tree(tree))
        else:
            # Fallback for non-git
            return "Not a git repository. Listing current directory:\n" + "\n".join(os.listdir("."))
    except Exception as e:
        return f"Error mapping repo: {e}"


def detect_project_blueprint() -> str:
    """Detects technologies and entry points."""
    findings = []
    files = os.listdir(".")

    if "package.json" in files:
        findings.append("Node.js/TypeScript Project (package.json detected)")
    if "pyproject.toml" in files or "requirements.txt" in files:
        findings.append("Python Project (pyproject.toml/requirements.txt detected)")
    if "Cargo.toml" in files:
        findings.append("Rust Project (Cargo.toml detected)")
    if "go.mod" in files:
        findings.append("Go Project (go.mod detected)")

    return "\n".join(findings) if findings else "Generic or unknown project structure."
