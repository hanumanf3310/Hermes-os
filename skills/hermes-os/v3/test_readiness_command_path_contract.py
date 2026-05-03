from importlib import util
from pathlib import Path


class _BridgeMock:
    def __init__(self, readiness_result):
        self._readiness_result = readiness_result
        self.calls = []
        self._mode = "hermes_os"

    def is_os_mode_active(self):
        return True

    def refresh_mode(self):
        return False

    def evaluate_policy_readiness(self, policy_id, min_feedback_events=20):
        self.calls.append((policy_id, min_feedback_events))
        return self._readiness_result


def _load_skill_class():
    skill_path = Path.home() / ".hermes" / "skills" / "hermes-os-integration" / "skill.py"
    spec = util.spec_from_file_location("hermes_os_integration_skill_for_command_test", str(skill_path))
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.HermesOSSkill


def _activate(skill, bridge):
    skill._bridge = bridge
    skill._initialized = True


def test_hermes_os_readiness_command_success_path_formats_report():
    HermesOSSkill = _load_skill_class()
    skill = HermesOSSkill()

    bridge = _BridgeMock(
        {
            "ok": True,
            "ready": False,
            "policy_report": {
                "acceptance_passed": False,
                "failed_signals": ["policy_state"],
                "signals": {
                    "sample_size": {"passed": True, "blockers": []},
                    "policy_state": {"passed": False, "blockers": ["policy_not_ready_for_readiness"]},
                },
                "observed_feedback_total": 4,
                "required_feedback_total": 20,
                "replay": {
                    "simulated_events": 0,
                    "route_flip_rate": 0.0,
                    "route_flip_rate_upper_bound": 0.0,
                    "recent_route_flip_rate": 0.0,
                    "seasonal_flip_delta": 0.0,
                    "sparse_mismatch_routes": [],
                },
            },
            "reason_codes": ["policy_not_ready_for_readiness"],
            "notes": [],
        }
    )
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "readiness policy-0001 20")

    assert bridge.calls == [("policy-0001", 20)]
    assert "🧾 **Hermes OS Policy Readiness**" in out
    assert "Policy: policy-0001" in out
    assert "Reason insights:" in out
    assert "policy_not_ready_for_readiness" in out


def test_hermes_os_readiness_command_invalid_min_samples_returns_usage():
    HermesOSSkill = _load_skill_class()
    skill = HermesOSSkill()
    _activate(skill, _BridgeMock({"ok": True, "policy_report": {}, "reason_codes": [], "notes": []}))

    out = skill.handle_command("hermes-os", "readiness policy-0001 not-a-number")

    assert out == "❗ Usage: hermes-os readiness <policy_id> [min_samples]"


def test_hermes_os_readiness_command_error_path_returns_reason_codes():
    HermesOSSkill = _load_skill_class()
    skill = HermesOSSkill()
    bridge = _BridgeMock(
        {
            "ok": False,
            "reason_codes": ["policy_not_found"],
            "error": "policy_not_found",
        }
    )
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "readiness policy-does-not-exist 20")

    assert bridge.calls == [("policy-does-not-exist", 20)]
    assert out == "❌ Policy readiness error: policy_not_found"


def test_hermes_os_readiness_command_success_golden_contract_snapshot():
    HermesOSSkill = _load_skill_class()
    skill = HermesOSSkill()
    bridge = _BridgeMock(
        {
            "ok": True,
            "ready": True,
            "policy_report": {
                "acceptance_passed": True,
                "failed_signals": [],
                "signals": {
                    "policy_state": {
                        "passed": False,
                        "blockers": ["policy_not_ready_for_readiness"],
                    },
                    "sample_size": {"passed": True, "blockers": []},
                    "false_positive": {
                        "passed": False,
                        "blockers": [
                            "too_many_should_fleet_false_positives",
                            "too_many_should_direct_false_positives",
                        ],
                    },
                },
                "observed_feedback_total": 45,
                "required_feedback_total": 60,
                "replay": {
                    "simulated_events": 14,
                    "route_flip_rate": 0.08,
                    "route_flip_rate_upper_bound": 0.2,
                    "recent_route_flip_rate": 0.12,
                    "seasonal_flip_delta": 0.07,
                    "sparse_mismatch_routes": ["direct", "fleet"],
                },
            },
            "reason_codes": [
                "policy_not_ready_for_readiness",
                "too_many_should_fleet_false_positives",
            ],
            "notes": ["note-1", "note-2"],
        }
    )
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "readiness policy-0001 55")

    expected = (
        "🧾 **Hermes OS Policy Readiness**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Policy: policy-0001\n"
        "Acceptance: ✅ PASS\n"
        "Feedback sample: 45 / 60\n"
        "\n"
        "**Signals:**\n"
        "  ⚠️ False Positive (too_many_should_fleet_false_positives, too_many_should_direct_false_positives)\n"
        "  ⚠️ Policy State (policy_not_ready_for_readiness)\n"
        "  ✅ Sample Size\n"
        "\n"
        "**Offline replay:**\n"
        "  Simulated events: 14\n"
        "  Overall route flip: 8.00%\n"
        "  Upper bound flip: 20.00%\n"
        "  Recent route flip: 12.00%\n"
        "  Seasonal flip delta: 7.00%\n"
        "  Sparse mismatch routes: direct, fleet\n"
        "\n"
        "**Reason insights:**\n"
        "  • policy_not_ready_for_readiness: policy นี้ยังไม่ใช่สถานะ `candidate`; readiness ใช้ได้เฉพาะ candidate เท่านั้น\n"
        "  • too_many_should_fleet_false_positives: พบสัญญาณ `should_fleet` false positive สูง; เสี่ยง over-route Fleet\n"
        "**Notes:**\n"
        "  • note-1\n"
        "  • note-2\n"
        "\n"
        "✅ Ready to request operational apply (manual approval only).\n"
        "\n"
        "**Apply approval checklist:**\n"
        "  ⚠️ False Positive (too_many_should_fleet_false_positives, too_many_should_direct_false_positives)\n"
        "  ⚠️ Policy State (policy_not_ready_for_readiness)\n"
        "  ✅ Sample Size"
    )

    assert out == expected
