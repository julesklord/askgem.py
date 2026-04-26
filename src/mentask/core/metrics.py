import json
import os
from dataclasses import dataclass

from .paths import get_config_path


@dataclass
class ModelPricing:
    """Pricing per 1 million tokens in USD."""

    input_1m: float
    output_1m: float


# Default pricing (approximate, based on standard Tier 1)
PRICING_MAP: dict[str, ModelPricing] = {
    "gemini-3.1-pro": ModelPricing(input_1m=2.00, output_1m=12.00),
    "gemini-3.1-flash": ModelPricing(input_1m=0.10, output_1m=0.40),
    "gemini-2.0-pro": ModelPricing(input_1m=3.50, output_1m=10.50),
    "gemini-2.0-flash": ModelPricing(input_1m=0.10, output_1m=0.40),
    "gemini-1.5-pro": ModelPricing(input_1m=1.25, output_1m=3.75),
    "gemini-1.5-flash": ModelPricing(input_1m=0.075, output_1m=0.30),
}


@dataclass
class TokenTracker:
    """Maintains token counts and cost estimates for a session and history."""

    model_name: str = "gemini-2.5-flash-lite"
    total_prompt_tokens: int = 0
    total_candidate_tokens: int = 0
    total_saved_tokens: int = 0  # Tokens saved via compaction

    def __post_init__(self):
        from .models_hub import hub

        hub.sync()  # Ensure cache is ready
        self._load_historical_usage()

    def _get_log_path(self) -> str:
        return get_config_path("usage_log.json")

    def _load_historical_usage(self):
        """Loads cumulative totals from the persistent log file."""
        path = self._get_log_path()
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    # We don't overwrite session tokens, but we keep these refs for historical reporting
                    self.historical_prompt = data.get("total_prompt", 0)
                    self.historical_candidate = data.get("total_candidate", 0)
                    self.total_saved_tokens = data.get("total_saved", 0)
            except Exception:
                self.historical_prompt = 0
                self.historical_candidate = 0
        else:
            self.historical_prompt = 0
            self.historical_candidate = 0
            self.total_saved_tokens = 0

    def _save_historical_usage(self, prompt_add: int, candidate_add: int, saved_add: int = 0):
        """Updates the persistent log file with new usage."""
        path = self._get_log_path()
        data = {"total_prompt": 0, "total_candidate": 0, "total_saved": 0}

        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        data["total_prompt"] = data.get("total_prompt", 0) + prompt_add
        data["total_candidate"] = data.get("total_candidate", 0) + candidate_add
        data["total_saved"] = data.get("total_saved", 0) + saved_add

        # Update our historical cache
        self.historical_prompt = data["total_prompt"]
        self.historical_candidate = data["total_candidate"]
        self.total_saved_tokens = data["total_saved"]

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def add_usage(self, prompt: int, candidates: int) -> None:
        """Accumulate usage from a single request and persist it."""
        p = prompt or 0
        c = candidates or 0
        self.total_prompt_tokens += p
        self.total_candidate_tokens += c
        self._save_historical_usage(p, c)

    def add_savings(self, tokens: int) -> None:
        """Log tokens saved via compaction."""
        self._save_historical_usage(0, 0, tokens)

    @property
    def total_tokens(self) -> int:
        return self.total_prompt_tokens + self.total_candidate_tokens

    def calculate_cost(self, prompt: int, candidate: int) -> float:
        """Returns the estimated cost in USD."""
        from .models_hub import hub

        pricing = hub.get_pricing(self.model_name)

        # Fallback to static PRICING_MAP if hub returns 0.0 (e.g. sync failed or model missing)
        if pricing["input"] == 0.0 and pricing["output"] == 0.0:
            base_model = self.model_name.split("/")[-1] if "/" in self.model_name else self.model_name
            static_pricing = next(
                (p for name, p in PRICING_MAP.items() if name in base_model), PRICING_MAP["gemini-2.0-flash"]
            )
            pricing = {"input": static_pricing.input_1m, "output": static_pricing.output_1m}

        input_cost = (prompt / 1_000_000) * pricing["input"]
        output_cost = (candidate / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def get_summary(self) -> str:
        """Returns a formatted summary for the TUI."""
        # Current Session
        cost = self.calculate_cost(self.total_prompt_tokens, self.total_candidate_tokens)
        session_line = (
            f"  [bold]Session Usage:[/]\n"
            f"  Tokens: [bold cyan]{self.total_tokens:,}[/bold cyan] "
            f"(In: {self.total_prompt_tokens:,} | Out: {self.total_candidate_tokens:,})\n"
            f"  Est. Cost: [bold green]${cost:.5f}[/bold green]\n"
        )

        # Global Cumulative
        hist = self.get_historical_report()
        global_line = (
            f"\n  [bold]Global Cumulative:[/]\n"
            f"  Total Tokens: [bold blue]{hist['total']:,}[/bold blue]\n"
            f"  Total Est. Cost: [bold green]${hist['cost']:.2f}[/bold green]\n"
            f"  Total Saved: [dim]{hist['saved_tokens']:,} tokens (~${hist['saved_cost']:.2f})[/dim]"
        )

        return session_line + global_line

    def get_historical_report(self) -> dict:
        """Returns full historical stats for audit."""
        total_p = getattr(self, "historical_prompt", 0)
        total_c = getattr(self, "historical_candidate", 0)
        cost = self.calculate_cost(total_p, total_c)
        saved_cost = self.calculate_cost(self.total_saved_tokens, 0)  # Estimates savings as input reduction

        return {
            "prompt": total_p,
            "candidate": total_c,
            "total": total_p + total_c,
            "cost": cost,
            "saved_tokens": self.total_saved_tokens,
            "saved_cost": saved_cost,
        }

    def reset(self) -> None:
        """Reset session metrics (historical remains)."""
        self.total_prompt_tokens = 0
        self.total_candidate_tokens = 0

    def reset_historical(self) -> None:
        """Wipes the persistent historical log."""
        path = self._get_log_path()
        if os.path.exists(path):
            os.remove(path)
        self.historical_prompt = 0
        self.historical_candidate = 0
        self.total_saved_tokens = 0
        self.reset()
