"""
Security and validation module for mentask.
Centralizes access control and safety checks for file and system operations.
"""

import enum
import os
import re
from dataclasses import dataclass
from pathlib import Path


class SafetyLevel(enum.Enum):
    SAFE = "safe"  # Auto-executable if configured
    NOTICE = "notice"  # Normal confirmation
    WARNING = "warning"  # High risk, needs red confirmation
    DANGEROUS = "dangerous"  # Massive risk, explicit "FORCE" needed


@dataclass
class SafetyReport:
    level: SafetyLevel
    category: str
    description: str
    pattern: str | None = None


# List of base commands that are considered "safe" (informative only)
_SAFE_COMMAND_WHITELIST: set[str] = {
    "ls",
    "git status",
    "git branch",
    "pwd",
    "dir",
    "date",
    "whoami",
    "python --version",
    "pip --version",
    "pip list",
    "git log",
    "git diff",
    "cat",
    "type",
    "echo",
    "hostname",
    "ver",
    "systeminfo",
    "ping",
}

DANGEROUS_PATTERNS = [
    # Mass Deletion
    (
        r"\brm\s+.*?(?:(?:-[a-z]*r[a-z]*|--recursive)(?:[\s'\"=;]|$|/).*?(?:/|\*|\./\*|~|~/)(?:[\s'\"=;]|$|/)|(?:/|\*|\./\*|~|~/)(?:[\s'\"=;]|$|/).*?(?:-[a-z]*r[a-z]*|--recursive)(?:[\s'\"=;]|$))",
        SafetyLevel.DANGEROUS,
        "MASS_DELETION",
        "Recursive deletion of root or wildcard patterns.",
    ),
    (r"(del|erase)\s+/s\s+/q", SafetyLevel.DANGEROUS, "MASS_DELETION", "Recursive silent deletion on Windows."),
    (r"Remove-Item.*-Recurse", SafetyLevel.DANGEROUS, "MASS_DELETION", "PowerShell recursive deletion."),
    # Network Exposure
    (
        r"(curl|wget).*(pipe|sh|bash|pwsh|powershell)",
        SafetyLevel.DANGEROUS,
        "NETWORK_INSTALL",
        "Direct pipe from web to shell (potential remote code execution).",
    ),
    (r"nc\s+-(l|p|lp)", SafetyLevel.WARNING, "NETWORK_EXPOSURE", "Opening a network listener (Netcat)."),
    (r"nmap", SafetyLevel.NOTICE, "NETWORK_SCAN", "Network scanning detected."),
    # System & Privilege
    (r"(sudo|doas|runas)", SafetyLevel.WARNING, "PRIVILEGE_ESCALATION", "Attempting to escalate privileges."),
    (r"chmod\s+777", SafetyLevel.DANGEROUS, "SYSTEM_MOD", "Setting world-writable permissions."),
    (r"reg\s+(add|delete|import)", SafetyLevel.WARNING, "SYSTEM_MOD", "Modifying Windows Registry."),
    # Information Leakage & Persistence
    (
        r"cat\s+.*(\.ssh|shadow|passwd|config\.js|settings\.json)",
        SafetyLevel.WARNING,
        "INFO_LEAK",
        "Accessing sensitive configuration or credentials.",
    ),
    (
        r"env\b|printenv\b|set\b",
        SafetyLevel.NOTICE,
        "INFO_LEAK",
        "Listing all environment variables (may contain secrets).",
    ),
    # Fork Bombs / DoS
    (r":\(\)\{\s*:\|:& \};:", SafetyLevel.DANGEROUS, "DOS_ATTACK", "Classic Bash fork-bomb."),
]

# Files that are essential for project integrity
CRITICAL_FILES: set[str] = {
    "pyproject.toml",
    "package.json",
    "uv.lock",
    "package-lock.json",
    "tox.ini",
    "makefile",
    "cmakelists.txt",
    ".gitignore",
    ".env",
    "mentask.py.code-workspace",
}

# Directories that should not be touched by the agent (unless specifically configured)
CRITICAL_DIRECTORIES: set[str] = {
    ".git",
    ".github",
    ".mentask",
}


def ensure_safe_path(path: str) -> str:
    """Ensures that the provided path is within the current working directory."""
    if (re.match(r"^[a-zA-Z]:[\\/]", path) or path.startswith("\\\\")) and os.name != "nt":
        raise PermissionError(f"Access denied: Path '{path}' is an absolute Windows path.")

    abs_path = os.path.abspath(path)
    cwd = os.getcwd()
    try:
        # Check if they share a common path that is exactly the CWD
        if os.path.commonpath([cwd, abs_path]) != cwd:
            raise PermissionError(f"Access denied: Path '{path}' is outside the allowed directory.")
    except ValueError:
        raise PermissionError(f"Access denied: Path '{path}' is on a different drive or outside context.") from None
    return abs_path


def analyze_command_safety(command: str) -> SafetyReport:
    """Analyzes a command and returns a detailed safety report.
    Args:
        command: The full command string.
    Returns:
        SafetyReport: The result of the analysis.
    """
    cmd_clean = command.strip().lower()

    # 1. Check for Critical/Dangerous patterns first
    for pattern, level, category, desc in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            return SafetyReport(level=level, category=category, description=desc, pattern=pattern)

    # 2. Check Whitelist for "SAFE" status
    # If it has pipes/redirections, it's NOT safe by default
    if any(op in cmd_clean for op in ["|", ">", "<", "&", ";", "`", "$("]):
        return SafetyReport(
            level=SafetyLevel.NOTICE, category="COMPLEX_COMMAND", description="Command contains pipes or redirections."
        )

    # Check if the command starts with any whitelisted phrase
    for safe_cmd in _SAFE_COMMAND_WHITELIST:
        if cmd_clean == safe_cmd or cmd_clean.startswith(f"{safe_cmd} "):
            return SafetyReport(
                level=SafetyLevel.SAFE, category="WHITELISTED", description="Informative or safe command."
            )

    # 3. Default fallback
    return SafetyReport(level=SafetyLevel.NOTICE, category="GENERIC_COMMAND", description="Standard shell command.")


def analyze_path_safety(path_str: str) -> SafetyReport:
    """Analyzes a file path for criticality and potential risks.

    Checks if the file is a known critical configuration file or belongs
    to a sensitive project directory.
    """
    path = Path(path_str)
    name = path.name.lower()

    # 1. Check if it's a critical file
    if name in CRITICAL_FILES:
        return SafetyReport(
            level=SafetyLevel.WARNING,
            category="CRITICAL_ASSET",
            description=f"Attempting to modify a critical project configuration file: {path.name}",
        )

    # 2. Check if it belongs to a critical directory
    parts = set(p.lower() for p in path.parts)
    intersect = parts.intersection(CRITICAL_DIRECTORIES)
    if intersect:
        dir_name = list(intersect)[0]

        # Exception: Allow dynamic agent tools in .mentask/plugins/
        if dir_name == ".mentask" and "plugins" in [p.lower() for p in path.parts]:
            pass
        else:
            return SafetyReport(
                level=SafetyLevel.DANGEROUS,
                category="PROTECTED_DIRECTORY",
                description=f"Attempting to modify internal project metadata in protected directory: {dir_name}",
            )

    return SafetyReport(level=SafetyLevel.SAFE, category="PATH_SAFE", description="Standard project path.")


def is_command_safe(command: str) -> bool:
    """Legacy wrapper for compatibility."""
    report = analyze_command_safety(command)
    return report.level == SafetyLevel.SAFE
