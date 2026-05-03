from importlib import util
from pathlib import Path


class _BridgeMock:
    def __init__(self, feedback_metrics):
        self._feedback_metrics = feedback_metrics
        self.calls = []
        self._mode = "hermes_os"

    def is_os_mode_active(self):
        return True

    def refresh_mode(self):
        return False

    def get_feedback_metrics(self, limit=None):
        self.calls.append(("get_feedback_metrics", limit))
        return self._feedback_metrics


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


def test_hermes_os_metrics_command_success_without_limit_formats_report():
    HermesOSSkill = _load_skill_class()
    skill = HermesOSSkill()

    bridge = _BridgeMock(
        {
            "ok": True,
            "routing_total": 10,
            "feedback_total": 4,
            "manual_override_rate": 0.1234,
            "route_mix": {
                "direct": 8,
                "fleet": 1,
                "direct_with_suggestion": 1,
                "unknown": 0,
            },
            "feedback": {
                "labels": {
                    "correct": 2,
                    "incorrect": 1,
                    "should_direct": 1,
                    "should_fleet": 0,
                },
                "false_positive": {
                    "should_direct": {"count": 3, "rate": 0.75},
                    "should_fleet": {"count": 1, "rate": 0.25},
                    "total": 4,
                    "rate": 1.0,
                },
            },
        }
    )
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "metrics")

    assert bridge.calls == [("get_feedback_metrics", None)]
    expected = (
        "📊 **Hermes OS Routing Feedback Metrics**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "routing_total: 10\n"
        "feedback_total: 4\n"
        "manual_override_rate: 12.34%\n"
        "\n"
        "**Route Mix:**\n"
        "  direct: 8\n"
        "  fleet: 1\n"
        "  direct_with_suggestion: 1\n"
        "  unknown: 0\n"
        "\n"
        "**Feedback Labels:**\n"
        "  correct: 2\n"
        "  incorrect: 1\n"
        "  should_direct: 1\n"
        "  should_fleet: 0\n"
        "\n"
        "**False Positive Signals:**\n"
        "  should_direct: 3 (rate 75.00%)\n"
        "  should_fleet: 1 (rate 25.00%)\n"
        "  total: 4 (rate 100.00%)"
    )

    assert out == expected


def test_hermes_os_metrics_command_invalid_limit_returns_usage():
    HermesOSSkill = _load_skill_class()
    skill = HermesOSSkill()
    _activate(skill, _BridgeMock({"ok": True}))

    out = skill.handle_command("hermes-os", "metrics not-a-number")

    assert out == "❗ Usage: hermes-os metrics [limit]"


def test_hermes_os_metrics_command_error_path_returns_error_message():
    HermesOSSkill = _load_skill_class()
    skill = HermesOSSkill()
    bridge = _BridgeMock(
        {
            "ok": False,
            "error": "metrics_store_down",
        }
    )
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "metrics 20")

    assert bridge.calls == [("get_feedback_metrics", 20)]
    assert out == "❌ metrics_store_down"
