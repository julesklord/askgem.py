"""
Token and Cost tracking for AskGem sessions.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ModelPricing:
    """Pricing per 1 million tokens in USD."""

    input_1m: float
    output_1m: float


# Default pricing (approximate, based on standard Tier 1)
PRICING_MAP: Dict[str, ModelPricing] = {
    "gemini-2.5-flash": ModelPricing(input_1m=0.10, output_1m=0.40),
    "gemini-2.5-pro": ModelPricing(input_1m=3.50, output_1m=10.50),
    "gemini-2.0-flash": ModelPricing(input_1m=0.10, output_1m=0.40),
    "gemini-2.0-pro": ModelPricing(input_1m=3.50, output_1m=10.50),
    "gemini-1.5-flash": ModelPricing(input_1m=0.075, output_1m=0.30),
    "gemini-1.5-pro": ModelPricing(input_1m=1.25, output_1m=3.75),
}


@dataclass
class TokenTracker:
    """Maintains token counts and cost estimates for a session."""

    model_name: str = "gemini-2.0-flash"
    total_prompt_tokens: int = 0
    total_candidate_tokens: int = 0

    def add_usage(self, prompt: int, candidates: int) -> None:
        """Accumulate usage from a single request.
        
        Args:
            prompt: The number of tokens consumed by the prompt.
            candidates: The number of tokens generated in the response.
        """
        self.total_prompt_tokens += prompt or 0
        self.total_candidate_tokens += candidates or 0

    @property
    def total_tokens(self) -> int:
        """Returns the combined sum of prompt and candidate tokens.
        
        Returns:
            int: Total token count.
        """
        return self.total_prompt_tokens + self.total_candidate_tokens

    def calculate_cost(self) -> float:
        """Returns the estimated cost in USD.
        
        Returns:
            float: The calculated cost based on active pricing map.
        """
        # Strip generation/version markers if present for mapping
        base_model = self.model_name.split("/")[-1] if "/" in self.model_name else self.model_name
        # Match partial names if exact match fails
        pricing = next((p for name, p in PRICING_MAP.items() if name in base_model), PRICING_MAP["gemini-2.0-flash"])

        input_cost = (self.total_prompt_tokens / 1_000_000) * pricing.input_1m
        output_cost = (self.total_candidate_tokens / 1_000_000) * pricing.output_1m
        return input_cost + output_cost

    def get_summary(self) -> str:
        """Returns a formatted summary for the TUI.
        
        Returns:
            str: The summary string with Rich formatting markup.
        """
        cost = self.calculate_cost()
        return (
            f"Tokens: [bold cyan]{self.total_tokens:,}[/bold cyan] "
            f"(In: {self.total_prompt_tokens:,} | Out: {self.total_candidate_tokens:,}) "
            f"Est. Cost: [bold green]${cost:.4f}[/bold green]"
        )

    def reset(self) -> None:
        """Reset session metrics."""
        self.total_prompt_tokens = 0
        self.total_candidate_tokens = 0
