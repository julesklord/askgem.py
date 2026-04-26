from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from mentask.cli.main import _parse_args, run_chatbot


def test_parse_args_accepts_list_option(monkeypatch):
    monkeypatch.setattr("sys.argv", ["mentask", "--list", "all"])

    args = _parse_args()

    assert args == Namespace(list="all", session_id=None)


def test_parse_args_rejects_invalid_list_value(monkeypatch):
    monkeypatch.setattr("sys.argv", ["mentask", "--list", "invalid"])

    with pytest.raises(SystemExit):
        _parse_args()


def test_run_chatbot_starts_agent_when_no_list_requested():
    with (
        patch("mentask.cli.main._parse_args", return_value=Namespace(list=None, session_id="test_session")),
        patch("mentask.cli.main._run_async_chatbot") as mock_run_async,
        patch("asyncio.run") as mock_asyncio_run,
    ):
        run_chatbot()

    mock_asyncio_run.assert_called_once()
    mock_run_async.assert_called_once()
    args = mock_run_async.call_args[0][0]
    assert args.session_id == "test_session"


def test_run_chatbot_lists_requested_audit_section():
    with (
        patch("mentask.cli.main._parse_args", return_value=Namespace(list="sessions", session_id=None)),
        patch("mentask.cli.console.console") as mock_console,
        patch("mentask.core.audit_manager.AuditManager") as mock_audit_class,
        patch("mentask.agent.chat.ChatAgent") as mock_agent_class,
    ):
        mock_audit = MagicMock()
        mock_audit.list_sessions.return_value = "session data"
        mock_audit_class.return_value = mock_audit

        run_chatbot()

    mock_audit_class.assert_called_once_with()
    mock_audit.list_sessions.assert_called_once_with()
    mock_agent_class.assert_not_called()
    assert mock_console.print.call_count == 3
    mock_console.print.assert_any_call("session data")


def test_run_chatbot_lists_all_audit_sections():
    with (
        patch("mentask.cli.main._parse_args", return_value=Namespace(list="all", session_id=None)),
        patch("mentask.cli.console.console") as mock_console,
        patch("mentask.core.audit_manager.AuditManager") as mock_audit_class,
    ):
        mock_audit = MagicMock()
        mock_audit.list_db.return_value = "db"
        mock_audit.list_home.return_value = "home"
        mock_audit.list_sessions.return_value = "sessions"
        mock_audit.list_spend.return_value = "spend"
        mock_audit.list_changelog.return_value = "changelog"
        mock_audit_class.return_value = mock_audit

        run_chatbot()

    mock_audit.list_db.assert_called_once_with()
    mock_audit.list_home.assert_called_once_with()
    mock_audit.list_sessions.assert_called_once_with()
    mock_audit.list_spend.assert_called_once_with()
    mock_audit.list_changelog.assert_called_once_with()
    assert mock_console.print.call_count == 7
