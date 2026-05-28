from unittest.mock import patch

import pytest

from mentask.core.metrics import TokenTracker


@pytest.fixture
def clean_tracker():
    return TokenTracker(model_name="gemini-2.0-flash")


def test_tracker_initialization(clean_tracker):
    assert clean_tracker.total_prompt_tokens == 0
    assert clean_tracker.total_candidate_tokens == 0


def test_add_usage(clean_tracker):
    clean_tracker.add_usage(100, 50)
    assert clean_tracker.total_prompt_tokens == 100
    assert clean_tracker.total_candidate_tokens == 50

    clean_tracker.add_usage(200, 100)
    assert clean_tracker.total_prompt_tokens == 300
    assert clean_tracker.total_candidate_tokens == 150


def test_metrics_summary(clean_tracker):
    clean_tracker.add_usage(100, 50)
    summary = clean_tracker.get_summary()

    assert "Tokens:" in summary
    assert "Cost:" in summary


@patch("mentask.core.models_hub.hub.get_model")
@patch("mentask.core.models_hub.hub.get_pricing")
def test_calculate_cost(mock_get_pricing, mock_get_model, clean_tracker):
    """Verifies that calculate_cost works with hub pricing and falls back correctly."""
    tracker = clean_tracker

    # Scenario 1: Standard hub pricing
    mock_get_pricing.return_value = {"input": 1.0, "output": 2.0}
    mock_get_model.return_value = {"name": "Test Model"}

    # 1 million input tokens = $1.0
    # 2 million output tokens = $4.0
    # Total = $5.0
    cost = tracker.calculate_cost(1_000_000, 2_000_000)
    assert cost == 5.0
    mock_get_pricing.assert_called_with(tracker.model_name)

    # Scenario 2: Fallback to static PRICING_MAP when model not in hub
    mock_get_pricing.return_value = {"input": 0.0, "output": 0.0}
    mock_get_model.return_value = None

    # "gemini-2.0-flash" is in PRICING_MAP with input_1m=0.10, output_1m=0.40
    # 1 million input tokens = $0.10
    # 2 million output tokens = $0.80
    # Total = $0.90
    cost = tracker.calculate_cost(1_000_000, 2_000_000)
    assert cost == 0.90

    # Scenario 3: Fallback to default when model is unknown and not in hub
    tracker_unknown = TokenTracker(model_name="completely-unknown")
    mock_get_model.return_value = None
    mock_get_pricing.return_value = {"input": 0.0, "output": 0.0}

    # The default fallback in PRICING_MAP is "gemini-2.0-flash"
    # Wait, "completely-unknown" doesn't match any key, so it should use generic fallback
    # Generic fallback in my new code is {"input": 0.1, "output": 0.4}
    # 1 million input = 0.1, 2 million output = 0.8 -> Total 0.9
    cost_unknown = tracker_unknown.calculate_cost(1_000_000, 2_000_000)
    assert cost_unknown == 0.90

    # Scenario 4: Hub model with 0.0 cost (free model) - should NOT fallback
    mock_get_model.return_value = {"name": "Free Model", "cost": {"input": 0, "output": 0}}
    mock_get_pricing.return_value = {"input": 0.0, "output": 0.0}
    cost_free = tracker.calculate_cost(1_000_000, 2_000_000)
    assert cost_free == 0.0


def test_total_tokens(clean_tracker):
    """Verifies that total_tokens returns the sum of prompt and candidate tokens."""
    tracker = clean_tracker
    assert tracker.total_tokens == 0

    tracker.add_usage(100, 50)
    assert tracker.total_tokens == 150

    tracker.add_usage(200, 100)
    assert tracker.total_tokens == 450


@patch("os.remove")
@patch("os.path.exists")
@patch.object(TokenTracker, "_get_log_path", return_value="/fake/path/usage_log.json")
def test_reset_historical_file_exists(mock_get_log_path, mock_exists, mock_remove, clean_tracker):
    """Verifies that reset_historical removes log file when it exists and resets counters."""
    mock_exists.return_value = True

    clean_tracker.historical_prompt = 1000
    clean_tracker.historical_candidate = 500
    clean_tracker.total_saved_tokens = 200
    clean_tracker.total_prompt_tokens = 100
    clean_tracker.total_candidate_tokens = 50

    clean_tracker.reset_historical()

    mock_exists.assert_called_once_with("/fake/path/usage_log.json")
    mock_remove.assert_called_once_with("/fake/path/usage_log.json")

    assert clean_tracker.historical_prompt == 0
    assert clean_tracker.historical_candidate == 0
    assert clean_tracker.total_saved_tokens == 0
    assert clean_tracker.total_prompt_tokens == 0
    assert clean_tracker.total_candidate_tokens == 0


@patch("os.remove")
@patch("os.path.exists")
@patch.object(TokenTracker, "_get_log_path", return_value="/fake/path/usage_log.json")
def test_reset_historical_file_not_exists(mock_get_log_path, mock_exists, mock_remove, clean_tracker):
    """Verifies that reset_historical does not attempt to remove file when it doesn't exist and resets counters."""
    mock_exists.return_value = False

    clean_tracker.historical_prompt = 1000
    clean_tracker.historical_candidate = 500
    clean_tracker.total_saved_tokens = 200
    clean_tracker.total_prompt_tokens = 100
    clean_tracker.total_candidate_tokens = 50

    clean_tracker.reset_historical()

    mock_exists.assert_called_once_with("/fake/path/usage_log.json")
    mock_remove.assert_not_called()

    assert clean_tracker.historical_prompt == 0
    assert clean_tracker.historical_candidate == 0
    assert clean_tracker.total_saved_tokens == 0
    assert clean_tracker.total_prompt_tokens == 0
    assert clean_tracker.total_candidate_tokens == 0

def test_total_tokens_edge_cases(clean_tracker):
    tracker = clean_tracker
    assert tracker.total_tokens == 0

    # Test None defaults handled by add_usage
    tracker.add_usage(None, None)
    assert tracker.total_tokens == 0

    # Test adding 0
    tracker.add_usage(0, 0)
    assert tracker.total_tokens == 0

    # Test adding only prompt tokens
    tracker.add_usage(100, 0)
    assert tracker.total_tokens == 100

    # Test adding only candidate tokens
    tracker.add_usage(0, 50)
    assert tracker.total_tokens == 150


def test_add_savings(clean_tracker):
    tracker = clean_tracker
    tracker.reset_historical()  # ensure clean state
    assert tracker.total_saved_tokens == 0

    tracker.add_savings(500)
    assert tracker.total_saved_tokens == 500

    tracker.add_savings(250)
    assert tracker.total_saved_tokens == 750
