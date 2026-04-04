"""
File manipulation tools module for the AI agent.

Provides guarded operations for reading and substituting code within existing files.
It does NOT execute scripts or handle file parsing logic beyond plain text.
"""

import difflib
import os
import shutil


def read_file(path: str, start_line: int = None, end_line: int = None) -> str:
    """Reads the content of a local file with safety limits.

    Allows reading specific line ranges to prevent exceeding token limits on massive files.
    Includes a 30,000 character safety cap for full-file reads.

    Args:
        path (str): Absolute or relative path to the file.
        start_line (int, optional): 1-indexed line number to start from. Defaults to None.
        end_line (int, optional): 1-indexed line number to stop at. Defaults to None.

    Returns:
        str: The content of the file or an error message.
    """
    try:
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."

        if not os.path.isfile(path):
            return f"Error: '{path}' is a directory. Use list_directory instead."

        with open(path, encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)
        if total_lines == 0:
            return f"The file '{path}' is completely empty."

        start = max(1, start_line) if start_line is not None else 1
        end = min(total_lines, end_line) if end_line is not None else total_lines

        if start > total_lines or start > end:
            return f"Error: Invalid line range [{start}-{end}]. File only has {total_lines} lines."

        # Extract lines (0-indexed extraction)
        selected_lines = lines[start - 1 : end]
        content = "".join(selected_lines)

        # Character Limit Protection (Milestone 2.4 Optimization)
        char_limit = 30000
        if len(content) > char_limit:
            content = content[:char_limit] + f"\n\n... [!] Content truncated at {char_limit} characters. Use specific line ranges to read more."

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
    Automatically creates a `.bkp` backup of the file before applying changes to prevent data loss.

    Args:
        path: Path to the file to modify.
        find_text: The EXACT literal string block to replace (including whitespaces/indentation).
        replace_text: The new content that will replace the find_text block.

    Returns:
        Status message of the modification result.
    """
    try:
        if not os.path.exists(path):
            # If the file doesn't exist, we assume the AI wants to create it
            # In that case, find_text should be empty.
            if find_text:
                return f"Error: File '{path}' does not exist, so we cannot search for text. To create a new file, leave 'find_text' empty."

            # Create subdirectories if needed
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(replace_text)
            return f"Success: Created new file '{path}' and wrote the content."

        # Read existing content
        with open(path, encoding='utf-8') as f:
            content = f.read()

        # Guard: empty find_text on an existing file would corrupt every character via str.replace behavior,
        # UNLESS the file is currently empty, in which case we allow writing to it from scratch.
        if not find_text and content:
            return f"Error: 'find_text' cannot be empty when the file '{path}' already contains text. Provide the exact block to replace, or delete the file first."

        # Target must exist exactly in the file
        if find_text not in content:
            return f"Error: The exact block 'find_text' was not found in '{path}'. Remember that indentation and inner blank lines must match perfectly. Use read_file to verify the exact content first."

        # Create a backup before proceeding (simple suffix logic)
        backup_path = f"{path}.bkp"
        shutil.copy2(path, backup_path)

        # Apply replacement
        new_content = content.replace(find_text, replace_text)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return f"Success: Replaced text in '{path}'. Original file backed up securely at '{backup_path}'."

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
        if not os.path.exists(path):
            if find_text:
                return f"Error: File '{path}' does not exist. Cannot diff non-existent content."
            # New file creation diff
            lines_after = replace_text.splitlines(keepends=True)
            diff = difflib.unified_diff([], lines_after, fromfile="/dev/null", tofile=path)
            return "".join(diff) or "No changes detected."

        with open(path, encoding='utf-8') as f:
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
