from importlib import util
from pathlib import Path


class _BridgeMock:
    def __init__(self, status_payload, readiness_results, apply_result=None, replay_result=None, health_result=None, tune_result=None, auto_run_status=None, auto_run_set_result=None, auto_run_cycle_result=None, auto_run_loop_result=None, feedback_result=None, propose_result=None):
        self._status_payload = status_payload
        self._readiness_results = readiness_results
        self._apply_result = apply_result or {"ok": True}
        self._replay_result = replay_result or {"ok": True, "evaluations": [], "evaluated_count": 0, "ready_count": 0, "blocked_count": 0}
        self._health_result = health_result or {"ok": True, "rollback_trigger": False, "risk_level": "none", "manual_override_rate": 0.0, "false_positive_rate": 0.0, "notes": ["ok"]}
        self._tune_result = tune_result or {"ok": True, "rollback_trigger": False, "apply_recommended": False, "reason_codes": [], "health": {}, "suggestions": []}
        self._auto_run_status = auto_run_status or {
            "ok": True,
            "mode": "off",
            "state": {
                "mode": "off",
                "canary_percent": 0.0,
                "cooldown_minutes": 60,
                "minimum_gain_floor": 0.0,
                "max_daily_change_rate": 0.2,
                "kill_switch": False,
            },
            "latest_cycle": {},
        }
        self._auto_run_set_result = auto_run_set_result or {
            "ok": True,
            "previous_mode": "off",
            "mode": "off",
            "state": {
                "mode": "off",
                "updated_by": "operator",
            },
        }
        self._auto_run_cycle_result = auto_run_cycle_result or {
            "ok": True,
            "cycle_id": "auto-cycle-0001",
            "mode": "off",
            "source": "manual",
            "decision": "manual_review",
            "replay": {"evaluated_count": 0, "ready_count": 0},
            "health": {"risk_level": "none", "rollback_trigger": False},
            "tune": {"apply_recommended": False},
        }
        self._auto_run_loop_result = auto_run_loop_result or {
            "ok": False,
            "blocked": True,
            "action": "auto_run_loop",
            "source": "scheduler",
            "actor": "operator",
            "eligibility": {
                "ok": False,
                "reason": "mode_off",
                "message": "auto-run mode is off",
                "mode": "off",
            },
        }
        self._feedback_result = feedback_result or {"ok": True}
        self._propose_result = propose_result or {
            "ok": True,
            "policy": {"policy_id": "policy-candidate-0001", "policy_sequence": 1},
        }
        self.calls = []
        self.calls_readiness = []
        self.calls_replay = []
        self.calls_health = []
        self.calls_tune = []
        self.calls_auto_run_status = []
        self.calls_auto_run_set = []
        self.calls_auto_run_cycle = []
        self.calls_auto_run_loop = []
        self.calls_feedback = []
        self.calls_propose = []
        self._mode = "hermes_os"
        self._os = self

    # Compatibility with skill handle command checks
    def is_os_mode_active(self):
        return True

    def refresh_mode(self):
        return False

    def status(self):
        return self._status_payload

    def evaluate_policy_readiness(self, policy_id, min_feedback_events=20):
        self.calls_readiness.append((policy_id, min_feedback_events))
        return self._readiness_results.get(policy_id, {"ok": False, "error": "policy_not_found", "reason_codes": ["policy_not_found"]})

    def evaluate_learning_policy_candidates(self, limit=None, min_feedback_events=20):
        self.calls_replay.append((limit, min_feedback_events))
        return self._replay_result

    def assess_active_policy_health(self, min_feedback_events=20):
        self.calls_health.append(min_feedback_events)
        return self._health_result

    def propose_guarded_auto_tune(self, min_feedback_events=20):
        self.calls_tune.append(min_feedback_events)
        return self._tune_result

    def get_auto_run_status(self):
        self.calls_auto_run_status.append("status")
        return self._auto_run_status

    def set_auto_run_mode(self, mode: str, actor: str = "operator", reason: str = ""):
        self.calls_auto_run_set.append((mode, actor, reason))
        payload = dict(self._auto_run_set_result)
        if payload.get("ok") is not False:
            payload["mode"] = mode
        return payload

    def run_learning_control_cycle(self, limit=None, min_feedback_events=20, actor="operator", source="manual"):
        self.calls_auto_run_cycle.append((limit, min_feedback_events, actor, source))
        return self._auto_run_cycle_result

    def run_auto_learning_loop(self, limit=None, min_feedback_events=20, actor="operator", source="scheduler", force=False):
        self.calls_auto_run_loop.append((limit, min_feedback_events, actor, source, force))
        return self._auto_run_loop_result

    def apply_policy(self, policy_id: str, reason: str):
        self.calls.append((policy_id, reason))
        return self._apply_result

    def capture_routing_feedback(self, task_id: str, label: str, note: str = ""):
        self.calls_feedback.append((task_id, label, note))
        return self._feedback_result

    def propose_policy(self, payload, rationale: str = ""):
        self.calls_propose.append((payload, rationale))
        return self._propose_result

    def get_learning_policies(self, include_inactive: bool = True):
        return self._status_payload.get("policy", {}).get("policies", [])


