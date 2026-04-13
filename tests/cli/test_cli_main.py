from unittest.mock import MagicMock, patch

from askgem.cli.main import run_chatbot


def test_run_chatbot_legacy():
    with patch("askgem.cli.main.argparse.ArgumentParser.parse_args") as mock_parse_args, \
         patch("askgem.agent.chat.ChatAgent") as mock_agent_class, \
         patch("askgem.cli.console.console") as mock_console, \
         patch("asyncio.run") as mock_asyncio_run, \
         patch("askgem.core.i18n.get_current_language", return_value="en"):

        mock_args = MagicMock()
        mock_args.legacy = True
        mock_parse_args.return_value = mock_args

        mock_instance = MagicMock()
        mock_instance.model_name = "test-model"
        mock_instance.edit_mode = "test-mode"
        mock_agent_class.return_value = mock_instance

        run_chatbot()

        mock_agent_class.assert_called_once()
        mock_console.print.assert_called()
        mock_asyncio_run.assert_called_once_with(mock_instance.start())

def test_run_chatbot_dashboard():
    with patch("askgem.cli.main.argparse.ArgumentParser.parse_args") as mock_parse_args, \
         patch("askgem.agent.chat.ChatAgent") as mock_agent_class:

        mock_args = MagicMock()
        mock_args.legacy = False
        mock_parse_args.return_value = mock_args

        mock_instance = MagicMock()
        mock_agent_class.return_value = mock_instance

        mock_dashboard_class = MagicMock()
        mock_dashboard = MagicMock()
        mock_dashboard_class.return_value = mock_dashboard

        # Use sys.modules patching instead of monkeypatching __import__
        fake_module = MagicMock()
        fake_module.AskGemDashboard = mock_dashboard_class

        # Patch the absolute module paths
        with patch.dict('sys.modules', {
            'askgem.cli.dashboard': fake_module,
            'askgem.cli.main.dashboard': fake_module
        }):
            run_chatbot()

        mock_agent_class.assert_called_once()
        mock_dashboard_class.assert_called_once_with(agent=mock_instance)
        mock_dashboard.run.assert_called_once()

def test_run_chatbot_dashboard_fallback():
    with patch("askgem.cli.main.argparse.ArgumentParser.parse_args") as mock_parse_args, \
         patch("askgem.agent.chat.ChatAgent") as mock_agent_class, \
         patch("askgem.cli.console.console") as mock_console, \
         patch("asyncio.run") as mock_asyncio_run:

        mock_args = MagicMock()
        mock_args.legacy = False
        mock_parse_args.return_value = mock_args

        mock_instance = MagicMock()
        mock_agent_class.return_value = mock_instance

        # We simulate ImportError when attempting to import AskGemDashboard by setting module to None
        with patch.dict('sys.modules', {'askgem.cli.dashboard': None}):
            # But we also have to mock builtins.__import__ because `from .dashboard import AskGemDashboard`
            # uses importlib logic that might still crash when sys.modules has None, so we patch `__import__` safely
            import builtins
            real_import = builtins.__import__
            def safe_mock_import(name, globals=None, locals=None, fromlist=(), level=0):
                if name == '.dashboard' or name == 'askgem.cli.dashboard' or 'dashboard' in name:
                    raise ImportError("Dashboard not implemented yet")
                return real_import(name, globals, locals, fromlist, level)

            with patch('builtins.__import__', side_effect=safe_mock_import):
                run_chatbot()

        mock_agent_class.assert_called_once()
        mock_console.print.assert_called_with("[warning]Dashboard not implemented yet. Falling back to --legacy...[/warning]")
        mock_asyncio_run.assert_called_once_with(mock_instance.start())
