import pytest
import os
from pathlib import Path
from src.askgem.agent.tools.file_tools import ListDirTool, ReadFileTool

@pytest.mark.asyncio
async def test_list_dir_tool(tmp_path):
    # Setup: Create a dummy directory structure
    d = tmp_path / "subdir"
    d.mkdir()
    (d / "file1.txt").write_text("hello")
    (d / "file2.py").write_text("print(1)")
    
    tool = ListDirTool()
    result = await tool.execute(path=str(d))
    
    assert not result.is_error
    assert "[FILE] file1.txt" in result.content
    assert "[FILE] file2.py" in result.content

@pytest.mark.asyncio
async def test_list_dir_not_found():
    tool = ListDirTool()
    result = await tool.execute(path="/path/that/does/not/exist/askgem")
    assert result.is_error
    assert "not a valid directory" in result.content

@pytest.mark.asyncio
async def test_read_file_tool(tmp_path):
    f = tmp_path / "test.txt"
    content = "Hello AskGem Port!"
    f.write_text(content)
    
    tool = ReadFileTool()
    result = await tool.execute(path=str(f))
    
    assert not result.is_error
    assert result.content == content

@pytest.mark.asyncio
async def test_read_file_not_found():
    tool = ReadFileTool()
    result = await tool.execute(path="non_existent_file.txt")
    assert result.is_error
    assert "not found" in result.content
