import sys
from unittest.mock import MagicMock

import pytest

from tools.merged_policy_validator import PolicyValidationError


def test_hermes_cli_main_fails_closed_when_policy_gate_fails(monkeypatch, capsys):
    import hermes_cli.main as main_mod

    def fail_gate():
        raise PolicyValidationError(["policy invalid"])

    monkeypatch.setattr("hermes_cli.policy_gate.assert_merged_policy_gate", fail_gate)
    monkeypatch.setattr(sys, "argv", ["hermes", "--version"])

    with pytest.raises(SystemExit) as excinfo:
        main_mod.main()

    captured = capsys.readouterr()
    assert excinfo.value.code == 1
    assert "merged policy hard gate failed" in captured.err
    assert "policy invalid" in captured.err


def test_gateway_main_fails_closed_when_policy_gate_fails(monkeypatch, capsys):
    import gateway.run as gateway_run

    def fail_gate():
        raise PolicyValidationError(["policy invalid"])

    monkeypatch.setattr("hermes_cli.policy_gate.assert_merged_policy_gate", fail_gate)
    monkeypatch.setattr(gateway_run.asyncio, "run", MagicMock(side_effect=AssertionError("should not run")))
    monkeypatch.setattr(sys, "argv", ["gateway"])

    with pytest.raises(SystemExit) as excinfo:
        gateway_run.main()

    captured = capsys.readouterr()
    assert excinfo.value.code == 1
    assert "merged policy hard gate failed" in captured.err
    assert "policy invalid" in captured.err
