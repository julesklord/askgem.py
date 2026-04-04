"""
Tools for managing persistent memory, identity, and dynamic tasks.
"""

from ..core.memory_manager import MemoryManager
from ..core.tasks_manager import TasksManager
from ..core.identity_manager import IdentityManager

# Singletons for the tools to use
_memory = MemoryManager()
_tasks = TasksManager()
_identity = IdentityManager()

def manage_memory(action: str, content: str = "", category: str = "Lessons Learned & Facts") -> str:
    """Manages the agent's long-term persistent memory (memory.md).

    Use this to 'learn' new facts about the user, project, or environment.

    Args:
        action (str): 'add' to append a fact, 'read' to view memory, 'reset' to wipe it.
        content (str): The fact or information to remember (required for 'add').
        category (str): The section header in the markdown file.

    Returns:
        str: Feedback on the operation or the memory content.
    """
    if action == "add":
        if not content:
            return "Error: content is required for 'add' action."
        if _memory.add_fact(content, category):
            return f"Success: Fact remembered in '{category}'."
        return "Error: Failed to update memory."
    elif action == "read":
        return _memory.read_memory()
    elif action == "reset":
        _memory.reset_memory()
        return "Success: Memory has been reset to default template."
    return f"Error: Unknown action '{action}'."

def manage_tasks(action: str, task: str = "", content: str = "") -> str:
    """Manages active goals and dynamic functions (tasks.md).

    Use this to track what you are doing or to refine your operational logic.

    Args:
        action (str): 'add' (task), 'complete' (task), 'read', 'update' (full overwrite).
        task (str): The description of the task (required for 'add' and 'complete').
        content (str): Full markdown content (required for 'update').

    Returns:
        str: Feedback on the operation.
    """
    if action == "add":
        if not task:
            return "Error: task is required for 'add' action."
        if _tasks.add_task(task):
            return f"Success: Task '{task}' added."
        return "Error: Failed to update tasks."
    elif action == "complete":
        if not task:
            return "Error: task is required for 'complete' action."
        if _tasks.complete_task(task):
            return f"Success: Task matching '{task}' completed."
        return "Error: Task not found."
    elif action == "read":
        return _tasks.read_tasks()
    elif action == "update":
        if not content:
            return "Error: content is required for 'update' action."
        if _tasks.update_tasks(content):
            return "Success: tasks.md updated."
        return "Error: Failed to update tasks."
    return f"Error: Unknown action '{action}'."

def manage_identity(action: str, content: str = "") -> str:
    """Manages the agent's core identity and persona (identity.md).

    Args:
        action (str): 'read' or 'update' (overwrite).
        content (str): New identity markdown (required for 'update').

    Returns:
        str: Identity content or feedback.
    """
    if action == "read":
        return _identity.read_identity()
    elif action == "update":
        if not content:
            return "Error: content is required for 'update' action."
        if _identity.update_identity(content):
            return "Success: identity.md updated. Restart may be required for full effect."
        return "Error: Failed to update identity."
    return f"Error: Unknown action '{action}'."
