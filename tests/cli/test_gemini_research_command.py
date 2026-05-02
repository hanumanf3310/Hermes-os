"""Tests for the Gemini research workflow slash command."""

from queue import Queue
from unittest.mock import MagicMock, patch

from hermes_cli.gemini_cli import GeminiCliResult
from hermes_cli.gemini_workflow import GeminiWorkflowResult


class TestGeminiResearchCommand:
    def _make_cli(self):
        from cli import HermesCLI

        cli = HermesCLI.__new__(HermesCLI)
        cli.config = {}
        cli.console = MagicMock()
        cli.agent = None
        cli.conversation_history = []
        cli._pending_input = Queue()
        return cli

    def test_cli_command_runs_workflow_and_queues_verification_prompt(self, capsys):
        cli = self._make_cli()
        workflow_result = GeminiWorkflowResult(
            available=True,
            question="What changed?",
            evidence="docs updated\ncommand added",
            summary="summary: docs updated\nclaims: - command added\nassumptions: none\nverification_risk: low",
            verification_prompt="Verify the Gemini summary against the evidence.",
            reason="",
            binary="/usr/bin/gemini",
            model="gemini-2.5-flash",
            exit_code=0,
        )

        with patch("hermes_cli.gemini_workflow.run_gemini_research_workflow", return_value=workflow_result):
            handled = cli.process_command(
                '/gemini-research --question "What changed?" --evidence "docs updated\ncommand added"'
            )

        assert handled is True
        captured = capsys.readouterr().out
        assert "Gemini workflow summary" in captured
        assert "summary: docs updated" in captured
        assert cli._pending_input.get_nowait() == workflow_result.verification_prompt

    def test_cli_command_falls_back_to_hermes_when_gemini_unavailable(self, capsys):
        cli = self._make_cli()
        workflow_result = GeminiWorkflowResult(
            available=False,
            question="What changed?",
            evidence="docs updated\ncommand added",
            reason="gemini binary not found",
            fallback_prompt="Gemini CLI is unavailable. Hermes OS should answer natively using the evidence below.",
            binary="",
            model="gemini-2.5-flash",
            exit_code=None,
        )

        with patch("hermes_cli.gemini_workflow.run_gemini_research_workflow", return_value=workflow_result):
            handled = cli.process_command(
                '/gemini-research --question "What changed?" --evidence "docs updated\ncommand added"'
            )

        assert handled is True
        captured = capsys.readouterr().out
        assert "Gemini workflow fallback to Hermes OS" in captured
        assert cli._pending_input.get_nowait() == workflow_result.fallback_prompt
