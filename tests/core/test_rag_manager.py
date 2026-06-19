import time

import pytest

from mentask.core.rag_manager import RAGManager


@pytest.mark.asyncio
async def test_rag_manager_hot_reload(tmp_path):
    # Setup test workspace files in the temporary directory
    file1 = tmp_path / "hello.txt"
    file1.write_text("Hello this is a test workspace file for semantic search.")

    rag = RAGManager(root_dir=str(tmp_path))

    # Query 1: should index workspace automatically and return results
    res1 = rag.query("semantic search", top_k=1)
    assert len(res1) == 1
    assert res1[0]["path"] == "hello.txt"
    assert "semantic search" in res1[0]["content"]

    # Verify that file metadata and mtime are recorded
    assert "hello.txt" in rag._file_mtimes
    original_mtime = rag._file_mtimes["hello.txt"]

    # Wait briefly to ensure file modification timestamp granularity differs
    time.sleep(0.1)

    # Modify the workspace file to include new concepts
    file1.write_text("This workspace file now talks about green pineapples and hot reloading.")

    # Query 2: searching for the new concepts should trigger automatic re-indexing
    res2 = rag.query("green pineapples", top_k=1)
    assert len(res2) == 1
    assert "green pineapples" in res2[0]["content"]
    assert rag._file_mtimes["hello.txt"] > original_mtime
