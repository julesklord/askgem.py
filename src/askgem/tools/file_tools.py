"""
File manipulation tools module for the AI agent.

Provides guarded operations for reading and substituting code within existing files.
It does NOT execute scripts or handle file parsing logic beyond plain text.
"""

import difflib
import os
import shutil
import tempfile


def _ensure_safe_path(path: str) -> str:
    """Ensures that the provided path is within the current working directory.

    Args:
        path: The path to validate.

    Returns:
        The absolute path if safe.

    Raises:
        PermissionError: If the path is outside the CWD.
    """
    abs_path = os.path.abspath(path)
    cwd = os.getcwd()
    if not abs_path.startswith(cwd):
        raise PermissionError(
            f"Access denied: Path '{path}' is outside the allowed directory."
        )
    return abs_path


def read_file(path: str, start_line: int = None, end_line: int = None) -> str:
    """Reads the content of a local file with safety limits.

    Allows reading specific line ranges to prevent exceeding token limits on massive files.
    Uses a generator to stream lines and avoid memory overhead.
    Includes a 30,000 character safety cap for the returned content.

    Args:
        path (str): Absolute or relative path to the file.
        start_line (int, optional): 1-indexed line number to start from. Defaults to None.
        end_line (int, optional): 1-indexed line number to stop at. Defaults to None.

    Returns:
        str: The content of the file or an error message.
    """
    try:
        path = _ensure_safe_path(path)
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."

        if not os.path.isfile(path):
            return f"Error: '{path}' is a directory. Use list_directory instead."

        # Count total lines first (efficiently)
        with open(path, encoding="utf-8") as f:
            total_lines = sum(1 for _ in f)

        if total_lines == 0:
            return f"The file '{path}' is completely empty."

        start = max(1, start_line) if start_line is not None else 1
        end = min(total_lines, end_line) if end_line is not None else total_lines

        if start > total_lines or start > end:
            return f"Error: Invalid line range [{start}-{end}]. File only has {total_lines} lines."

        # Extract selected lines using streaming
        selected_lines = []
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if i < start:
                    continue
                if i > end:
                    break
                selected_lines.append(line)

        content = "".join(selected_lines)

        # Safety cap: prevent context window explosion on large files
        char_limit = 30_000
        if len(content) > char_limit:
            content = (
                content[:char_limit]
                + f"\n\n... [!] Content truncated at {char_limit} characters. "
                f"Use start_line/end_line to read specific ranges."
            )

        info_header = f"--- Reading '{path}' (Lines {start} to {end} of {total_lines}) ---\n"
        return info_header + content

    except UnicodeDecodeError:
        return f"Error: '{path}' appears to be a binary file or uses an unsupported encoding. Cannot read as text."
    except PermissionError:
        return f"Error: Permission denied to read file '{path}'."
    except Exception as e:
        return f"Unexpected error reading '{path}': {e}"


def edit_file(path: str, find_text: str, replace_text: str) -> str:
    """
    Finds an exact block of text in a local file and replaces it.
    Uses atomic writing (temporary file + rename) and creates a `.bkp` backup
    to prevent data loss and corruption.

    Args:
        path: Path to the file to modify.
        find_text: The EXACT literal string block to replace (including whitespaces/indentation).
        replace_text: The new content that will replace the find_text block.

    Returns:
        Status message of the modification result.
    """
    try:
        path = _ensure_safe_path(path)
        if not os.path.exists(path):
            # If the file doesn't exist, we assume the AI wants to create it
            # In that case, find_text should be empty.
            if find_text:
                return f"Error: File '{path}' does not exist, so we cannot search for text. To create a new file, leave 'find_text' empty."

            # Create subdirectories if needed
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            # Atomic write for new file as well
            dir_name = os.path.dirname(os.path.abspath(path))
            fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix=".askgem_tmp_", text=True)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(replace_text)
                os.replace(temp_path, path)
            except Exception:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise

            return f"Success: Created new file '{path}' and wrote the content."

        # Read existing content
        with open(path, encoding="utf-8") as f:
            content = f.read()

        # Guard: empty find_text on an existing file would corrupt every character via str.replace behavior,
        # UNLESS the file is currently empty, in which case we allow writing to it from scratch.
        if not find_text and content:
            return f"Error: 'find_text' cannot be empty when the file '{path}' already contains text. Provide the exact block to replace, or delete the file first."

        # Target must exist exactly in the file
        if find_text not in content:
            return f"Error: The exact block 'find_text' was not found in '{path}'. Remember that indentation and inner blank lines must match perfectly. Use read_file to verify the exact content first."

        # Guard: ambiguous replacement — multiple matches would corrupt unintended sections
        occurrences = content.count(find_text)
        if occurrences > 1:
            return (
                f"Error: 'find_text' was found {occurrences} times in '{path}'. "
                f"Replacement is ambiguous. Provide more surrounding context in 'find_text' "
                f"to uniquely identify the target block."
            )

        # Create a backup before proceeding (simple suffix logic)
        backup_path = f"{path}.bkp"
        shutil.copy2(path, backup_path)

        # Apply replacement (safe: exactly one occurrence guaranteed above)
        new_content = content.replace(find_text, replace_text, 1)

        # Atomic write: write to a temporary file in the same directory and then rename
        # This prevents file corruption if the process is interrupted during writing.
        dir_name = os.path.dirname(os.path.abspath(path))
        fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix=".askgem_tmp_", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(new_content)
            # Preserve original permissions
            shutil.copymode(path, temp_path)
            os.replace(temp_path, path)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

        return f"Success: Replaced text in '{path}'. Original file backed up securely at '{backup_path}' and written atomically."

    except UnicodeDecodeError:
        return f"Error: '{path}' appears to be a binary file. Refusing to edit."
    except PermissionError:
        return f"Error: Permission denied modifying '{path}'."
    except Exception as e:
        return f"Fatal error modifying '{path}': {e}"


