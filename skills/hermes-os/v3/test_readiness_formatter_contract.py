from pathlib import Path
from importlib import util

import pytest

from hermes_os import HermesOS


@pytest.fixture(scope="module")
def skill_module():
    """Load hermes-os-integration skill module via SourceFileLoader."""
    skill_path = Path.home() / ".hermes" / "skills" / "hermes-os-integration" / "skill.py"
    assert skill_path.exists(), f"skill file not found: {skill_path}"
    spec = util.spec_from_file_location("hermes_os_integration_skill_test", str(skill_path))
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_readiness_report_renders_all_policy_signals(skill_module):
    """Formatter should render every signal key from policy_report signals."""
    skill = skill_module.HermesOSSkill()
    os_instance = HermesOS()

    policy_report = os_instance._build_readiness_policy_report(
        reason_codes=[
            "insufficient_feedback_samples",
            "offline_replay_recent_drift_risk",
            "too_many_should_fleet_false_positives",
            "offline_replay_confidence_low",
        ],
        replay_summary={
            "simulated_events": 7,
            "route_flip_rate": 0.24,
            "route_flip_rate_upper_bound": 0.39,
            "recent_route_flip_rate": 0.48,
            "seasonal_flip_delta": 0.11,
            "sparse_mismatch_routes": ["fleet_complex"],
        },
        observed_feedback_total=4,
        required_feedback_total=20,
    )

    result = skill._format_readiness_report(
        policy_id="policy-0001",
        readiness={
            "ok": True,
            "policy_report": policy_report,
            "reason_codes": [
                "insufficient_feedback_samples",
                "offline_replay_recent_drift_risk",
                "too_many_should_fleet_false_positives",
                "offline_replay_confidence_low",
            ],
            "notes": ["mock note"],
            "observed_feedback_total": 4,
            "required_feedback_total": 20,
        },
    )

    lines = result.splitlines()
    assert "🧾 **Hermes OS Policy Readiness**" in lines[0]
    assert "Policy: policy-0001" in result
    assert "Feedback sample: 4 / 20" in result
    assert "**Signals:**" in result
    assert "**Reason insights:**" in result

    for signal_key in policy_report["signals"].keys():
        human_label = signal_key.replace("_", " ").title()
        assert any(human_label in line for line in lines), f"missing signal label: {human_label}"

    assert "• insufficient_feedback_samples" in result
    assert "• offline_replay_recent_drift_risk" in result
    assert "• too_many_should_fleet_false_positives" in result
    assert "• offline_replay_confidence_low" in result


def test_readiness_report_unknown_reason_has_fallback_explanation(skill_module):
    """Unknown reason code should not break rendering and should show fallback explanation."""
    skill = skill_module.HermesOSSkill()
    readiness = {
        "ok": True,
        "policy_report": {
            "acceptance_passed": True,
            "failed_signals": [],
            "signals": {
                "sample_size": {"passed": True, "blockers": []},
                "policy_state": {"passed": True, "blockers": []},
                "false_positive": {"passed": True, "blockers": []},
                "threshold_guard": {"passed": True, "blockers": []},
                "replay_history": {"passed": True, "blockers": []},
                "replay_overall": {"passed": True, "blockers": []},
                "replay_recent": {"passed": True, "blockers": []},
                "replay_confidence": {"passed": True, "blockers": []},
                "replay_seasonal": {"passed": True, "blockers": []},
                "replay_sparsity": {"passed": True, "blockers": []},
            },
            "observed_feedback_total": 20,
            "required_feedback_total": 20,
            "replay": {
                "simulated_events": 0,
                "route_flip_rate": 0,
                "route_flip_rate_upper_bound": 0,
                "recent_route_flip_rate": 0,
                "seasonal_flip_delta": 0,
                "sparse_mismatch_routes": [],
            },
        },
        "reason_codes": ["some_unknown_reason_code"],
        "notes": [],
    }
    result = skill._format_readiness_report("policy-0002", readiness)

    assert "Reason insights:" in result
    assert "some_unknown_reason_code" in result
    assert "รหัสเตือนนี้ยังไม่มีคำอธิบายในระบบ" in result
