import logging
import re
from typing import Any

_logger = logging.getLogger("mentask")


class ContextCompressor:
    """Utility to compress prompt context by removing redundancies without losing semantic meaning."""

    @staticmethod
    def compress_text(text: str) -> str:
        """Compresses generic text by normalizing whitespace."""
        if not text:
            return ""
        # Remove comments from plain text too (heuristic)
        text = re.sub(r"(?m)^\s*#.*$", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        return text.strip()

    @staticmethod
    def _strip_python_comments(code: str) -> str:
        lines = []
        in_triple_double = False
        in_triple_single = False
        for line in code.splitlines():
            in_double = False
            in_single = False
            escaped = False
            comment_idx = -1
            i = 0
            while i < len(line):
                char = line[i]
                if escaped:
                    escaped = False
                    i += 1
                    continue
                if char == "\\":
                    escaped = True
                    i += 1
                    continue

                # Check triple quotes first
                if not in_single and not in_double:
                    if not in_triple_single and line[i:i+3] == '"""':
                        in_triple_double = not in_triple_double
                        i += 3
                        continue
                    if not in_triple_double and line[i:i+3] == "'''":
                        in_triple_single = not in_triple_single
                        i += 3
                        continue

                if not in_triple_double and not in_triple_single:
                    if char == '"' and not in_single:
                        in_double = not in_double
                    elif char == "'" and not in_double:
                        in_single = not in_single
                    elif char == "#" and not in_double and not in_single:
                        comment_idx = i
                        break
                i += 1

            if comment_idx != -1:
                line = line[:comment_idx].rstrip()
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _strip_js_comments(code: str) -> str:
        result = []
        i = 0
        in_string = None  # None, '"', "'", or '`'
        in_line_comment = False
        in_block_comment = False
        escaped = False

        while i < len(code):
            char = code[i]
            next_char = code[i+1] if i + 1 < len(code) else ""

            if in_line_comment:
                if char == "\n":
                    in_line_comment = False
                    result.append(char)
                i += 1
                continue

            if in_block_comment:
                if char == "*" and next_char == "/":
                    in_block_comment = False
                    i += 2
                else:
                    i += 1
                continue

            if escaped:
                escaped = False
                result.append(char)
                i += 1
                continue

            if char == "\\":
                escaped = True
                result.append(char)
                i += 1
                continue

            if in_string:
                if char == in_string:
                    in_string = None
                result.append(char)
                i += 1
                continue

            if char in ('"', "'", "`"):
                in_string = char
                result.append(char)
                i += 1
                continue

            if char == "/" and next_char == "/":
                in_line_comment = True
                i += 2
                continue

            if char == "/" and next_char == "*":
                in_block_comment = True
                i += 2
                continue

            result.append(char)
            i += 1

        return "".join(result)

    @staticmethod
    def compress_code(code: str, language: str = "") -> str:
        """Compresses code blocks by removing comments and unnecessary whitespace."""
        lang = language.lower()

        # Simple heuristic IF NOT "unknown"
        if not lang and "unknown" not in language.lower() and re.search(r"^\s*#", code, re.MULTILINE):
            # But wait, test_compress_code_unknown_language expects '#' to STAY if lang is empty or unknown
            pass

        if lang in ("python", "py"):
            code = ContextCompressor._strip_python_comments(code)
        elif lang in ("javascript", "js", "typescript", "ts", "java", "c", "cpp"):
            code = ContextCompressor._strip_js_comments(code)

        code = re.sub(r"\n{2,}", "\n", code)
        return code.strip()

    @classmethod
    def code_replacer(cls, match) -> str:
        lang = match.group(1) or ""
        body = match.group(2) or ""
        compressed_body = cls.compress_code(body, lang)
        return f"```{lang}\n{compressed_body}\n```"

    @classmethod
    def smart_compress(cls, content: str) -> str:
        """Detects if content is code or text and compresses accordingly."""
        # Check if it has markdown code blocks
        if "```" in content:
            compressed = re.sub(r"```(\w*)\n?(.*?)(?:```|$)", cls.code_replacer, content, flags=re.DOTALL)
            return compressed.strip()
        else:
            return cls.compress_text(content)


class ContextSnapper:
    """Orchestrates proactive context snapping (compaction) based on token thresholds."""

    MODEL_LIMITS = {
        "gemini-3.1-pro": 1_048_576,
        "gemini-3.1-flash": 1_048_576,
        "gemini-2.5-flash": 1_048_576,
        "gemini-2.0-flash": 1_000_000,
        "gemini-2.0-pro": 2_000_000,
        "gemini-1.5-flash": 1_000_000,
        "gemini-1.5-pro": 2_000_000,
        "default": 128_000,
    }

    def __init__(self, model_name: str, threshold_pct: float = 0.65):
        self.model_name = model_name
        self.threshold_pct = threshold_pct
        self.limit = self._get_model_limit(model_name)
        self.threshold = int(self.limit * threshold_pct)

    def _get_model_limit(self, model_name: str) -> int:
        from mentask.core.models_hub import hub

        # 1. Try to get from models.dev Hub
        info = hub.get_model(model_name)
        if info and info.get("context"):
            return int(info["context"])

        # 2. Fallback to hardcoded common limits
        for key, limit in self.MODEL_LIMITS.items():
            if key in model_name:
                return limit
        return self.MODEL_LIMITS["default"]

    def should_snap(self, current_tokens: int) -> bool:
        return current_tokens >= self.threshold

    def get_token_status(self, current_tokens: int) -> dict:
        pct = (current_tokens / self.limit) * 100
        return {
            "tokens": current_tokens,
            "limit": self.limit,
            "percentage": round(pct, 2),
            "is_dangerous": current_tokens > (self.limit * 0.90),
        }


class ContextCompactor:
    """Centralizes context compaction logic (history summarization and reconstruction)

    to avoid duplication between SessionManager and AgentOrchestrator.
    """

    @staticmethod
    def construct_compacted_history(
        system_messages: list[Any],
        summary_text: str,
        recent_files: list[str],
    ) -> list[Any]:
        """Constructs a new list of messages starting with system instructions,

        retaining project-local details and recent files context.
        """
        import os

        from mentask.agent.schema import Message, Role
        from mentask.core.summarizer import Summarizer

        formatted_summary = Summarizer.format_summary(summary_text)
        continuation_text = Summarizer.get_user_continuation_message(formatted_summary)

        # 1. Build new history starting with system messages
        new_history = [msg for msg in system_messages if msg.role == Role.SYSTEM]
        new_history.append(
            Message(
                role=Role.SYSTEM,
                content="[COMPACTION BOUNDARY] The previous conversation has been summarized to save tokens.",
            )
        )

        # 2. Append retained files context
        if recent_files:
            files_context = "\n\nRETAINED CONTEXT (Recent Files):\n"
            for path in recent_files:
                if os.path.exists(path):
                    try:
                        with open(path, encoding="utf-8") as f:
                            content = f.read()
                            if len(content) > 2000:
                                content = content[:2000] + "..."
                            files_context += f"\nFile: {path}\n```\n{content}\n```\n"
                    except (OSError, UnicodeDecodeError) as e:
                        _logger.warning(f"Failed to read recent file {path} for compaction: {e}")
            continuation_text += files_context

        # 3. Add continuation message
        new_history.append(Message(role=Role.USER, content=continuation_text))
        return new_history