def _load_skill_class():
    skill_path = Path.home() / ".hermes" / "skills" / "hermes-os-integration" / "skill.py"
    spec = util.spec_from_file_location("hermes_os_status_apply_command_test", str(skill_path))
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.HermesOSSkill


def _activate(skill, bridge):
    skill._bridge = bridge
    skill._os = bridge
    skill._initialized = True


def _build_status_payload(policy_state):
    return {
        "mode": "hermes_os",
        "active": True,
        "version": "test",
        "components": {"core": True},
        "fleet": {"main_agents": 1, "sub_agents": 0},
        "phase3": {
            "analyze_only": False,
            "auto_route_enabled": False,
            "auto_route_threshold": 0.91,
        },
        "policy": policy_state,
    }


def test_status_includes_latest_candidate_readiness_summary():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 1,
                "policies": [
                    {
                        "policy_id": "policy-candidate-001",
                        "status": "candidate",
                        "created_at": "2026-04-25T10:00:00",
                    }
                ],
            }
        ),
        readiness_results={
            "policy-candidate-001": {
                "ok": True,
                "policy_report": {
                    "acceptance_passed": True,
                    "observed_feedback_total": 22,
                    "required_feedback_total": 20,
                    "failed_signals": [],
                    "signals": {
                        "sample_size": {"passed": True, "blockers": []},
                        "policy_state": {"passed": True, "blockers": []},
                    },
                },
            }
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "status")

    assert "**Latest Candidate Readiness Summary:**" in out
    assert "Policy: policy-candidate-001" in out
    assert "Acceptance: ✅ PASS" in out
    assert "Feedback sample: 22 / 20" in out
    assert "**Apply approval checklist:**" in out
    assert bridge.calls_readiness == [("policy-candidate-001", 20)]


def test_status_with_no_pending_candidate_policies_shows_waiting_message():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "status")

    assert "**Latest Candidate Readiness Summary:**" in out
    assert "No pending candidate policy found." in out


def test_apply_command_is_blocked_when_acceptance_not_passed():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={
            "policy-apply-001": {
                "ok": True,
                "policy_report": {
                    "acceptance_passed": False,
                    "failed_signals": ["policy_state"],
                    "signals": {
                        "sample_size": {"passed": False, "blockers": ["insufficient_feedback"]},
                    },
                    "observed_feedback_total": 6,
                    "required_feedback_total": 20,
                    "reason_codes": ["policy_not_ready_for_readiness"],
                    "notes": ["check threshold"],
                },
            }
        },
        apply_result={"ok": True},
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "apply policy-apply-001 deploy")

    assert "🚫 Apply blocked" in out
    assert "policy-apply-001" in out
    assert "⚠️ Sample Size (insufficient_feedback)" in out
    assert bridge.calls == []
    assert bridge.calls_readiness == [("policy-apply-001", 20)]


