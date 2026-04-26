"""
Tools for managing persistent memory and active missions.
"""

from ..core.memory_manager import MemoryManager
from ..core.mission_manager import MissionManager

# Singletons for the tools to use
_memory = MemoryManager()
_mission = MissionManager()


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


def manage_mission(action: str, task: str = "") -> str:
    """Manages high-level active goals and task tracking (heartbeat.md).

    Use this to keep track of what you are currently working on.

    Args:
        action (str): 'add' to create a new task, 'complete' to mark as done, 'read' to view missions.
        task (str): The description of the task (required for 'add' and 'complete').

    Returns:
        str: Feedback on the mission update or the heartbeat content.
    """
    if action == "add":
        if not task:
            return "Error: task is required for 'add' action."
        if _mission.add_task(task):
            return f"Success: Task '{task}' added to active missions."
        return "Error: Failed to update heartbeat."
    elif action == "complete":
        if not task:
            return "Error: task is required for 'complete' action."
        if _mission.complete_task(task):
            return f"Success: Task matching '{task}' marked as completed."
        return f"Error: Task '{task}' not found or already completed."
    elif action == "read":
        return _mission.read_missions()
    return f"Error: Unknown action '{action}'."
