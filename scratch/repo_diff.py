import argparse
import os
import subprocess
import sys


def is_git_repo(path):
    """Check if the given path is inside a git repository."""
    try:
        # rev-parse works even if the path is a subdirectory of the repo
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            capture_output=True,
            check=True,
            text=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def main():
    parser = argparse.ArgumentParser(description="Get git diff for a specific repository.")
    parser.add_argument("repo_path", help="Path to the repository")
    parser.add_argument("--base", default="HEAD~1", help="Base reference (default: HEAD~1)")
    parser.add_argument("--head", default="HEAD", help="Head reference (default: HEAD)")

    args = parser.parse_args()
    repo_path = os.path.abspath(args.repo_path)

    if not os.path.exists(repo_path):
        print(f"Error: Path '{repo_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if not is_git_repo(repo_path):
        print(f"Error: '{repo_path}' is not a valid git repository.", file=sys.stderr)
        sys.exit(1)

    try:
        # Use --no-pager to prevent blocking in some environments
        cmd = ["git", "--no-pager", "diff", args.base, args.head]
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        # Return diff text to stdout
        sys.stdout.write(result.stdout)

    except subprocess.CalledProcessError as e:
        print(f"Git diff failed with exit code {e.returncode}:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(e.returncode)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
