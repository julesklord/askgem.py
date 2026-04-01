import os
import subprocess
from typing import List

def list_directory(path: str = ".") -> str:
    """
    Lists all files and folders inside a specific directory on the host system.
    Useful for exploring the current working environment, finding code or other resources.
    
    Args:
        path: The absolute or relative path of the directory to list. Empty defaults to the current directory.
        
    Returns:
        A formatted string with the found items or an error message if the path is invalid.
    """
    try:
        elements = os.listdir(path)
        if not elements:
            return f"The directory '{path}' is empty."
        
        listing = [f"Directory: {path}"]
        listing.append("Items:")
        for item in sorted(elements):
            full_path = os.path.join(path, item)
            item_type = "📁" if os.path.isdir(full_path) else "📄"
            listing.append(f"- {item_type} {item}")
            
        return "\n".join(listing)
    except FileNotFoundError:
        return f"Error: The path '{path}' does not exist."
    except PermissionError:
        return f"Error: Permission denied to read the path '{path}'."
    except Exception as e:
        return f"Unexpected error while listing path '{path}': {e}"


def execute_bash(command: str) -> str:
    """
    Executes a shell command (bash or cmd), captures its standard output (stdout) and errors (stderr), 
    and returns them as text.
    
    WARNING: Use primarily for safe script executions, automated testing,
    git status checks, version checks, or compilations.
    
    Args:
        command: The exact command to execute in the local user's terminal.
        
    Returns:
        The output of the executed command or a failure message if the command crashes or isn't found.
    """
    try:
        # shell=True allows literal command execution (e.g., supporting Pipes, 'cd')
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False # We handle exit codes manually to prevent Python loop crashes
        )
        
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
            
        if not output:
            output = "Command executed successfully. (No output printed on screen)"
            
        return output.strip()
    except Exception as e:
        return f"Critical error attempting to execute command '{command}': {e}"
