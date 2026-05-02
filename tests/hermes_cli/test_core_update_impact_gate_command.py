from types import SimpleNamespace

from hermes_cli.commands import resolve_command, telegram_bot_commands
from hermes_cli.core_update_impact_gate import (
    CoreUpdateImpactRequest,
    CoreUpdateImpactResult,
    classify_core_update_impact,
    format_core_update_impact_result,
    parse_core_update_impact_request,
)


def test_core_update_impact_gate_registry_and_telegram_alias():
    cmd = resolve_command("hermes-core-update-impact-gate")
    assert cmd is not None
    assert cmd.name == "hermes-core-update-impact-gate"
    assert resolve_command("hermes_core_update_impact_gate").name == "hermes-core-update-impact-gate"

    telegram_names = {name for name, _ in telegram_bot_commands()}
    assert "hermes_core_update_impact_gate" in telegram_names
    assert "hermes-core-update-impact-gate" not in telegram_names


def test_core_update_impact_gate_parse_defaults_and_flags():
    req, error = parse_core_update_impact_request("")
    assert error is None
    assert req == CoreUpdateImpactRequest()

    req, error = parse_core_update_impact_request("--upstream https://example.com/alt.git --ref develop")
    assert error is None
    assert req == CoreUpdateImpactRequest(
        upstream_repo="https://example.com/alt.git",
        upstream_ref="develop",
    )


def test_core_update_impact_gate_classifies_protected_surfaces():
    risk, impacted, protected, backup_required, next_action = classify_core_update_impact(
        [
            "cli.py",
            "gateway/run.py",
            "hermes_cli/policy_gate.py",
            "hermes_cli/hermes_os_format.py",
            "agent/context_mode_retrieval.py",
            "tests/gateway/test_hermes_os_session_binding.py",
            "website/docs/reference/merged-hard-gate-policy.yaml",
        ]
    )

    assert risk == "CRITICAL"
    assert backup_required is True
    assert "command-routing" in impacted
    assert "policy-gate" in impacted
    assert "status-format" in impacted
    assert "context-routing" in impacted
    assert "cli.py" in protected
    assert "gateway/run.py" in protected
    assert "hermes_cli/policy_gate.py" in protected
    assert "website/docs/reference/merged-hard-gate-policy.yaml" in protected
    assert "backup branch" in next_action


def test_core_update_impact_gate_formats_report():
    result = CoreUpdateImpactResult(
        ok=True,
        repo_path="/repo",
        local_branch="main",
        local_head="abc123",
        upstream_repo="https://github.com/NousResearch/hermes-agent",
        upstream_ref="main",
        upstream_head="def456",
        latest_tag="v1.2.3",
        ahead=2,
        behind=4,
        dirty_files=("cli.py",),
        untracked_files=(),
        changed_files=("cli.py", "gateway/run.py"),
        impacted_surfaces=("command-routing",),
        protected_files=("cli.py", "gateway/run.py"),
        risk="CRITICAL",
        backup_required=True,
        next_action="Create a backup branch and run focused Hermes OS parity smoke tests before update.",
    )

    report = format_core_update_impact_result(result)
    assert "Hermes Core Update Impact Gate" in report
    assert "CRITICAL" in report
    assert "cli.py" in report
    assert "Next action" in report


def test_cli_core_update_impact_gate_handler_prints_report(monkeypatch):
    from cli import HermesCLI
    import hermes_cli.core_update_impact_gate as helper

    printed = []

    monkeypatch.setattr(helper, "parse_core_update_impact_request", lambda raw_args: (CoreUpdateImpactRequest(), None))
    monkeypatch.setattr(helper, "run_core_update_impact_gate", lambda request: CoreUpdateImpactResult(ok=True))
    monkeypatch.setattr(helper, "format_core_update_impact_result", lambda result: "REPORT")

    cli = object.__new__(HermesCLI)
    cli.console = SimpleNamespace(print=printed.append)

    cli._handle_core_update_impact_gate_command("hermes-core-update-impact-gate")

    assert printed == ["REPORT"]
