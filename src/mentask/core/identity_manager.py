import contextlib
from pathlib import Path

from .paths import get_config_dir, get_global_config_dir, get_standard_knowledge_dir


class KnowledgeManager:
    """
    Manages the hierarchical knowledge Hub for mentask.
    Loads and aggregates markdown files from:
    1. Standard Hub (Package internal)
    2. Global Hub (~/.mentask/)
    3. Local Hub (User Project .mentask/)
    """

    def __init__(self):
        self.standard_dir = get_standard_knowledge_dir()
        self.global_dir = get_global_config_dir()
        self.active_dir = get_config_dir()

    def _load_md_from_dir(self, directory: Path) -> str:
        """Reads all .md files in a directory and concatenates them."""
        content = []
        if not directory.exists():
            return ""

        # Search for markdown files
        for md_file in sorted(directory.glob("*.md")):
            with contextlib.suppress(Exception), open(md_file, encoding="utf-8") as f:
                file_content = f.read().strip()
                if file_content:
                    content.append(f"### Knowledge Module: {md_file.stem.upper()}\n{file_content}")

        return "\n\n".join(content)

    def get_knowledge_index(self) -> str:
        """
        Returns a concise index of all available knowledge modules across hubs.
        This is what will be injected into the system prompt.
        """
        index = []

        for label, directory in [
            ("STANDARD", self.standard_dir),
            ("GLOBAL", self.global_dir),
            ("LOCAL", self.active_dir),
        ]:
            if directory.exists():
                modules = [f"{md.stem.upper()}" for md in directory.glob("*.md")]
                if modules:
                    index.append(f"- {label}: {', '.join(modules)}")

        # Check for legacy local file
        if (Path.cwd() / ".mentask_knowledge.md").exists():
            index.append("- LOCAL: PROJECT_KNOWLEDGE (Legacy file)")

        if not index:
            return "No extended knowledge modules available."

        return "\n".join(index)

    def get_module_content(self, module_name: str) -> str | None:
        """
        Retrieves the content of a specific module by its name (case-insensitive).
        """
        target = module_name.lower()

        # Search in all directories
        for directory in [self.active_dir, self.global_dir, self.standard_dir]:
            if not directory.exists():
                continue
            for md_file in directory.glob("*.md"):
                if md_file.stem.lower() == target:
                    with contextlib.suppress(Exception):
                        return md_file.read_text(encoding="utf-8").strip()

        # Check legacy file
        if target in ("project_knowledge", ".mentask_knowledge"):
            legacy_path = Path.cwd() / ".mentask_knowledge.md"
            if legacy_path.exists():
                return legacy_path.read_text(encoding="utf-8").strip()

        return None

    def read_knowledge_hub(self) -> str:
        """
        Aggregates the entire Knowledge Hub hierarchy (Legacy/Full mode).
        Used when token economy is not a priority or for debugging.
        """
        full_hub = []

        # 1. Internal Standard Hub
        standard = self._load_md_from_dir(self.standard_dir)
        if standard:
            full_hub.append(f"## STANDARDIZED CORE KNOWLEDGE\n{standard}")

        # 2. Global Personal Hub (~/.mentask/)
        global_kb = self._load_md_from_dir(self.global_dir)
        if global_kb:
            full_hub.append(f"## GLOBAL PERSONAL KNOWLEDGE\n{global_kb}")

        # 3. Local Project Project Hub (.mentask/ or project root)
        # We check both the .mentask folder and the .mentask_knowledge.md file specifically
        local_dir_kb = ""
        if self.active_dir != self.global_dir:
            local_dir_kb = self._load_md_from_dir(self.active_dir)

        # Legacy/Shortcut: Project root .mentask_knowledge.md
        local_file_kb = ""
        local_path = Path.cwd() / ".mentask_knowledge.md"
        if local_path.exists():
            with contextlib.suppress(Exception), open(local_path, encoding="utf-8") as f:
                local_file_kb = f.read().strip()

        if local_dir_kb or local_file_kb:
            full_hub.append(f"## LOCAL PROJECT KNOWLEDGE\n{local_dir_kb}\n\n{local_file_kb}")

        if not full_hub:
            return "No extended knowledge available."

        return "\n\n".join(full_hub)

    def read_identity(self) -> str:
        """
        Loads only the essential identity configuration from:
        1. .mentask_identity.md (Global/Home)
        2. .mentask_identity.md (Local Project Root)
        3. identity.md (Local .mentask/ folder)

        The heavy Knowledge Hub aggregation is suspended.
        """
        identity = []

        # 1. Global Identity
        global_path = get_global_config_dir() / ".mentask_identity.md"
        if global_path.exists():
            with contextlib.suppress(Exception):
                identity.append(global_path.read_text(encoding="utf-8"))

        # 2. Local Identity (Folder-based)
        if self.active_dir != self.global_dir:
            folder_identity = self.active_dir / "identity.md"
            if folder_identity.exists():
                with contextlib.suppress(Exception):
                    identity.append(folder_identity.read_text(encoding="utf-8"))

        # 3. Local Identity (Legacy/Root file)
        local_path = Path.cwd() / ".mentask_identity.md"
        if local_path.exists():
            with contextlib.suppress(Exception):
                identity.append(local_path.read_text(encoding="utf-8"))

        if not identity:
            return "You are mentask, a professional autonomous coding agent."

        return "\n\n".join(identity)
