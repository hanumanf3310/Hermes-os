"""Tests for the checkpoint / go-no-go command."""

from unittest.mock import MagicMock, patch

from hermes_cli.checkpoint_gate import (
    CheckpointRequest,
    format_checkpoint_result,
    parse_checkpoint_request,
    run_checkpoint_gate,
)
from hermes_cli.commands import resolve_command


class TestCheckpointCommand:
    def _make_cli(self):
        from cli import HermesCLI

        cli = HermesCLI.__new__(HermesCLI)
        cli.config = {}
        cli.console = MagicMock()
        cli.agent = None
        cli.conversation_history = []
        cli._pending_input = MagicMock()
        return cli

    def test_registry_contains_checkpoint(self):
        cmd = resolve_command("checkpoint")
        assert cmd is not None
        assert cmd.name == "checkpoint"
        assert "go-no-go" in cmd.description.lower() or "checkpoint" in cmd.description.lower()

    def test_parse_checkpoint_flags(self):
        request = parse_checkpoint_request(
            '--goal "Finish dashboard" --current "on current path" --evidence "browser console + tests" --alternatives "switch route"'
        )
        assert request == CheckpointRequest(
            goal="Finish dashboard",
            current_state="on current path",
            evidence="browser console + tests",
            alternatives="switch route",
        )

    def test_parse_checkpoint_shorthand(self):
        request = parse_checkpoint_request("Finish dashboard ||| current path ||| tests passed ||| switch route")
        assert request.goal == "Finish dashboard"
        assert request.current_state == "current path"
        assert request.evidence == "tests passed"
        assert request.alternatives == "switch route"

    def test_evaluate_redirects_when_loop_signals_present(self):
        result = run_checkpoint_gate(
            CheckpointRequest(
                goal="Keep re-auditing old context",
                current_state="looping on same checkpoint",
                evidence="no new data",
                alternatives="switch path",
            )
        )
        assert result.decision == "REDIRECT"
        assert result.loop_risk is True

    def test_format_checkpoint_result_contains_decision_card(self):
        result = run_checkpoint_gate(CheckpointRequest(goal="Ship the patch", evidence="tests passed"))
        text = format_checkpoint_result(result)
        assert "Checkpoint / Go-No-Go" in text
        assert "Decision:" in text
        assert "Goal: Ship the patch" in text

    def test_cli_dispatches_checkpoint_handler(self):
        cli = self._make_cli()
        with patch.object(cli, "_handle_checkpoint_command", create=True) as mock_handler:
            assert cli.process_command('/checkpoint --goal "Ship the patch" --evidence "tests passed"') is True
        mock_handler.assert_called_once()