def diff_file(path: str, find_text: str, replace_text: str) -> str:
    """Generates a unified diff preview of a proposed change without modifying the file.

    Useful for verifying that a search-and-replace block targets the correct lines
    and has the intended effect before calling edit_file.

    Args:
        path (str): Path to the file to preview.
        find_text (str): The exact block of text to be replaced.
        replace_text (str): The new content to substitute.

    Returns:
        str: A formatted unified diff or an error message.
    """
    try:
        path = _ensure_safe_path(path)
        if not os.path.exists(path):
            if find_text:
                return f"Error: File '{path}' does not exist. Cannot diff non-existent content."
            # New file creation diff
            lines_after = replace_text.splitlines(keepends=True)
            diff = difflib.unified_diff([], lines_after, fromfile="/dev/null", tofile=path)
            return "".join(diff) or "No changes detected."

        with open(path, encoding="utf-8") as f:
            content = f.read()

        if find_text not in content:
            return f"Error: 'find_text' was not found in '{path}'. Diff cannot be generated."

        new_content = content.replace(find_text, replace_text)

        lines_before = content.splitlines(keepends=True)
        lines_after = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(lines_before, lines_after, fromfile=path, tofile=path)
        return "".join(diff) or "No changes detected (find_text and replace_text are identical)."

    except Exception as e:
        return f"Error generating diff for '{path}': {e}"


def list_directory(path: str = ".") -> str:
    """
    Lists all files and folders inside a specific directory on the host system.
    Useful for exploring the current working environment, finding code or other resources.

    Args:
        path: The absolute or relative path of the directory to list. Empty defaults to the current directory.

    Returns:
        A formatted string with the found items or an error message if the path is invalid.
    """
    if not path:
        path = "."

    try:
        path = _ensure_safe_path(path)
        if not os.path.exists(path):
            return f"Error: The path '{path}' does not exist."
        if not os.path.isdir(path):
            return f"Error: The path '{path}' is a file, not a directory."

        elements = sorted(os.listdir(path))
        if not elements:
            return f"The directory '{path}' is empty."

        max_items = 100
        total_items = len(elements)

        listing = [f"Directory: {path}"]
        listing.append(f"Items (showing {min(max_items, total_items)} of {total_items}):")

        for item in elements[:max_items]:
            full_path = os.path.join(path, item)
            item_type = "📁" if os.path.isdir(full_path) else "📄"
            listing.append(f"- {item_type} {item}")

        if total_items > max_items:
            listing.append(f"\n[i] ... and {total_items - max_items} more items hidden. Use a more specific path.")

        return "\n".join(listing)
    except PermissionError:
        return f"Error: Permission denied to read the path '{path}'."
    except Exception as e:
        return f"Unexpected error while listing path '{path}': {e}"


def delete_file(path: str) -> str:
    """Deletes a file permanently. Use with caution.

    Args:
        path (str): Path to the file to delete.

    Returns:
        str: Success or error message.
    """
    try:
        path = _ensure_safe_path(path)
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."
        if os.path.isdir(path):
            return f"Error: '{path}' is a directory. delete_file only works on files."

        os.remove(path)
        return f"Success: Deleted file '{path}'."
    except Exception as e:
        return f"Error deleting file '{path}': {e}"


def move_file(source: str, destination: str) -> str:
    """Moves or renames a file.

    Args:
        source (str): Current file path.
        destination (str): New file path.

    Returns:
        str: Success or error message.
    """
    try:
        source = _ensure_safe_path(source)
        destination = _ensure_safe_path(destination)
        if not os.path.exists(source):
            return f"Error: Source file '{source}' does not exist."

        # Create destination directory if it doesn't exist
        dest_dir = os.path.dirname(os.path.abspath(destination))
        os.makedirs(dest_dir, exist_ok=True)

        shutil.move(source, destination)
        return f"Success: Moved '{source}' to '{destination}'."
    except Exception as e:
        return f"Error moving file: {e}"
