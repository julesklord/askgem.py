"""
General persistent memory manager for mentask.

Handles reading and writing to memory.md, which stores long-term facts,
user preferences, and project-specific context.
"""

import logging
import os
from pathlib import Path
from typing import Any

from .paths import (
    ensure_dir,
    get_config_dir,
    get_local_knowledge_path,
    get_memory_path,
)

_logger = logging.getLogger("mentask.core.memory")


DEFAULT_MEMORY_TEMPLATE = """# mentask Persistent Memory
# Last Updated: {date}

## User Profile & Preferences
- Preferred Language: Spanish (Default)

## Lessons Learned & Facts
-

## Rules & Constraints
-
"""

DEFAULT_LOCAL_TEMPLATE = """# Project Knowledge: {project}
# Last Updated: {date}

## Project Patterns
-

## Fixed Errors
-

## Tech Stack
-
"""


class MemoryManager:
    """Manages both global (~/.mentask/memory.md) and project-local memory.

    Local memory is stored in .mentask/memory.md if the directory is initialized,
    otherwise it falls back to .mentask_knowledge.md in the project root.
    """

    def __init__(self, config=None):
        self.config = config
        self.path_global = get_memory_path()
        self.path_local = get_local_knowledge_path()
        self.memory_dir = os.path.join(get_config_dir(), "memories")
        ensure_dir(Path(self.memory_dir))

        self._ensure_memory_exists(self.path_global, DEFAULT_MEMORY_TEMPLATE)

    def _ensure_memory_exists(self, path: str, template: str):
        """Creates a memory file with a template if it doesn't exist."""
        if not os.path.exists(path):
            from datetime import datetime

            project_name = os.path.basename(os.getcwd())
            content = template.format(date=datetime.now().strftime("%Y-%m-%d"), project=project_name)
            ensure_dir(Path(os.path.dirname(path)))
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    def scan_memories(self) -> list[dict]:
        """Scans the memories directory for additional context files using a metadata cache."""
        memories = []
        if not os.path.exists(self.memory_dir):
            return []

        cache_path = os.path.join(self.memory_dir, ".metadata_cache.json")
        import json
        cache = {}
        if os.path.exists(cache_path):
            try:
                with open(cache_path, encoding="utf-8") as f:
                    cache = json.load(f)
            except Exception as e:
                _logger.debug("Failed to read metadata cache: %s", e, exc_info=True)
                cache = {}

        updated_cache = False
        for file in os.listdir(self.memory_dir):
            if file.endswith(".md") and not file.startswith("."):
                path = os.path.join(self.memory_dir, file)
                mtime = os.path.getmtime(path)

                # Check cache first
                if file in cache and cache[file].get("mtime") == mtime:
                    memories.append(cache[file])
                    continue

                # Cache miss or outdated: Read and parse
                try:
                    with open(path, encoding="utf-8") as f:
                        content = f.read(1000)

                    lines = [line.strip() for line in content.splitlines() if line.strip()]
                    desc = ""
                    if lines:
                        desc = lines[1] if lines[0].startswith("#") and len(lines) > 1 else lines[0]

                    entry = {
                        "filename": file,
                        "path": path,
                        "description": desc[:200],
                        "mtime": mtime,
                    }
                    memories.append(entry)
                    cache[file] = entry
                    updated_cache = True
                except Exception as e:  # nosec B112
                    _logger.debug(f"Failed to read memory file {file}: {e}")
                    continue

        if updated_cache:
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(cache, f)
            except Exception as e:
                _logger.debug(f"Failed to save memory cache: {e}")

        return sorted(memories, key=lambda x: x["mtime"], reverse=True)

    async def find_relevant_memories(self, query: str, orchestrator: Any) -> str:
        """Uses a side-query to select the most relevant memories for the current task.

        This implements the 'Selective Memory' pattern from the Reference Synergy initiative.
        """
        memories = self.scan_memories()
        if not memories:
            return ""

        # Limit manifest to top 100 most recent memories to avoid context bloat in side-query
        manifest_entries = [f"- {m['filename']}: {m['description']}" for m in memories[:100]]
        manifest = "\n".join(manifest_entries)

        selection_prompt = (
            "You are a selective memory retrieval system for MentAsk.\n"
            "Given the USER QUERY and a list of AVAILABLE MEMORY FILES (with brief descriptions), "
            "identify which files contain information that would be CRITICAL to answering the query accurately.\n\n"
            f"AVAILABLE MEMORIES:\n{manifest}\n\n"
            f"USER QUERY: {query}\n\n"
            "INSTRUCTIONS:\n"
            "1. Select up to 3 filenames.\n"
            "2. Respond ONLY with a comma-separated list of filenames (e.g., 'coding_patterns.md, api_keys.md').\n"
            "3. If none are truly relevant, respond exactly with 'NONE'.\n"
            "4. Do not provide any explanation or markdown formatting."
        )

        try:
            # We use a lower temperature and a dedicated call for the side-query
            selected_raw = ""
            # We use the provider directly for a stateless, clean turn
            async for event in orchestrator.provider.stream_turn(
                [{"role": "user", "content": selection_prompt}], [], config={"temperature": 0.0}
            ):
                if event["type"] == "text":
                    selected_raw += event["content"]

            selected_raw = selected_raw.strip().strip("\"'")
            if "NONE" in selected_raw.upper() or not selected_raw:
                return ""

            # Parse filenames, being careful with comma/newline variations
            candidates = [f.strip() for f in selected_raw.replace("\n", ",").split(",")]
            valid_filenames = {m["filename"] for m in memories}
            selected_files = [f for f in candidates if f in valid_filenames]

            if not selected_files:
                return ""

            relevant_content = "\n--- SELECTIVE MEMORY (Relevant Context) ---\n"
            for filename in selected_files:
                path = os.path.join(self.memory_dir, filename)
                try:
                    with open(path, encoding="utf-8") as f:
                        file_content = f.read()
                    relevant_content += f"\n[File: {filename}]\n{file_content}\n"
                except Exception as e:
                    _logger.warning(f"Failed to read selected memory {filename}: {e}")

            return relevant_content + "--- END SELECTIVE MEMORY ---\n"
        except Exception as e:
            _logger.error(f"Error in selective memory retrieval: {e}")
            return ""

    def read_memory(self, scope: str = "all") -> str:
        """Reads memory content.

        Args:
            scope: 'global', 'local', or 'all' (merged).
        """
        global_content = ""
        local_content = ""

        if scope in ("global", "all") and os.path.exists(self.path_global):
            with open(self.path_global, encoding="utf-8") as f:
                global_content = f"--- GLOBAL PERSISTENT MEMORY ---\n{f.read()}\n"

        if scope in ("local", "all") and os.path.exists(self.path_local):
            with open(self.path_local, encoding="utf-8") as f:
                local_content = f"--- LOCAL PROJECT KNOWLEDGE ---\n{f.read()}\n"

        if scope == "all":
            return f"{global_content}\n{local_content}"
        return global_content if scope == "global" else local_content

    def add_fact(self, fact: str, category: str = "Lessons Learned & Facts", scope: str = "local") -> bool:
        """Appends a new fact to a specific category in global or local memory.

        Args:
            fact: The fact to remember.
            category: The markdown section.
            scope: 'global' or 'local'.
        """
        path = self.path_local if scope == "local" else self.path_global
        template = DEFAULT_LOCAL_TEMPLATE if scope == "local" else DEFAULT_MEMORY_TEMPLATE

        # Ensure it exists before adding
        self._ensure_memory_exists(path, template)

        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()

            lines = content.splitlines()

            # Optimization: Use sets for O(1) category membership matching
            existing_categories = {
                line.strip().lower().replace("## ", "").strip()
                for line in lines
                if line.strip().startswith("##")
            }

            target_cat_norm = category.strip().lower()
            target_index = -1

            if target_cat_norm in existing_categories:
                # Find the index of the header line
                for i, line in enumerate(lines):
                    line_stripped = line.strip().lower()
                    if line_stripped.startswith("##") and line_stripped.replace("##", "").strip() == target_cat_norm:
                        target_index = i
                        break

            if target_index != -1:
                lines.insert(target_index + 1, f"- {fact}")
            else:
                lines.append(f"\n## {category}")
                lines.append(f"- {fact}")

            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True
        except Exception as e:
            _logger.error("Failed to add fact to memory at %s: %s", path, e, exc_info=True)
            return False

    def reset_memory(self, scope: str = "global"):
        """Wipes specific memory file."""
        path = self.path_local if scope == "local" else self.path_global
        if os.path.exists(path):
            os.remove(path)
        # Re-ensure if global
        if scope == "global":
            self._ensure_memory_exists(self.path_global, DEFAULT_MEMORY_TEMPLATE)
