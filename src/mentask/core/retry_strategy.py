import contextlib
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger("mentask.core.retry_strategy")

# Transient error patterns that should trigger retry
_TRANSIENT_PATTERNS = (
    "rate limit",
    "429",
    "503",
    "502",
    "500",
    "timeout",
    "connection",
    "network",
    "temporarily",
    "overloaded",
    "quota",
    "throttl",
    "econnreset",
    "econnrefused",
)


def parse_rate_limit_headers(headers: dict[str, str]) -> dict[str, Any]:
    """Parse rate limit headers from API responses.

    Recognizes common rate limit header formats:
    - X-RateLimit-Reset: epoch timestamp or seconds
    - Retry-After: seconds or HTTP-date
    - X-RateLimit-Remaining: remaining requests

    Returns dict with 'retry_after' (seconds), 'remaining' (int or None),
    and 'reset_at' (epoch float or None).
    """
    result: dict[str, Any] = {"retry_after": None, "remaining": None, "reset_at": None}

    # Retry-After (most reliable)
    retry_after = headers.get("Retry-After") or headers.get("retry-after")
    if retry_after:
        with contextlib.suppress(ValueError):
            result["retry_after"] = max(int(retry_after), 1)

    # X-RateLimit-Remaining
    remaining = headers.get("X-RateLimit-Remaining") or headers.get("x-ratelimit-remaining")
    if remaining:
        with contextlib.suppress(ValueError):
            result["remaining"] = int(remaining)

    # X-RateLimit-Reset (epoch seconds)
    reset = headers.get("X-RateLimit-Reset") or headers.get("x-ratelimit-reset")
    if reset:
        with contextlib.suppress(ValueError):
            result["reset_at"] = float(reset)

    # Auto-compute retry_after from reset_at if not provided
    if result["reset_at"] and not result["retry_after"]:
        import time

        wait = max(result["reset_at"] - time.time(), 1)
        result["retry_after"] = min(int(wait), 120)  # Cap at 2 minutes

    return result


class TimeoutSeverity(Enum):
    NETWORK = "network"
    MODEL = "model"
    API_TRANSIENT = "api_transient"
    UNKNOWN = "unknown"


@dataclass
class TimeoutContext:
    elapsed: float
    attempt: int
    max_attempts: int = 3
    error_msg: str = ""
    provider: str = "unknown"

    def classify(self) -> TimeoutSeverity:
        msg_lower = self.error_msg.lower()

        # Long-running timeouts are model-level (needs context reduction)
        if self.elapsed > 60:
            return TimeoutSeverity.MODEL

        # Network-level issues
        if any(pat in msg_lower for pat in ("connection", "network", "econnreset", "econnrefused")):
            return TimeoutSeverity.NETWORK

        # Transient API errors (rate limits, server errors)
        if any(pat in msg_lower for pat in _TRANSIENT_PATTERNS):
            return TimeoutSeverity.API_TRANSIENT

        return TimeoutSeverity.UNKNOWN

    def get_recovery_strategy(self) -> dict[str, Any]:
        severity = self.classify()

        if severity == TimeoutSeverity.NETWORK:
            return {
                "action": "retry_with_backoff",
                "backoff_seconds": 2 ** self.attempt,
                "max_retries": self.max_attempts,
            }
        elif severity == TimeoutSeverity.API_TRANSIENT:
            # Exponential backoff with jitter for rate limits and server errors
            base_wait = min(2 ** self.attempt, 30)  # Cap at 30s
            return {
                "action": "retry_with_backoff",
                "backoff_seconds": base_wait,
                "max_retries": self.max_attempts,
                "reason": "transient_api_error",
            }
        elif severity == TimeoutSeverity.MODEL:
            return {
                "action": "reduce_context_and_retry",
                "compression": "aggressive",
                "fallback_model": "qwen2.5-7b",
                "timeout_seconds": 30,
            }
        else:
            return {
                "action": "simple_retry",
                "timeout_seconds": 45,
                "retries_left": self.max_attempts - self.attempt,
            }


class TimeoutRecoveryManager:
    def __init__(self, max_global_attempts: int = 3):
        self.max_global_attempts = max_global_attempts
        self.timeout_history: list[TimeoutContext] = []
        self.metrics_reporter: dict[str, Any] = {
            "total_timeouts": 0,
            "timeouts_by_provider": {},
            "timeouts_by_severity": {},
            "successful_recoveries": 0,
            "failed_recoveries": 0,
        }

    def get_metrics(self) -> dict[str, Any]:
        return dict(self.metrics_reporter)

    def handle_timeout(self, error: Exception, provider: str, elapsed: float, current_attempt: int) -> dict[str, Any]:
        ctx = TimeoutContext(
            elapsed=elapsed,
            attempt=current_attempt,
            max_attempts=self.max_global_attempts,
            error_msg=str(error),
            provider=provider,
        )

        self.timeout_history.append(ctx)
        strategy = ctx.get_recovery_strategy()

        # Update metrics
        self.metrics_reporter["total_timeouts"] += 1
        self.metrics_reporter["timeouts_by_provider"][provider] = (
            self.metrics_reporter["timeouts_by_provider"].get(provider, 0) + 1
        )
        sev = ctx.classify().value
        self.metrics_reporter["timeouts_by_severity"][sev] = (
            self.metrics_reporter["timeouts_by_severity"].get(sev, 0) + 1
        )

        logger.warning(
            "Timeout in %s (attempt %d/%d): %.1fs - Strategy: %s",
            provider,
            current_attempt,
            self.max_global_attempts,
            elapsed,
            strategy["action"],
        )

        return strategy
