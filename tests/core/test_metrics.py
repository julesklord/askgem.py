from unittest.mock import patch

import pytest

from mentask.core.metrics import TokenTracker


@pytest.fixture
def clean_tracker(tmp_path):
    # Mock the log path to use a temp file
    log_file = tmp_path / "test_usage.json"
    with patch("mentask.core.metrics.get_config_path", return_value=str(log_file)):
        yield TokenTracker(model_name="gemini-2.0-flash")


def test_metrics_accumulation(clean_tracker):
    """Verifies that tokens and costs accumulate correctly."""
    tracker = clean_tracker
    tracker.add_usage(100, 50)

    assert tracker.total_prompt_tokens == 100
    assert tracker.total_candidate_tokens == 50
    # calculate_cost now requires arguments
    assert tracker.calculate_cost(100, 50) > 0

    tracker.add_usage(200, 100)
    assert tracker.total_prompt_tokens == 300
    assert tracker.total_candidate_tokens == 150


def test_metrics_pricing_difference(tmp_path):
    """Verifies that different models result in different costs."""
    log_file = tmp_path / "test_usage_pricing.json"
    with patch("mentask.core.metrics.get_config_path", return_value=str(log_file)):
        tracker_flash = TokenTracker(model_name="gemini-1.5-flash")
        tracker_pro = TokenTracker(model_name="gemini-1.5-pro")

        # Pro should be more expensive than Flash for the same usage
        cost_flash = tracker_flash.calculate_cost(1000, 1000)
        cost_pro = tracker_pro.calculate_cost(1000, 1000)
        assert cost_pro > cost_flash


def test_metrics_reset(clean_tracker):
    """Verifies that metrics can be reset to zero."""
    tracker = clean_tracker
    tracker.add_usage(100, 50)
    tracker.reset()

    assert tracker.total_prompt_tokens == 0
    assert tracker.calculate_cost(tracker.total_prompt_tokens, tracker.total_candidate_tokens) == 0.0


def test_metrics_summary(clean_tracker):
    """Verifies the formatted summary string."""
    tracker = clean_tracker
    tracker.add_usage(1000, 500)
    summary = tracker.get_summary()

    assert "Tokens:" in summary
    assert "Cost:" in summary
