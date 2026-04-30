"""Tests for the Gemini CLI slash command and Hermes fallback."""

from queue import Queue
from unittest.mock import MagicMock, patch

from hermes_cli.gemini_cli import GeminiCliResult


class TestGeminiCLICommand:
    def _make_cli(self):
        from cli import HermesCLI

        cli = HermesCLI.__new__(HermesCLI)
        cli.config = {}
        cli.console = MagicMock()
        cli.agent = None
        cli.conversation_history = []
        cli._pending_input = Queue()
        return cli

    def test_cli_command_uses_gemini_when_available(self, capsys):
        cli = self._make_cli()
        result = GeminiCliResult(
            available=True,
            binary="/usr/bin/gemini",
            model="gemini-2.5-flash",
            prompt="Reply exactly: GEMINI_OK",
            output="GEMINI_OK",
            exit_code=0,
        )

        with patch("hermes_cli.gemini_cli.run_gemini_cli", return_value=result):
            handled = cli.process_command("/gemini-cli Reply exactly: GEMINI_OK")

        assert handled is True
        captured = capsys.readouterr().out
        assert "GEMINI_OK" in captured
        assert cli._pending_input.empty()

    def test_cli_command_falls_back_to_hermes_os_when_gemini_unavailable(self, capsys):
        cli = self._make_cli()
        result = GeminiCliResult(
            available=False,
            binary="",
            model="gemini-2.5-flash",
            prompt="Explain the change",
            reason="gemini binary not found",
            exit_code=None,
        )

        with patch("hermes_cli.gemini_cli.run_gemini_cli", return_value=result):
            handled = cli.process_command("/gemini_cli Explain the change")

        assert handled is True
        captured = capsys.readouterr().out
        assert "Falling back to Hermes OS native handling" in captured
        assert cli._pending_input.get_nowait() == "Explain the change"
