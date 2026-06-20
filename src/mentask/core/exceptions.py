"""exceptions.py — Custom exception hierarchy for the mentask agent."""


class MentaskError(Exception):
    """Base exception class for all mentask errors."""

    pass


class ConfigError(ValueError, MentaskError):
    """Exception raised for configuration errors (e.g., missing API keys, malformed JSON settings)."""

    pass


class SecurityError(PermissionError, MentaskError):
    """Exception raised for security violations (e.g., path traversal, blocked commands)."""

    pass


class ProviderError(RuntimeError, MentaskError):
    """Exception raised for provider-related errors (e.g., API limits, network timeouts)."""

    pass


class SandboxError(RuntimeError, MentaskError):
    """Exception raised for errors during sandbox execution."""

    pass