def test_apply_command_runs_when_readiness_passed():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={
            "policy-apply-002": {
                "ok": True,
                "policy_report": {
                    "acceptance_passed": True,
                    "failed_signals": [],
                    "signals": {
                        "sample_size": {"passed": True, "blockers": []},
                        "policy_state": {"passed": True, "blockers": []},
                    },
                    "observed_feedback_total": 30,
                    "required_feedback_total": 20,
                },
            }
        },
        apply_result={"ok": True},
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "apply policy-apply-002")

    assert "✅ Policy applied: policy-apply-002" in out
    assert "Acceptance: ✅ PASS" in out
    assert bridge.calls == [("policy-apply-002", "manual-approval")]
    assert bridge.calls_readiness == [("policy-apply-002", 20)]


def test_replay_command_evaluates_candidate_policies():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        replay_result={
            "ok": True,
            "evaluations": [
                {
                    "policy_id": "candidate-001",
                    "ready": True,
                    "reason_codes": ["policy_simulation_passed"],
                    "observed_feedback_total": 30,
                    "required_feedback_total": 20,
                },
                {
                    "policy_id": "candidate-002",
                    "ready": False,
                    "reason_codes": ["too_many_should_direct_false_positives"],
                    "observed_feedback_total": 15,
                    "required_feedback_total": 20,
                },
            ],
            "evaluated_count": 2,
            "ready_count": 1,
            "blocked_count": 1,
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "replay 5 20")

    assert "🧪 **Hermes OS Replay Evaluation**" in out
    assert "Evaluated: 2" in out
    assert "Ready: 1 / Blocked: 1" in out
    assert "candidate-001" in out
    assert "candidate-002" in out
    assert "⚠️ candidate-002" in out
    assert bridge.calls_replay == [(5, 20)]


def test_health_command_returns_policy_risk():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        health_result={
            "ok": True,
            "rollback_trigger": True,
            "risk_level": "high",
            "manual_override_rate": 0.31,
            "false_positive_rate": 0.27,
            "notes": ["manual override elevated"],
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "health 20")

    assert "🛡️ **Hermes OS Active Policy Health**" in out
    assert "Rollback trigger: 🚨" in out
    assert "Risk level: high" in out
    assert "Manual override rate: 31.00%" in out
    assert bridge.calls_health == [20]


def test_tune_command_returns_suggested_changes():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        tune_result={
            "ok": True,
            "rollback_trigger": False,
            "apply_recommended": True,
            "reason_codes": ["guarded_tuning_available"],
            "health": {
                "policy_id": "policy-live",
                "risk_level": "low",
                "rollback_trigger": False,
            },
            "suggestions": [
                {
                    "type": "increase_directness_guardrail",
                    "from": 0.8,
                    "to": 0.85,
                    "rationale": "Too many should_direct false positives",
                }
            ],
            "notes": ["safe, low-risk signal"],
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "tune 20")

    assert "🧠 **Hermes OS Guarded Tuning**" in out
    assert "Apply recommended: true" in out
    assert "increase_directness_guardrail" in out
    assert "guarded_tuning_available" in out
    assert "safe, low-risk signal" in out
    assert bridge.calls_tune == [20]


def test_auto_run_status_command_shows_control_status():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        auto_run_status={
            "ok": True,
            "mode": "pilot",
            "state": {
                "mode": "pilot",
                "canary_percent": 0.1,
                "cooldown_minutes": 30,
                "minimum_gain_floor": 0.0,
                "max_daily_change_rate": 0.15,
                "kill_switch": False,
            },
            "latest_cycle": {
                "decision": "pilot_recommend",
            },
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "auto-run status")

    assert "⚙️ **Hermes OS Auto-Run**" in out
    assert "Mode: pilot" in out
    assert "Canary: 10.00%" in out
    assert "Cooldown: 30 minutes" in out
    assert "Decision: pilot_recommend" in out
    assert bridge.calls_auto_run_status == ["status"]


