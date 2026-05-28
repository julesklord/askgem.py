import pytest

from mentask.agent.core.classifier import TaskClassifier
from mentask.agent.schema import EngineeringLevel


class MockProvider:
    def __init__(self, response_text):
        self.response_text = response_text

    async def stream_turn(self, messages, tools, config=None):
        yield {"type": "text", "content": self.response_text}


@pytest.mark.asyncio
async def test_classify_l1():
    provider = MockProvider("L1_PRAGMATIC")
    classifier = TaskClassifier(provider)
    level = await classifier.classify("make a simple script")
    assert level == EngineeringLevel.L1_PRAGMATIC


@pytest.mark.asyncio
async def test_classify_l2():
    provider = MockProvider("L2_STANDARD")
    classifier = TaskClassifier(provider)
    level = await classifier.classify("fix a bug in the orchestrator")
    assert level == EngineeringLevel.L2_STANDARD


@pytest.mark.asyncio
async def test_classify_l3():
    provider = MockProvider("L3_ARCHITECT")
    classifier = TaskClassifier(provider)
    level = await classifier.classify("refactor the whole project architecture")
    assert level == EngineeringLevel.L3_ARCHITECT


@pytest.mark.asyncio
async def test_classify_fallback():
    provider = MockProvider("I don't know")
    classifier = TaskClassifier(provider)
    level = await classifier.classify("something weird")
    assert level == EngineeringLevel.L2_STANDARD
