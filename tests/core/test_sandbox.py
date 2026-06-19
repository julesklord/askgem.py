import pytest
from mentask.core.sandbox import LocalSandbox, SandboxManager, DockerSandbox


@pytest.mark.asyncio
async def test_local_sandbox_execution():
    manager = SandboxManager(config=None)
    assert isinstance(manager.sandbox, LocalSandbox)

    code, stdout, stderr = await manager.execute("echo 'hello'", timeout=5.0)
    assert code == 0
    assert stdout.strip() == "hello"
    assert stderr == ""


@pytest.mark.asyncio
async def test_local_sandbox_timeout():
    manager = SandboxManager(config=None)
    code, stdout, stderr = await manager.execute("sleep 10", timeout=0.1)
    assert code == -1
    assert "timed out" in stderr.lower()


@pytest.mark.asyncio
async def test_sandbox_manager_config():
    class MockConfig:
        settings = {"sandbox_mode": "docker", "sandbox_image": "python:3.11-slim"}

    manager = SandboxManager(config=MockConfig())
    assert isinstance(manager.sandbox, DockerSandbox)
    assert manager.sandbox.image == "python:3.11-slim"
