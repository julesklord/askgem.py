from unittest.mock import MagicMock, patch

import pytest

from mentask.tools.worktree_tools import enter_worktree


class TestEnterWorktree:
    def test_dirty_directory_raises_error(self):
        with patch("subprocess.run") as mock_run:
            # Mock the return value of git status --porcelain
            mock_run.return_value = MagicMock(stdout=" M some_file.py\n")

            with pytest.raises(RuntimeError) as exc_info:
                enter_worktree("test-branch")

            assert "The working directory is dirty" in str(exc_info.value)
            # Verify subprocess.run was called with correct arguments
            mock_run.assert_called_once_with(
                ["git", "status", "--porcelain"], capture_output=True, text=True, check=False
            )
