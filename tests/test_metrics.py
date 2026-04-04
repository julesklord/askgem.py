"""
Unit tests for the metrics tracking system (TokenTracker).
"""

from src.askgem.core.metrics import TokenTracker


def test_metrics_accumulation():
    """Verifies that tokens and costs accumulate correctly."""
    tracker = TokenTracker(model_name="gemini-1.5-flash")
    
    # 1. First turn: 100 prompt, 50 completion (Flash)
    tracker.add_usage(100, 50)
    
    assert tracker.total_prompt_tokens == 100
    assert tracker.total_candidate_tokens == 50
    assert tracker.calculate_cost() > 0
    
    # 2. Second turn: 200 prompt, 100 completion (Flash)
    tracker.add_usage(200, 100)
    
    assert tracker.total_prompt_tokens == 300
    assert tracker.total_candidate_tokens == 150


def test_metrics_pricing_difference():
    """Verifies that different models result in different costs."""
    tracker_flash = TokenTracker(model_name="gemini-1.5-flash")
    tracker_pro = TokenTracker(model_name="gemini-1.5-pro")
    
    tracker_flash.add_usage(1000, 1000)
    tracker_pro.add_usage(1000, 1000)
    
    # Pro should be more expensive than Flash
    assert tracker_pro.calculate_cost() > tracker_flash.calculate_cost()


def test_metrics_reset():
    """Verifies that metrics can be reset to zero."""
    tracker = TokenTracker()
    tracker.add_usage(100, 50)
    tracker.reset()
    
    assert tracker.total_prompt_tokens == 0
    assert tracker.calculate_cost() == 0.0


def test_metrics_summary():
    """Verifies the formatted summary string."""
    tracker = TokenTracker()
    tracker.add_usage(1000, 500)
    summary = tracker.get_summary()
    
    assert "Tokens:" in summary
    assert "Cost:" in summary
