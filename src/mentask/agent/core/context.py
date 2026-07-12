"""
Context management module for mentask.

Handles system instruction assembly (Memory, Missions, OS),
project structure discovery, and context window optimization.
"""

import logging
import os
import platform
from pathlib import Path
from typing import Any

from ...core.i18n import _
from ...core.memory_manager import MemoryManager
from ...core.mission_manager import MissionManager

_logger = logging.getLogger("mentask.agent.context")

# Marker files that reveal the type of project
_PROJECT_MARKERS = {
    "pyproject.toml": "Python (pyproject)",
    "setup.py": "Python (setup.py)",
    "requirements.txt": "Python (pip)",
    "package.json": "Node.js / JavaScript",
    "tsconfig.json": "TypeScript",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "Makefile": "C/C++ or generic Make",
    "CMakeLists.txt": "C/C++ (CMake)",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java/Kotlin (Gradle)",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "pubspec.yaml": "Dart/Flutter",
}

# Directories to skip during blueprint scan
_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".mentask",
    ".tox",
    "dist",
    "build",
    ".eggs",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".next",
    "target",
    "coverage",
}


class ContextManager:
    """Manages the semantic context, project awareness, and memory of the agent."""

    def __init__(self):
        self.memory = MemoryManager()
        self.mission = MissionManager()

    # ------------------------------------------------------------------
    # Project Blueprint (auto-discovery)
    # ------------------------------------------------------------------
    def _get_project_blueprint(self, max_depth: int = 2) -> str:
        """Scans the CWD up to *max_depth* levels and returns a concise
        directory tree together with detected project type(s).

        The output is designed to be injected directly into the system prompt
        so the agent is aware of the project layout from turn 0.
        """
        cwd = Path.cwd()
        detected_types: list[str] = []
        tree_lines: list[str] = []

        def _walk(directory: Path, prefix: str, depth: int):
            if depth > max_depth:
                return
            try:
                entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            except PermissionError:
                return

            # Filter out hidden/skipped dirs
            entries = [
                e
                for e in entries
                if not (e.is_dir() and e.name in _SKIP_DIRS)
                and not (e.name.startswith(".") and e.is_dir() and e.name != ".mentask")
            ]

            for i, entry in enumerate(entries):
                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "
                child_prefix = prefix + ("    " if is_last else "│   ")

                if entry.is_dir():
                    tree_lines.append(f"{prefix}{connector}{entry.name}/")
                    _walk(entry, child_prefix, depth + 1)
                else:
                    # Detect project type from marker files
                    if entry.name in _PROJECT_MARKERS:
                        detected_types.append(_PROJECT_MARKERS[entry.name])
                    tree_lines.append(f"{prefix}{connector}{entry.name}")

        _walk(cwd, "", 0)

        # Assemble output
        project_type_str = ", ".join(set(detected_types)) if detected_types else "Unknown"
        blueprint = f"Project Root: {cwd.name}/\n"
        blueprint += f"Detected Type: {project_type_str}\n"
        blueprint += "```\n"
        blueprint += "\n".join(tree_lines[:80])  # Cap at 80 lines to save tokens
        if len(tree_lines) > 80:
            blueprint += f"\n... ({len(tree_lines) - 80} more entries)\n"
        blueprint += "\n```"
        return blueprint

    # ------------------------------------------------------------------
    # System Instruction Builder
    # ------------------------------------------------------------------
    async def get_relevant_context(self, query: str, orchestrator: Any) -> str:
        """Fetches relevant context from selective memory and workspace semantic RAG."""
        memory_context = ""
        try:
            memory_context = await self.memory.find_relevant_memories(query, orchestrator)
        except Exception as e:
            _logger.warning("Failed to fetch selective memory context: %s", e)

        rag_context = ""
        try:
            from ...core.rag_manager import RAGManager
            current_cwd = os.getcwd()

            # Lazy-init or re-index when the working directory changes
            if not hasattr(self, "_rag_manager") or getattr(self, "_rag_cwd", None) != current_cwd:
                self._rag_manager = RAGManager(root_dir=current_cwd)
                self._rag_manager.index_workspace()
                self._rag_cwd = current_cwd
                _logger.debug("RAG index built: %d chunks for '%s'", len(self._rag_manager.chunks), current_cwd)

            # Minimum similarity threshold — avoids injecting unrelated noise
            MIN_RELEVANCE = 0.15
            chunks = [c for c in self._rag_manager.query(query, top_k=4) if c["score"] >= MIN_RELEVANCE]

            if chunks:
                rag_lines = ["\n--- SEMANTIC WORKSPACE CONTEXT (Retrieved Files) ---"]
                for chunk in chunks:
                    rag_lines.append(
                        f"\n[File: {chunk['path']} | Lines {chunk['start_line']}-{chunk['end_line']} | Score: {chunk['score']:.2f}]"
                    )
                    rag_lines.append(chunk["content"])
                rag_lines.append("\n--- END SEMANTIC WORKSPACE CONTEXT ---")
                rag_context = "\n".join(rag_lines)
        except Exception as e:
            _logger.warning("Failed to fetch semantic RAG context: %s", e)

        merged = ""
        if memory_context:
            merged += memory_context + "\n"
        if rag_context:
            merged += rag_context + "\n"
        return merged

    def build_system_instruction(self, include_blueprint: bool = False, relevant_memory: str = "") -> str:
        """Assembles the system instruction.
        'include_blueprint' should only be True on initial turn or if specifically requested.
        'relevant_memory' is pre-fetched context from selective memory.
        """
        # Base context
        base_context = _("sys.context", os=f"{platform.system()} {platform.release()}", cwd=os.getcwd())
        full_instruction = f"{base_context}\n\n"

        if relevant_memory:
            full_instruction += f"{relevant_memory}\n\n"

        if include_blueprint:
            try:
                blueprint = self._get_project_blueprint()
                full_instruction += "## PROJECT STRUCTURE\n"
                full_instruction += f"{blueprint}\n\n"
            except Exception as e:
                _logger.warning("Failed to scan project structure: %s", e)

        # Efficiency & Tone guidelines
        full_instruction += self._get_efficiency_guidelines()
        full_instruction += self._get_tone_guidelines()
        full_instruction += self._get_action_care_guidelines()

        return full_instruction

    def _get_efficiency_guidelines(self) -> str:
        """Returns guidelines for token management and autonomous analysis."""
        return """
## TOKEN EFFICIENCY & FAST PATH
- **Be Concise**: Go straight to the point. Lead with the action. Skip "I will now...", "Let's begin by...".
- **Auto-Discovery**: Always check for `GEMINI.md`, `STANDARD.md`, or `README.md` at the start of a new complex task if they exist in the root to align with repository rules. Do not guess the architecture.
- **Fast Path Execution**: If the solution is obvious, localized, or explicitly requested, skip deep research and execute immediately. Do not over-plan simple tasks.
- **Surgical Reads**: Do not read full files to find a line. Use `grep_search` or `analyze_codebase(mode='map')`.
- **Parallel Execution**: Emit multiple tool calls in a single turn whenever independent tasks exist. Combine terminal commands (e.g. `git status && git diff`).
- **Context Management**: Use `delegate_mission(specialist_type='explorer')` to offload massive research tasks.
"""

    def _get_tone_guidelines(self) -> str:
        """Guidelines for how to communicate with the user."""
        return """
## COMMUNICATION STYLE
- **Professional & Direct**: Do not use emojis unless explicitly requested.
- **No Colon Before Tools**: Do not use a colon before a tool call (e.g., use "I will read the file." instead of "I will read the file:").
- **Accurate Reports**: If a task fails or tests fail, report it faithfully. Never claim "all tests pass" if the output shows otherwise.
"""

    def _get_action_care_guidelines(self) -> str:
        """Guidelines for safety and blast radius consideration."""
        return """
## EXECUTING ACTIONS WITH CARE
- **Measure Twice, Cut Once**: Never modify code you haven't read.
- **Adversarial Verification**: For any implementation involving logic changes (not just docs/style), you MUST use `delegate_mission(specialist_type='verifier')` to validate the work before declaring it finished.
- **Verification Evidence**: Do not accept "it works" as an answer. Require command output or screenshot evidence.
- **Atomic Commits**: If you have git access, favor small, logical commits over one giant dump.

## MISSION INTEGRITY & ANTI-LOOP
- **Task Perseverance**: DO NOT end the conversation or say "task complete" if the primary goal has not been reached. If a tool fails, find a different way (e.g., use a different search pattern, read a different file, or change your implementation approach).
- **Anti-Loop Strategy**: If you notice you are trying the same thing multiple times without success, you MUST change your strategy. Do not get stuck in a loop of repeating failed commands.
- **Exhaust All Avenues**: Before declaring a task impossible, you must have tried at least 3 different logical approaches.
- **No Early Exit**: Do not finish your thinking process until you have a concrete tool call or a final result that fulfills the user's original intent.
"""