def test_auto_run_set_command_rejects_non_off_modes_for_manual_learning():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        auto_run_set_result={
            "ok": True,
            "previous_mode": "off",
            "mode": "pilot",
            "state": {"mode": "pilot", "updated_by": "operator"},
        },
    )

    skill = _load_skill_class()()

    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "auto-run set pilot to validate")

    assert "Manual learning only" in out
    assert "hermes-learning" in out
    assert bridge.calls_auto_run_set == []


def test_auto_run_set_command_allows_off_mode():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        auto_run_set_result={
            "ok": True,
            "previous_mode": "pilot",
            "mode": "off",
            "state": {"mode": "off", "updated_by": "operator"},
        },
    )

    skill = _load_skill_class()()

    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "auto-run set off manual")

    assert "✅ Auto-run mode updated" in out
    assert "pilot -> off" in out
    assert bridge.calls_auto_run_set == [("off", "operator", "manual")]


def test_auto_run_run_command_is_deprecated_in_favor_of_hermes_learning():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        auto_run_cycle_result={
            "ok": True,
            "cycle_id": "auto-cycle-20260425-0001-pilot",
            "mode": "pilot",
            "source": "telegram-command",
            "decision": "pilot_recommend",
            "replay": {
                "evaluated_count": 2,
                "ready_count": 1,
            },
            "health": {
                "risk_level": "low",
                "rollback_trigger": False,
            },
            "tune": {
                "apply_recommended": True,
            },
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "auto-run run 10 25")

    assert "Manual learning only" in out
    assert "hermes-learning run" in out
    assert bridge.calls_auto_run_cycle == []

def test_auto_run_loop_command_is_disabled_for_manual_learning_mode():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        auto_run_loop_result={
            "ok": True,
            "cycle_id": "auto-cycle-20260425-0001-pilot",
            "mode": "pilot",
            "source": "telegram-command",
            "decision": "pilot_recommend",
            "replay": {
                "evaluated_count": 2,
                "ready_count": 1,
            },
            "health": {
                "risk_level": "low",
                "rollback_trigger": False,
            },
            "tune": {
                "apply_recommended": True,
            },
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "auto-run loop 10 25")

    assert "Manual learning only" in out
    assert "hermes-learning run" in out
    assert bridge.calls_auto_run_loop == []


