"""Tests for the Hermes OS CLI command activation flow."""

from types import SimpleNamespace
from unittest.mock import patch

from cli import HermesCLI


def test_root_command_activates_hermes_os_mode_and_reports_ready(capsys):
    """The root CLI command should activate Hermes OS immediately."""
    cli = object.__new__(HermesCLI)

    fake_stdout = "🛰️ Hermes OS\n✓ Hermes OS mode: ON\n  Mode: hermes_os\n  RTK: enabled\n"
    fake_result = SimpleNamespace(returncode=0, stdout=fake_stdout, stderr="")

    with patch("subprocess.run", return_value=fake_result) as mock_run:
        cli._handle_hermes_os_command("/hermes-os")

    captured = capsys.readouterr().out
    assert mock_run.call_count == 1
    assert mock_run.call_args.args[0] == ["hermes-os", "on"]
    assert "Mode: hermes_os" in captured
    assert "พร้อมทำงานใน Hermes OS context" in captured
    assert "Hermes OS Context" in captured
    assert "Hermes OS context active" in captured
    assert "Direct execution remains the default" in captured
    assert "Fleet runs only on explicit" in captured


def test_explicit_status_still_reports_status(capsys):
    """Explicit /hermes-os status should remain a status-only command."""
    cli = object.__new__(HermesCLI)

    fake_stdout = "Status:\n  Mode: hermes_os\n  Gateway: running\n"
    fake_result = SimpleNamespace(returncode=0, stdout=fake_stdout, stderr="")

    with patch("subprocess.run", return_value=fake_result) as mock_run:
        cli._handle_hermes_os_command("/hermes-os status")

    captured = capsys.readouterr().out
    assert mock_run.call_count == 1
    assert mock_run.call_args.args[0] == ["hermes-os", "status"]
    assert "Mode: hermes_os" in captured
    assert "ready to work" not in captured.lower()
