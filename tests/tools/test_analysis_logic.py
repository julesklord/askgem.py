"""
Tests for tools/analysis_logic.py
"""
from unittest.mock import patch

from mentask.tools.analysis_logic import get_git_diff_stat


class TestGetGitDiffStat:
    @patch("subprocess.run")
    def test_get_git_diff_stat_success(self, mock_run):
        """Test get_git_diff_stat with changes detected."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = " file1.py | 10 +++++++++-\n 1 file changed, 9 insertions(+), 1 deletion(-)\n"

        result = get_git_diff_stat()

        mock_run.assert_called_once_with(["git", "diff", "--stat", "HEAD"], capture_output=True, text=True, check=False)
        assert "file1.py" in result
        assert "1 file changed" in result

    @patch("subprocess.run")
    def test_get_git_diff_stat_no_changes(self, mock_run):
        """Test get_git_diff_stat when no changes are detected (empty stdout)."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""

        result = get_git_diff_stat()

        mock_run.assert_called_once_with(["git", "diff", "--stat", "HEAD"], capture_output=True, text=True, check=False)
        assert result == "No changes detected via git diff."

    @patch("subprocess.run")
    def test_get_git_diff_stat_failure(self, mock_run):
        """Test get_git_diff_stat when the git command fails."""
        mock_run.return_value.returncode = 128
        mock_run.return_value.stderr = "fatal: not a git repository"

        result = get_git_diff_stat()

        mock_run.assert_called_once_with(["git", "diff", "--stat", "HEAD"], capture_output=True, text=True, check=False)
        assert "Error: Git diff failed" in result
        assert "fatal: not a git repository" in result

    @patch("subprocess.run")
    def test_get_git_diff_stat_exception(self, mock_run):
        """Test get_git_diff_stat when subprocess.run raises an exception."""
        mock_run.side_effect = FileNotFoundError("No such file or directory: 'git'")

        result = get_git_diff_stat()

        mock_run.assert_called_once_with(["git", "diff", "--stat", "HEAD"], capture_output=True, text=True, check=False)
        assert "Error executing git:" in result
        assert "No such file or directory" in result
