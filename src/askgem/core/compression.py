import re


class ContextCompressor:
    """Utility to compress prompt context by removing redundancies without losing semantic meaning."""

    @staticmethod
    def compress_text(text: str) -> str:
        """Compresses generic text by normalizing whitespace."""
        if not text:
            return ""
        # Remove repeated newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Collapse multiple spaces (excluding indentation if possible)
        text = re.sub(r" {2,}", " ", text)
        return text.strip()

    @staticmethod
    def compress_code(code: str, language: str = "") -> str:
        """Compresses code blocks by removing comments and unnecessary whitespace."""
        if language.lower() in ("python", "py"):
            # Remove python comments (simple regex, avoiding strings is hard without full parser)
            code = re.sub(r"(?m)^\s*#.*$", "", code)
        elif language.lower() in ("javascript", "js", "typescript", "ts", "java", "c", "cpp"):
            # Remove // comments
            code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
            # Remove /* */ comments
            code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)

        # Collapse multiple empty lines
        code = re.sub(r"\n{2,}", "\n", code)
        return code.strip()

    @classmethod
    def smart_compress(cls, content: str) -> str:
        """Detects if content is code or text and compresses accordingly.
        Often reduces token count by 30-50% in code-heavy prompts.
        """

        # Detect code blocks
        def code_replacer(match):
            lang = match.group(1) or ""
            body = match.group(2) or ""
            compressed_body = cls.compress_code(body, lang)
            return f"```{lang}\n{compressed_body}\n```"

        # Match ```lang ... ```
        compressed = re.sub(r"```(\w*)\n?(.*?)(?:```|$)", code_replacer, content, flags=re.DOTALL)

        # If no code blocks were found, compress as plain text
        if compressed == content:
            return cls.compress_text(content)

        return compressed
