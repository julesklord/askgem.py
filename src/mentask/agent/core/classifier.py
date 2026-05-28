import logging

from ..schema import EngineeringLevel

_logger = logging.getLogger("mentask")

CLASSIFICATION_PROMPT = """
Analyze the following USER REQUEST and classify it into one of four Engineering Levels:

- L0_INQUIRY: Pure questions, requests for information, or general discussion where NO CODE CHANGES or system actions are needed.
- L1_PRAGMATIC: Simple technical tasks, single-file scripts, file lookups, or straightforward commands.
- L2_STANDARD: Feature development, multi-file changes, bug fixes requiring research, or new logic implementation.
- L3_ARCHITECT: Core refactoring, architectural changes, complex migrations, or tasks affecting the entire system.

Respond ONLY with the level key (e.g., L1_PRAGMATIC).

USER REQUEST: {prompt}
"""

# Providers that cannot be used for fast sidechain calls (no streaming JSON API).
# These get a heuristic classification instead.
_SIDECHAIN_INCAPABLE_PROVIDERS = ("CLIProvider",)


def _heuristic_classify(prompt: str) -> EngineeringLevel:
    """Fast regex-free heuristic for providers that can't handle sidechain calls."""
    p = prompt.lower()

    # L0: questions / greetings
    q_signals = ("?", "what is", "how does", "explain", "tell me", "who is", "saludos", "hello", "hi ")
    if any(p.startswith(s) or s in p for s in q_signals) and len(p) < 200:
        return EngineeringLevel.L0_INQUIRY

    # L3: architectural signals
    arch_signals = ("refactor", "migrate", "redesign", "overhaul", "rewrite", "architecture", "restructure")
    if any(s in p for s in arch_signals):
        return EngineeringLevel.L3_ARCHITECT

    # L1: simple single-action signals
    simple_signals = ("list", "show", "read file", "print", "cat ", "ls ", "find ", "grep ")
    if any(p.startswith(s) or s in p for s in simple_signals):
        return EngineeringLevel.L1_PRAGMATIC

    return EngineeringLevel.L2_STANDARD


class TaskClassifier:
    def __init__(self, provider):
        self.provider = provider

    def _provider_supports_sidechain(self) -> bool:
        """Returns False for providers that can't handle quick sidechain classification calls."""
        try:
            # ProviderManager wraps a SessionManager (self.provider.client)
            # SessionManager has a .provider attribute pointing to the actual BaseProvider subclass
            actual_provider = getattr(self.provider, "client", None)
            if actual_provider is not None:
                actual_provider = getattr(actual_provider, "provider", actual_provider)
            provider_class = type(actual_provider).__name__
            return provider_class not in _SIDECHAIN_INCAPABLE_PROVIDERS
        except Exception:
            return True  # Assume capable on error; worst case: warning log + L2 default

    async def classify(self, prompt: str, config=None) -> EngineeringLevel:
        # Fast path: heuristic for CLI and other non-sidechain-capable providers
        if not self._provider_supports_sidechain():
            level = _heuristic_classify(prompt)
            _logger.debug(f"Heuristic classification (CLI bridge): {level.value}")
            return level

        try:
            # We use a non-streaming turn for a quick classification
            from ..schema import Message, Role

            messages = [Message(role=Role.USER, content=CLASSIFICATION_PROMPT.format(prompt=prompt))]

            # Use a copy of config to limit output tokens for speed
            import copy

            fast_config = copy.copy(config) if config else {}
            if isinstance(fast_config, dict):
                fast_config["max_output_tokens"] = 10
            elif hasattr(fast_config, "max_output_tokens"):
                fast_config.max_output_tokens = 10

            raw_response = ""
            async for event in self.provider.stream_turn(messages, [], config=fast_config):
                if event["type"] == "text":
                    raw_response += event["content"]

            raw_response = raw_response.strip().upper()

            if "L3" in raw_response:
                return EngineeringLevel.L3_ARCHITECT
            elif "L2" in raw_response:
                return EngineeringLevel.L2_STANDARD
            elif "L1" in raw_response:
                return EngineeringLevel.L1_PRAGMATIC
            elif "L0" in raw_response:
                return EngineeringLevel.L0_INQUIRY

            _logger.warning(f"Unexpected classification response: {raw_response}. Defaulting to L2.")
            return EngineeringLevel.L2_STANDARD

        except Exception as e:
            _logger.error(f"Task classification failed: {e}")
            return EngineeringLevel.L2_STANDARD
