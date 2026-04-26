import logging
import re

_logger = logging.getLogger("mentask")


class ContextCompressor:
    """Utility to compress prompt context by removing redundancies without losing semantic meaning."""

    @staticmethod
    def compress_text(text: str) -> str:
        """Compresses generic text by normalizing whitespace."""
        if not text:
            return ""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        return text.strip()

    @staticmethod
    def compress_code(code: str, language: str = "") -> str:
        """Compresses code blocks by removing comments and unnecessary whitespace."""
        if language.lower() in ("python", "py"):
            code = re.sub(r"(?m)^\s*#.*$", "", code)
        elif language.lower() in ("javascript", "js", "typescript", "ts", "java", "c", "cpp"):
            code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
            code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        code = re.sub(r"\n{2,}", "\n", code)
        return code.strip()

    @classmethod
    def smart_compress(cls, content: str) -> str:
        """Detects if content is code or text and compresses accordingly."""

        def code_replacer(match):
            lang = match.group(1) or ""
            body = match.group(2) or ""
            compressed_body = cls.compress_code(body, lang)
            return f"```{lang}\n{compressed_body}\n```"

        compressed = re.sub(r"```(\w*)\n?(.*?)(?:```|$)", code_replacer, content, flags=re.DOTALL)
        if compressed == content:
            return cls.compress_text(content)
        return compressed


class ContextSnapper:
    """
    Orchestrates proactive context snapping (compaction) based on token thresholds.
    """

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
