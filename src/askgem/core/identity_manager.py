from pathlib import Path
from .paths import get_config_dir, get_global_config_dir, get_standard_knowledge_dir


class KnowledgeManager:
    """
    Manages the hierarchical knowledge Hub for AskGem.
    Loads and aggregates markdown files from:
    1. Standard Hub (Package internal)
    2. Global Hub (~/.askgem/)
    3. Local Hub (User Project .askgem/)
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
            try:
                with open(md_file, encoding="utf-8") as f:
                    file_content = f.read().strip()
                    if file_content:
                        content.append(f"### Knowledge Module: {md_file.stem.upper()}\n{file_content}")
            except Exception:
                continue

        return "\n\n".join(content)

    def read_knowledge_hub(self) -> str:
        """
        Aggregates the entire Knowledge Hub hierarchy.
        
        Returns:
            str: Full concatenated markdown instructions.
        """
        full_hub = []

        # 1. Internal Standard Hub
        standard = self._load_md_from_dir(self.standard_dir)
        if standard:
            full_hub.append(f"## STANDARDIZED CORE KNOWLEDGE\n{standard}")

        # 2. Global Personal Hub (~/.askgem/)
        global_kb = self._load_md_from_dir(self.global_dir)
        if global_kb:
            full_hub.append(f"## GLOBAL PERSONAL KNOWLEDGE\n{global_kb}")

        # 3. Local Project Project Hub (.askgem/ or project root)
        # We check both the .askgem folder and the .askgem_knowledge.md file specifically
        local_dir_kb = ""
        if self.active_dir != self.global_dir:
            local_dir_kb = self._load_md_from_dir(self.active_dir)

        # Legacy/Shortcut: Project root .askgem_knowledge.md
        local_file_kb = ""
        local_path = Path.cwd() / ".askgem_knowledge.md"
        if local_path.exists():
            try:
                with open(local_path, encoding="utf-8") as f:
                    local_file_kb = f.read().strip()
            except Exception:
                pass

        if local_dir_kb or local_file_kb:
            full_hub.append(f"## LOCAL PROJECT KNOWLEDGE\n{local_dir_kb}\n\n{local_file_kb}")

        if not full_hub:
            return "No extended knowledge available."

        return "\n\n".join(full_hub)

    def read_identity(self) -> str:
        """Backward compatibility for IdentityManager. Legacy calls use this."""
        return self.read_knowledge_hub()