def test_auto_run_loop_command_with_force_stays_disabled_for_manual_learning_mode():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        auto_run_loop_result={
            "ok": False,
            "blocked": True,
            "action": "auto_run_loop",
            "source": "telegram-command",
            "actor": "operator",
            "eligibility": {
                "reason": "cooldown_not_elapsed",
                "message": "next auto-run cycle in 120 seconds",
                "mode": "pilot",
            },
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-os", "auto-run loop 10 25 force")

    assert "Manual learning only" in out
    assert "hermes-learning run" in out
    assert bridge.calls_auto_run_loop == []


def test_hermes_learning_run_command_executes_manual_cycle():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        auto_run_cycle_result={
            "ok": True,
            "cycle_id": "manual-cycle-20260425-0001",
            "mode": "off",
            "source": "hermes-learning-command",
            "decision": "manual_review",
            "replay": {
                "evaluated_count": 3,
                "ready_count": 1,
            },
            "health": {
                "risk_level": "low",
                "rollback_trigger": False,
            },
            "tune": {
                "apply_recommended": True,
            },
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-learning", "run 10 25")

    assert "🧠 **Hermes Learning (Manual)**" in out
    assert "Cycle: manual-cycle-20260425-0001" in out
    assert "Decision: manual_review" in out
    assert bridge.calls_auto_run_cycle == [(10, 25, "operator", "hermes-learning-command")]


def test_hermes_learning_ingest_feedback_records_feedback_signal():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        feedback_result={"ok": True},
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command("hermes-learning", "ingest feedback task-abc should_fleet needs multi-step")

    assert "✅ Learning feedback ingested" in out
    assert "task-abc" in out
    assert bridge.calls_feedback == [("task-abc", "should_fleet", "needs multi-step")]


def test_hermes_learning_ingest_policy_creates_candidate():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        propose_result={
            "ok": True,
            "policy": {"policy_id": "policy-candidate-0099", "policy_sequence": 99},
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command(
        "hermes-learning",
        'ingest policy {"auto_route_enabled": true, "auto_route_threshold": 0.91, "rationale": "lower FP"}',
    )

    assert "✅ Learning policy ingested" in out
    assert "policy-candidate-0099" in out
    assert bridge.calls_propose == [
        ({"auto_route_enabled": True, "auto_route_threshold": 0.91}, "lower FP")
    ]


def test_hermes_learning_ingest_note_creates_policy_candidate_from_text_only():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        propose_result={
            "ok": True,
            "policy": {"policy_id": "policy-candidate-0101", "policy_sequence": 101},
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command(
        "hermes-learning",
        "ingest note พบว่าเคส multi-step ควร route ไป fleet และต้องมี checklist validation",
    )

    assert "✅ Learning note ingested" in out
    assert "policy-candidate-0101" in out
    assert len(bridge.calls_propose) == 1
    payload, rationale = bridge.calls_propose[0]
    assert payload == {}
    assert "multi-step" in rationale
    assert "checklist" in rationale


def test_hermes_learning_ingest_note_with_link_reads_and_summarizes_both_sources():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        propose_result={
            "ok": True,
            "policy": {"policy_id": "policy-candidate-0102", "policy_sequence": 102},
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    skill._fetch_url_text = lambda url, timeout=10, max_chars=4000: "เอกสารต้นทางแนะนำให้เพิ่ม safety gate และ pre-flight analyzer"

    out = skill.handle_command(
        "hermes-learning",
        "ingest note ปรับ workflow ให้ rollback ง่าย --link https://example.com/plan",
    )

    assert "✅ Learning note ingested" in out
    assert "policy-candidate-0102" in out
    assert len(bridge.calls_propose) == 1
    payload, rationale = bridge.calls_propose[0]
    assert payload == {}
    assert "ปรับ workflow ให้ rollback ง่าย" in rationale
    assert "safety gate" in rationale
    assert "https://example.com/plan" in rationale


def test_hermes_learning_ingest_note_supports_multiple_links():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        propose_result={
            "ok": True,
            "policy": {"policy_id": "policy-candidate-0103", "policy_sequence": 103},
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    skill._fetch_url_text = lambda url, timeout=10, max_chars=4000: f"summary from {url}"

    out = skill.handle_command(
        "hermes-learning",
        "ingest note รวมบทเรียน --link https://example.com/a --link https://example.com/b",
    )

    assert "✅ Learning note ingested" in out
    assert "Sources read: 2/2" in out
    payload, rationale = bridge.calls_propose[0]
    assert payload == {}
    assert "https://example.com/a" in rationale
    assert "https://example.com/b" in rationale


def test_hermes_learning_ingest_note_supports_file_attachment(tmp_path):
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        propose_result={
            "ok": True,
            "policy": {"policy_id": "policy-candidate-0104", "policy_sequence": 104},
        },
    )

    note_file = tmp_path / "learning_note.txt"
    note_file.write_text("เอกสารแนบเสนอให้เพิ่ม retry policy และ monitor alert", encoding="utf-8")

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command(
        "hermes-learning",
        f"ingest note ปรับระบบตามไฟล์แนบ --file {note_file}",
    )

    assert "✅ Learning note ingested" in out
    assert "policy-candidate-0104" in out
    payload, rationale = bridge.calls_propose[0]
    assert payload == {}
    assert "ปรับระบบตามไฟล์แนบ" in rationale
    assert "retry policy" in rationale
    assert str(note_file) in rationale


def test_hermes_learning_ingest_note_supports_title_and_tags_metadata():
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        propose_result={
            "ok": True,
            "policy": {"policy_id": "policy-candidate-0105", "policy_sequence": 105},
        },
    )

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command(
        "hermes-learning",
        "ingest note เพิ่มมาตรฐาน rollout --title Fleet Rollout Guard --tags routing,safety,phase3",
    )

    assert "✅ Learning note ingested" in out
    payload, rationale = bridge.calls_propose[0]
    assert payload == {}
    assert "title: Fleet Rollout Guard" in rationale
    assert "tags: routing, safety, phase3" in rationale


def test_hermes_learning_ingest_note_supports_pdf_source(tmp_path):
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        propose_result={
            "ok": True,
            "policy": {"policy_id": "policy-candidate-0106", "policy_sequence": 106},
        },
    )

    pdf_file = tmp_path / "plan.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%mock\n")

    skill = _load_skill_class()()
    _activate(skill, bridge)
    skill._read_pdf_file = lambda file_path, max_chars=4000: "pdf recommends canary release and rollback checklist"

    out = skill.handle_command(
        "hermes-learning",
        f"ingest note ใช้ข้อเสนอจาก pdf --file {pdf_file}",
    )

    assert "✅ Learning note ingested" in out
    payload, rationale = bridge.calls_propose[0]
    assert payload == {}
    assert "canary release" in rationale
    assert str(pdf_file) in rationale


def test_hermes_learning_ingest_note_includes_source_quality_scoring(tmp_path):
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        propose_result={
            "ok": True,
            "policy": {"policy_id": "policy-candidate-0107", "policy_sequence": 107},
        },
    )

    note_file = tmp_path / "quality_note.txt"
    note_file.write_text("short", encoding="utf-8")

    skill = _load_skill_class()()
    _activate(skill, bridge)
    skill._fetch_url_text = lambda url, timeout=10, max_chars=4000: "this is a sufficiently detailed source text " * 20

    out = skill.handle_command(
        "hermes-learning",
        f"ingest note ประเมินคุณภาพแหล่งข้อมูล --link https://example.com/quality --file {note_file}",
    )

    assert "✅ Learning note ingested" in out
    assert "Avg quality:" in out
    payload, rationale = bridge.calls_propose[0]
    assert payload == {}
    assert "source_quality[https://example.com/quality]" in rationale
    assert f"source_quality[{note_file}]" in rationale


def test_hermes_learning_ingest_note_quality_gate_blocks_low_quality_save(tmp_path):
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
    )

    note_file = tmp_path / "low_quality.txt"
    note_file.write_text("tiny", encoding="utf-8")

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command(
        "hermes-learning",
        f"ingest note เนื้อหาสั้นมาก --file {note_file} --quality-gate 0.7",
    )

    assert "⚠️ Quality gate not met" in out
    assert "Use --force to save anyway" in out
    assert bridge.calls_propose == []


def test_hermes_learning_ingest_note_quality_gate_allows_force_override(tmp_path):
    bridge = _BridgeMock(
        status_payload=_build_status_payload(
            {
                "active_id": "policy-live",
                "status": "active",
                "active_sequence": 11,
                "policy_store_path": "policy-store",
                "policy_ledger_path": "policy-ledger",
                "policy_candidates": 0,
                "policies": [],
            }
        ),
        readiness_results={},
        propose_result={
            "ok": True,
            "policy": {"policy_id": "policy-candidate-0108", "policy_sequence": 108},
        },
    )

    note_file = tmp_path / "low_quality_force.txt"
    note_file.write_text("tiny", encoding="utf-8")

    skill = _load_skill_class()()
    _activate(skill, bridge)

    out = skill.handle_command(
        "hermes-learning",
        f"ingest note เนื้อหาสั้นมาก --file {note_file} --quality-gate 0.7 --force",
    )

    assert "✅ Learning note ingested" in out
    assert "Avg quality:" in out
    assert len(bridge.calls_propose) == 1
