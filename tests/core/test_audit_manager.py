from unittest.mock import patch

from rich.table import Table

from mentask.core.audit_manager import AuditManager


class TestAuditManager:
    @patch("mentask.core.audit_manager.MemoryManager")
    @patch("mentask.core.audit_manager.TokenTracker")
    def test_list_db(self, mock_tracker, mock_memory_manager):
        # Setup mock memory
        mock_memory = mock_memory_manager.return_value

        def mock_read_memory(scope):
            if scope == "global":
                return "## Global Cat\n- Fact 1\n- Fact 2\n"
            else:
                return "## Local Cat\n- Fact 3\n"

        mock_memory.read_memory.side_effect = mock_read_memory

        manager = AuditManager()

        table = manager.list_db()

        assert isinstance(table, Table)
        assert table.title == "[bold blue]mentask Knowledge DB[/bold blue]"

        columns = [c.header for c in table.columns]
        assert columns == ["Scope", "Category", "Fact"]

        # Check rows
        # Table.rows or list(table.columns[0].cells) ?
        # Rich tables don't easily expose rows as a simple list. We can check `list(table.columns[0].cells)`

        scopes = list(table.columns[0].cells)
        categories = list(table.columns[1].cells)
        facts = list(table.columns[2].cells)

        assert scopes == ["GLOBAL", "GLOBAL", "LOCAL"]
        assert categories == ["Global Cat", "Global Cat", "Local Cat"]
        assert facts == ["Fact 1", "Fact 2", "Fact 3"]

    @patch("mentask.core.audit_manager.MemoryManager")
    @patch("mentask.core.audit_manager.TokenTracker")
    def test_list_changelog_real_or_fallback(self, mock_tracker, mock_memory_manager):
        from rich.panel import Panel
        manager = AuditManager()
        panel = manager.list_changelog()
        assert isinstance(panel, Panel)
        assert panel.title == "[bold white]Changelog (Recent Changes)[/bold white]"

    @patch("mentask.core.audit_manager.MemoryManager")
    @patch("mentask.core.audit_manager.TokenTracker")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="## [0.99.0] - 2026-06-20\n\n### Added\n- Dynamic tests\n\n## [0.98.0]")
    def test_list_changelog_parsed(self, mock_read, mock_exists, mock_tracker, mock_memory_manager):
        from rich.panel import Panel
        manager = AuditManager()
        panel = manager.list_changelog()
        assert isinstance(panel, Panel)
        assert panel.title == "[bold white]Changelog (Recent Changes)[/bold white]"
        # The markdown rendering wraps the content, so we can verify the text inside the panel structure or render it
        # Just check that it succeeded and didn't crash.

