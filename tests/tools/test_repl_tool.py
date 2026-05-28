import pytest

from mentask.agent.tools.repl_tool import PythonReplTool


@pytest.fixture
def repl_tool():
    tool = PythonReplTool()
    yield tool
    tool.sandbox.close()


@pytest.mark.asyncio
async def test_repl_basic_execution(repl_tool):
    res = await repl_tool.execute("print('hello world')")
    assert not res.is_error
    assert res.content == "hello world\n"


@pytest.mark.asyncio
async def test_repl_state_persistence(repl_tool):
    await repl_tool.execute("x = 42")
    res = await repl_tool.execute("print(x * 2)")
    assert not res.is_error
    assert res.content == "84\n"


@pytest.mark.asyncio
async def test_repl_syntax_error(repl_tool):
    res = await repl_tool.execute("print('unclosed")
    assert res.is_error
    assert "SyntaxError" in res.content


@pytest.mark.asyncio
async def test_repl_security_os_system(repl_tool):
    res = await repl_tool.execute("import os\nos.system('echo hacked')")
    assert res.is_error
    assert "PermissionError" in res.content
    assert "os.system" in res.content


@pytest.mark.asyncio
async def test_repl_security_file_write(repl_tool):
    res = await repl_tool.execute("with open('hacked.txt', 'w') as f: f.write('hack')")
    assert res.is_error
    assert "PermissionError" in res.content
    assert "write access is forbidden" in res.content


@pytest.mark.asyncio
async def test_repl_security_subprocess(repl_tool):
    res = await repl_tool.execute("import subprocess\nsubprocess.Popen(['echo', 'hacked'])")
    assert res.is_error
    assert "PermissionError" in res.content
    assert "subprocess.Popen" in res.content


@pytest.mark.asyncio
async def test_repl_security_network(repl_tool):
    res = await repl_tool.execute("import urllib.request\nurllib.request.urlopen('http://google.com')")
    assert res.is_error
    assert "PermissionError" in res.content
    assert "Network access is forbidden" in res.content
