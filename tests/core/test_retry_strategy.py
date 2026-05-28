from mentask.core.retry_strategy import TimeoutContext, TimeoutRecoveryManager, TimeoutSeverity


def test_timeout_classification_network():
    ctx = TimeoutContext(error_msg="connection reset", provider="ollama", elapsed=5.0, attempt=1)

    assert ctx.classify() == TimeoutSeverity.NETWORK
    strategy = ctx.get_recovery_strategy()
    assert strategy["action"] == "retry_with_backoff"
    assert strategy["backoff_seconds"] > 0


def test_timeout_classification_model():
    ctx = TimeoutContext(error_msg="TimeoutError()", provider="ollama", elapsed=65.0, attempt=1)

    assert ctx.classify() == TimeoutSeverity.MODEL
    strategy = ctx.get_recovery_strategy()
    assert strategy["action"] == "reduce_context_and_retry"


def test_timeout_manager_metrics():
    mgr = TimeoutRecoveryManager()
    mgr.handle_timeout(Exception("connection error"), "test_provider", 2.0, 1)
    metrics = mgr.get_metrics()

    assert metrics["total_timeouts"] == 1
    assert metrics["timeouts_by_provider"]["test_provider"] == 1
