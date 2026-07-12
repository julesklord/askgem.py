import logging
import subprocess

from mentask.core.subprocess_safety import safe_run

_logger = logging.getLogger("mentask.tools.git")


def git_commit(message: str, stage_all: bool = False, paths: list[str] | None = None) -> str:
    """
    Executes a git commit with the specified message.

    Args:
        message: The commit message.
        stage_all: If True, runs 'git add .' before committing.
        paths: Specific paths to stage before committing.
    """
    try:
        # 1. Staging
        if stage_all:
            safe_run(["git", "add", "."], check=True, capture_output=True)
        elif paths:
            safe_run(["git", "add"] + paths, check=True, capture_output=True)

        # 2. Check if there are changes to commit
        status = safe_run(["git", "diff", "--cached", "--quiet"], check=False)
        if status.returncode == 0:
            return "No changes staged to commit. Use 'stage_all=True' or stage files first."

        # 3. Commit
        result = safe_run(
            ["git", "commit", "-m", message],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        return f"Success: {result.stdout.strip()}"

    except subprocess.CalledProcessError as e:
        error_msg = (e.stderr or str(e)).strip()
        _logger.error(f"Git commit failed: {error_msg}")
        return f"Error: Git commit failed. {error_msg}"
    except Exception as e:
        _logger.error(f"Unexpected error during git commit: {e}")
        return f"Error: {str(e)}"


def get_staged_diff() -> str:
    """Returns the diff of staged changes."""
    try:
        result = safe_run(
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
        )
        return result.stdout or "No staged changes."
    except Exception as e:
        return f"Error getting staged diff: {e}"
