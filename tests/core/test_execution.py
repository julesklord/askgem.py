import asyncio

import pytest

from mentask.core.execution import BlockingOperationManager, OperationTimeout


@pytest.mark.asyncio
async def test_execution_timeout():
    mgr = BlockingOperationManager(global_timeout=1)

    async def slow_op():
        await asyncio.sleep(5)
        return "done"

    result = await mgr.execute_long_operation("test_op", "testing timeout", slow_op, timeout_seconds=1)
    assert isinstance(result, OperationTimeout)
    assert result.op_id == "test_op"


@pytest.mark.asyncio
async def test_execution_success():
    mgr = BlockingOperationManager(global_timeout=5)

    async def fast_op():
        await asyncio.sleep(0.1)
        return "success"

    result = await mgr.execute_long_operation("test_op", "testing success", fast_op, timeout_seconds=5)
    assert result == "success"
