import sys

import pytest

from tools.merged_policy_validator import PolicyValidationError


def test_cli_main_fails_closed_when_policy_gate_fails(monkeypatch, capsys):
    import cli as cli_mod

    def fail_gate():
        raise PolicyValidationError(["policy invalid"])

    monkeypatch.setattr("hermes_cli.policy_gate.assert_merged_policy_gate", fail_gate)
    monkeypatch.setattr(sys, "argv", ["cli.py"])

    with pytest.raises(SystemExit) as excinfo:
        cli_mod.main()

    captured = capsys.readouterr()
    assert excinfo.value.code == 1
    assert "merged policy hard gate failed" in captured.err
    assert "policy invalid" in captured.err
