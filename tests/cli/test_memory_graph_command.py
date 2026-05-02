"""Tests for the Hermes Memory Graph slash command."""

from unittest.mock import MagicMock, patch


class TestHermesMemoryGraphCLICommand:
    def _make_cli(self):
        from cli import HermesCLI

        cli = HermesCLI.__new__(HermesCLI)
        cli.config = {}
        cli.console = MagicMock()
        cli.agent = None
        cli.conversation_history = []
        return cli

    def test_cli_command_prints_public_link(self):
        cli = self._make_cli()
        status = {
            "already_running": False,
            "public_dashboard_url": "https://reveals-sit-considering-edward.trycloudflare.com/dashboard.html",
            "local_dashboard_url": "http://127.0.0.1:9130/dashboard.html",
            "api_url": "http://127.0.0.1:9130/api/fact-graph",
        }

        with patch("hermes_cli.memory_graph.ensure_memory_graph_ready", return_value=status):
            result = cli.process_command("/Hermes-memory-graph")

        assert result is True
        cli.console.print.assert_called_once()
        printed = str(cli.console.print.call_args.args[0])
        assert "https://reveals-sit-considering-edward.trycloudflare.com/dashboard.html" in printed
        assert "http://127.0.0.1:9130/dashboard.html" in printed

    def test_telegram_alias_resolves(self):
        from hermes_cli.commands import resolve_command

        cmd = resolve_command("hermes_memory_graph")
        assert cmd is not None
        assert cmd.name == "hermes-memory-graph"
