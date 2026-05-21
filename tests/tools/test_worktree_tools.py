import subprocess
import unittest
from unittest.mock import MagicMock, patch

from mentask.tools.worktree_tools import enter_worktree, exit_worktree


class TestWorktreeTools(unittest.TestCase):
    @patch("subprocess.run")
    @patch("subprocess.check_output")
    @patch("os.makedirs")
    @patch("os.chdir")
    @patch("os.getcwd")
    def test_enter_worktree_success(self, mock_getcwd, mock_chdir, mock_makedirs, mock_check_output, mock_run):
        # Mocking
        mock_run.side_effect = [
            MagicMock(stdout=""),  # git status
            MagicMock(),  # git rev-parse (branch exists)
            MagicMock(),  # git worktree add
        ]
        mock_check_output.return_value = "/repo/root"

        # Call
        result = enter_worktree("test-branch")

        # Verify
        self.assertIn("Success", result)
        self.assertIn("test-branch", result)
        mock_chdir.assert_called()

    @patch("subprocess.run")
    @patch("subprocess.check_output")
    @patch("os.chdir")
    @patch("os.getcwd")
    def test_exit_worktree_success(self, mock_getcwd, mock_chdir, mock_check_output, mock_run):
        # Mocking
        mock_getcwd.return_value = "/repo/root/.mentask/worktrees/test-branch"
        mock_check_output.return_value = "/repo/root"

        # Call
        result = exit_worktree()

        # Verify
        self.assertIn("Success", result)
        mock_chdir.assert_called_with("/repo/root")
        mock_run.assert_called()

    @patch("subprocess.run")
    def test_enter_worktree_dirty_dir(self, mock_run):
        mock_run.return_value = MagicMock(stdout=" M some_file.py")
        with self.assertRaisesRegex(RuntimeError, "working directory is dirty"):
            enter_worktree("test-branch")

    @patch("subprocess.run")
    @patch("subprocess.check_output")
    @patch("os.makedirs")
    @patch("os.chdir")
    @patch("os.getcwd")
    def test_enter_worktree_new_branch(self, mock_getcwd, mock_chdir, mock_makedirs, mock_check_output, mock_run):
        # Mocking
        mock_run.side_effect = [
            MagicMock(stdout=""),  # git status
            subprocess.CalledProcessError(1, "git rev-parse"),  # git rev-parse (branch doesn't exist)
            MagicMock(),  # git worktree add
        ]
        mock_check_output.return_value = "/repo/root"

        # Call
        result = enter_worktree("new-branch")

        # Verify
        self.assertIn("Success", result)
        self.assertIn("new-branch", result)
        mock_chdir.assert_called()

    @patch("subprocess.check_output")
    @patch("os.getcwd")
    def test_exit_worktree_already_at_root(self, mock_getcwd, mock_check_output):
        # Mocking
        mock_getcwd.return_value = "/repo/root"
        mock_check_output.return_value = "/repo/root"

        # Call & Verify
        with self.assertRaisesRegex(RuntimeError, "Already at repository root"):
            exit_worktree()


if __name__ == "__main__":
    unittest.main()
