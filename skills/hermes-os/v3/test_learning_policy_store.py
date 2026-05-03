import json

import pytest

from hermes_os import HermesOS


class _Router:
    def __init__(self):
        self.calls = []


class _Fleet:
    def __init__(self):
        self.calls = []

    def execute_task(self, task_description=None, division=None, safety_critical=False, context=None):
        self.calls.append((task_description, division, safety_critical, context or {}))
        return {
            "status": "completed",
            "qa_passed": True,
            "execution_time_seconds": 0.1,
            "result": {"via": "fleet"},
            "safety_passed": True,
        }


def _setup_os_for_policy_test(tmp_path):
    os_instance = HermesOS()
    # isolate mutable artifacts for safe tests
    os_instance.policy_store_path = tmp_path / "hermes_os_learning_policy.jsonl"
    os_instance.policy_ledger_path = tmp_path / "hermes_os_policy_ledger.jsonl"
    os_instance.routing_telemetry_path = tmp_path / "hermes_os_route_telemetry.jsonl"
    os_instance._telemetry_window = []
    os_instance.phase3_config["analyze_only"] = True
    os_instance.phase3_config["auto_route_enabled"] = True
    os_instance.phase3_config["auto_route_threshold"] = 0.92
    os_instance.router = _Router()
    os_instance.fleet = _Fleet()
    # re-bootstrap in isolated location
    os_instance._init_learning_policy_store()
    return os_instance


def _append_routed_event(
    os_instance: HermesOS,
    task_id: str,
    task_description: str,
    route_value: str,
):
    os_instance._append_route_telemetry(
        task_id=task_id,
        task_description=task_description,
        decision=type("Decision", (), {"route": type("Route", (), {"value": route_value})(), "raw": {}, "factors": {}})(),
        execution_decision=type("ExecutionDecision", (), {"route": type("Route", (), {"value": route_value})()})(),
        result={"status": "completed", "qa_passed": True},
        manual_override="",
        decision_metadata={"raw_contract": "legacy", "source": "test", "suggestion": "", "score": 0.5, "factors": {}},
        started_at=0,
        routing_latency=0.0,
        execution_latency=0.0,
        error=None,
    )


def test_learning_policy_store_bootstrap(tmp_path):
    os_instance = _setup_os_for_policy_test(tmp_path)

    status = os_instance.get_policy_status()
    assert status["active"]["status"] == "active"
    assert status["candidates"] == 0
    assert status["total_records"] == 1
    assert status["active"]["policy_id"].startswith("policy-")

    # policy store file should contain exactly one bootstrap record
    lines = os_instance.policy_store_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event_type"] == "learning_policy"
    assert record["status"] == "active"


def test_propose_learning_policy_validation_and_candidate(tmp_path):
    os_instance = _setup_os_for_policy_test(tmp_path)

    bad = os_instance.propose_learning_policy({"unsupported": True})
    assert bad["ok"] is False
    assert "unsupported policy keys" in bad["error"]

    bad_threshold = os_instance.propose_learning_policy({"auto_route_threshold": 1.5})
    assert bad_threshold["ok"] is False
    assert "within [0.0, 1.0]" in bad_threshold["error"]

    result = os_instance.propose_learning_policy({
        "auto_route_enabled": False,
        "auto_route_threshold": 0.75,
    }, rationale="Reduce route sensitivity")
    assert result["ok"] is True
    policy = result["policy"]
    assert policy["status"] == "candidate"
    assert policy["runtime_config"]["auto_route_enabled"] is False
    assert policy["runtime_config"]["auto_route_threshold"] == 0.75

    status = os_instance.get_policy_status()
    assert status["candidates"] == 1
    assert status["total_records"] == 2


def test_apply_learning_policy_and_readiness(tmp_path):
    os_instance = _setup_os_for_policy_test(tmp_path)

    # need empty telemetry to prove readiness gate works on sample minimum
    os_instance.routing_telemetry_path.write_text("", encoding="utf-8")

    proposal = os_instance.propose_learning_policy(
        {"auto_route_threshold": 0.9},
        rationale="prep for rollout",
    )
    assert proposal["ok"] is True
    policy_id = proposal["policy"]["policy_id"]

    readiness_empty = os_instance.evaluate_learning_policy_readiness(policy_id, min_feedback_events=5)
    assert readiness_empty["ok"] is True
    assert readiness_empty["ready"] is False
    assert readiness_empty["reason_codes"] == ["insufficient_feedback_samples"]

    # activate with explicit reason
    applied = os_instance.apply_learning_policy(policy_id, reason="validation_passed")
    assert applied["ok"] is True
    assert applied["policy"]["status"] == "active"
    assert applied["policy"]["policy_id"] == policy_id
    assert applied["previous_active"]["policy_id"].startswith("policy-")

    status = os_instance.get_policy_status()
    assert status["active"]["policy_id"] == policy_id
    assert status["active"]["status"] == "active"
    assert status["total_records"] == 3

    # readiness for unknown policy should fail clearly
    unknown = os_instance.evaluate_learning_policy_readiness("policy-does-not-exist")
    assert unknown["ok"] is False
    assert unknown["reason_codes"] == ["policy_not_found"]


def test_readiness_ready_pending_after_samples(tmp_path):
    os_instance = _setup_os_for_policy_test(tmp_path)

    # Add a single routing decision + feedback
    os_instance._append_route_telemetry(
        task_id="task-001",
        task_description="simple task",
        decision=type("Decision", (), {"route": type("Route", (), {"value": "hermes_direct"})(), "raw": {}, "factors": {}})(),
        execution_decision=type("ExecutionDecision", (), {"route": type("Route", (), {"value": "hermes_direct"})()})(),
        result={"status": "completed", "qa_passed": True},
        manual_override="",
        decision_metadata={"raw_contract": "legacy", "source": "test", "suggestion": "", "score": 0.5, "factors": {}},
        started_at=0,
        routing_latency=0.0,
        execution_latency=0.0,
        error=None,
    )
    os_instance.capture_routing_feedback(task_id="task-001", label="correct", note="ok")

    proposal = os_instance.propose_learning_policy({"auto_route_enabled": True}, rationale="sampled")
    assert proposal["ok"] is True
    policy_id = proposal["policy"]["policy_id"]

    # keep min_feedback=0 to isolate replay readiness behavior
    readiness = os_instance.evaluate_learning_policy_readiness(policy_id, min_feedback_events=0)
    assert readiness["ok"] is True
    assert readiness["ready"] is False
    assert "offline_replay_insufficient_history" in readiness["reason_codes"]


def test_readiness_offline_replay_stability_pass(tmp_path):
    os_instance = _setup_os_for_policy_test(tmp_path)

    # 3+ direct decisions with matching feedback keep replay signal stable
    for idx in range(3):
        task_id = f"stable-{idx}"
        os_instance._append_route_telemetry(
            task_id=task_id,
            task_description="simple task",
            decision=type("Decision", (), {"route": type("Route", (), {"value": "hermes_direct"})(), "raw": {}, "factors": {}})(),
            execution_decision=type("ExecutionDecision", (), {"route": type("Route", (), {"value": "hermes_direct"})()})(),
            result={"status": "completed", "qa_passed": True},
            manual_override="",
            decision_metadata={"raw_contract": "legacy", "source": "test", "suggestion": "", "score": 0.5, "factors": {}},
            started_at=0,
            routing_latency=0.0,
            execution_latency=0.0,
            error=None,
        )
        os_instance.capture_routing_feedback(task_id=task_id, label="correct", note="ok")

    proposal = os_instance.propose_learning_policy({"auto_route_enabled": True}, rationale="stability check")
    assert proposal["ok"] is True
    policy_id = proposal["policy"]["policy_id"]

    readiness = os_instance.evaluate_learning_policy_readiness(policy_id, min_feedback_events=3)
    assert readiness["ok"] is True
    assert readiness["ready"] is True
    assert readiness["reason_codes"] == ["policy_simulation_passed"]
    assert readiness["offline_replay"]["route_flip_rate"] == 0.0
    assert readiness["policy_report"]["acceptance_passed"] is True
    assert readiness["policy_report"]["failed_signals"] == []


def test_readiness_offline_replay_route_flip_guard(tmp_path):
    os_instance = _setup_os_for_policy_test(tmp_path)

    # historical routes are fleet, but candidate with analyze-only keeps direct -> flips should be high
    for idx in range(3):
        task_id = f"fleet-historical-{idx}"
        os_instance._append_route_telemetry(
            task_id=task_id,
            task_description="complex task",
            decision=type("Decision", (), {"route": type("Route", (), {"value": "fleet_complex"})(), "raw": {}, "factors": {}})(),
            execution_decision=type("ExecutionDecision", (), {"route": type("Route", (), {"value": "fleet_complex"})()})(),
            result={"status": "completed", "qa_passed": True},
            manual_override="",
            decision_metadata={"raw_contract": "legacy", "source": "test", "suggestion": "", "score": 0.5, "factors": {}},
            started_at=0,
            routing_latency=0.0,
            execution_latency=0.0,
            error=None,
        )
        os_instance.capture_routing_feedback(task_id=task_id, label="correct", note="fleet ok")

    proposal = os_instance.propose_learning_policy(
        {"auto_route_enabled": False, "auto_route_threshold": 0.92},
        rationale="route-flip guard",
    )
    assert proposal["ok"] is True
    policy_id = proposal["policy"]["policy_id"]

    readiness = os_instance.evaluate_learning_policy_readiness(policy_id, min_feedback_events=0)
    assert readiness["ok"] is True
    assert readiness["ready"] is False
    assert "offline_replay_too_many_route_changes" in readiness["reason_codes"]
    assert readiness["offline_replay"]["route_flip_rate"] == 1.0


def test_readiness_offline_replay_recent_window_drift_guard(tmp_path):
    os_instance = _setup_os_for_policy_test(tmp_path)

    # Historical baseline mostly direct, but recent window drifts to fleet
    for idx in range(6):
        task_id = f"stable-direct-{idx}"
        os_instance._append_route_telemetry(
            task_id=task_id,
            task_description="simple task",
            decision=type("Decision", (), {"route": type("Route", (), {"value": "hermes_direct"})(), "raw": {}, "factors": {}})(),
            execution_decision=type("ExecutionDecision", (), {"route": type("Route", (), {"value": "hermes_direct"})()})(),
            result={"status": "completed", "qa_passed": True},
            manual_override="",
            decision_metadata={"raw_contract": "legacy", "source": "test", "suggestion": "", "score": 0.5, "factors": {}},
            started_at=0,
            routing_latency=0.0,
            execution_latency=0.0,
            error=None,
        )
        os_instance.capture_routing_feedback(task_id=task_id, label="correct", note="direct ok")

    for idx in range(3):
        task_id = f"recent-fleet-{idx}"
        os_instance._append_route_telemetry(
            task_id=task_id,
            task_description="complex task",
            decision=type("Decision", (), {"route": type("Route", (), {"value": "fleet_complex"})(), "raw": {}, "factors": {}})(),
            execution_decision=type("ExecutionDecision", (), {"route": type("Route", (), {"value": "fleet_complex"})()})(),
            result={"status": "completed", "qa_passed": True},
            manual_override="",
            decision_metadata={"raw_contract": "legacy", "source": "test", "suggestion": "", "score": 0.5, "factors": {}},
            started_at=0,
            routing_latency=0.0,
            execution_latency=0.0,
            error=None,
        )
        os_instance.capture_routing_feedback(task_id=task_id, label="correct", note="fleet ok")

    proposal = os_instance.propose_learning_policy(
        {"auto_route_enabled": False, "auto_route_threshold": 0.92},
        rationale="recent drift guard",
    )
    assert proposal["ok"] is True
    policy_id = proposal["policy"]["policy_id"]

    readiness = os_instance.evaluate_learning_policy_readiness(policy_id, min_feedback_events=0)
    assert readiness["ok"] is True
    assert readiness["ready"] is False
    assert "offline_replay_recent_drift_risk" in readiness["reason_codes"]
    assert readiness["offline_replay"]["route_flip_rate"] < 0.35
    assert readiness["offline_replay"]["recent_route_flip_rate"] > 0.55


def test_readiness_offline_replay_confidence_bound_guard(tmp_path):
    os_instance = _setup_os_for_policy_test(tmp_path)

    # Small sample with minor mismatch can look safe by point estimate, but confidence should remain low
    for idx in range(3):
        task_id = f"conf-direct-{idx}"
        os_instance._append_route_telemetry(
            task_id=task_id,
            task_description="simple task",
            decision=type("Decision", (), {"route": type("Route", (), {"value": "hermes_direct"})(), "raw": {}, "factors": {}})(),
            execution_decision=type("ExecutionDecision", (), {"route": type("Route", (), {"value": "hermes_direct"})()})(),
            result={"status": "completed", "qa_passed": True},
            manual_override="",
            decision_metadata={"raw_contract": "legacy", "source": "test", "suggestion": "", "score": 0.5, "factors": {}},
            started_at=0,
            routing_latency=0.0,
            execution_latency=0.0,
            error=None,
        )
        os_instance.capture_routing_feedback(task_id=task_id, label="correct", note="direct ok")

    task_id = "conf-fleet-0"
    os_instance._append_route_telemetry(
        task_id=task_id,
        task_description="complex task",
        decision=type("Decision", (), {"route": type("Route", (), {"value": "fleet_complex"})(), "raw": {}, "factors": {}})(),
        execution_decision=type("ExecutionDecision", (), {"route": type("Route", (), {"value": "fleet_complex"})()})(),
        result={"status": "completed", "qa_passed": True},
        manual_override="",
        decision_metadata={"raw_contract": "legacy", "source": "test", "suggestion": "", "score": 0.5, "factors": {}},
        started_at=0,
        routing_latency=0.0,
        execution_latency=0.0,
        error=None,
    )
    os_instance.capture_routing_feedback(task_id=task_id, label="correct", note="fleet ok")

    proposal = os_instance.propose_learning_policy(
        {"auto_route_enabled": False, "auto_route_threshold": 0.92},
        rationale="confidence bound guard",
    )
    assert proposal["ok"] is True
    policy_id = proposal["policy"]["policy_id"]

    readiness = os_instance.evaluate_learning_policy_readiness(policy_id, min_feedback_events=0)
    assert readiness["ok"] is True
    assert readiness["ready"] is False
    assert "offline_replay_confidence_low" in readiness["reason_codes"]
    assert readiness["offline_replay"]["route_flip_rate"] == 0.25
    assert readiness["offline_replay"]["route_flip_rate_upper_bound"] > 0.35
    assert readiness["policy_report"]["acceptance_passed"] is False
    assert "replay_confidence" in readiness["policy_report"]["failed_signals"]


def test_readiness_offline_replay_seasonal_shift_guard(tmp_path):
    os_instance = _setup_os_for_policy_test(tmp_path)

    # 10 events split: first half stable direct, second half mixed with fleet mismatches
    # Overall flip remains low, recent window stays below drift threshold, but half-to-half shift should be flagged.
    for idx in range(5):
        task_id = f"seasonal-a-{idx}"
        _append_routed_event(os_instance, task_id, "simple", "hermes_direct")
        os_instance.capture_routing_feedback(task_id=task_id, label="correct", note="ok")

    for idx in range(3):
        task_id = f"seasonal-b-direct-{idx}"
        _append_routed_event(os_instance, task_id, "simple", "hermes_direct")
        os_instance.capture_routing_feedback(task_id=task_id, label="correct", note="ok")

    for idx in range(2):
        task_id = f"seasonal-b-fleet-{idx}"
        _append_routed_event(os_instance, task_id, "complex", "fleet_complex")
        os_instance.capture_routing_feedback(task_id=task_id, label="correct", note="ok")

    proposal = os_instance.propose_learning_policy(
        {"auto_route_enabled": False, "auto_route_threshold": 0.92},
        rationale="seasonal shift guard",
    )
    assert proposal["ok"] is True
    policy_id = proposal["policy"]["policy_id"]

    readiness = os_instance.evaluate_learning_policy_readiness(policy_id, min_feedback_events=0)
    assert readiness["ok"] is True
    assert readiness["ready"] is False
    assert "offline_replay_seasonal_shift_risk" in readiness["reason_codes"]
    assert readiness["offline_replay"]["route_flip_rate"] == 0.2
    assert readiness["offline_replay"]["recent_route_flip_rate"] <= 0.55


def test_readiness_offline_replay_route_sparsity_guard(tmp_path):
    os_instance = _setup_os_for_policy_test(tmp_path)

    # 10 events where only one fleet sample appears; sparse route mismatch should be considered risky.
    for idx in range(9):
        task_id = f"sparse-direct-{idx}"
        _append_routed_event(os_instance, task_id, "simple", "hermes_direct")
        os_instance.capture_routing_feedback(task_id=task_id, label="correct", note="ok")

    task_id = "sparse-fleet-0"
    _append_routed_event(os_instance, task_id, "complex", "fleet_complex")
    os_instance.capture_routing_feedback(task_id=task_id, label="correct", note="ok")

    proposal = os_instance.propose_learning_policy(
        {"auto_route_enabled": False, "auto_route_threshold": 0.92},
        rationale="sparsity guard",
    )
    assert proposal["ok"] is True
    policy_id = proposal["policy"]["policy_id"]

    readiness = os_instance.evaluate_learning_policy_readiness(policy_id, min_feedback_events=0)
    assert readiness["ok"] is True
    assert readiness["ready"] is False
    assert "offline_replay_route_sparsity_risk" in readiness["reason_codes"]
    assert "fleet_complex" in readiness["offline_replay"]["sparse_mismatch_routes"]


def test_readiness_guardrails_detect_policy_risks(tmp_path):
    os_instance = _setup_os_for_policy_test(tmp_path)
    os_instance.phase3_config["auto_route_threshold"] = 0.9

    # craft data where candidate would exceed false-positive guardrails
    _append_routed_event(os_instance, "task-a", "refactor task", "hermes_direct")
    os_instance.capture_routing_feedback(task_id="task-a", label="should_fleet", note="needs fleet")
    _append_routed_event(os_instance, "task-b", "refactor task", "hermes_direct")
    os_instance.capture_routing_feedback(task_id="task-b", label="should_fleet", note="still direct")

    proposal = os_instance.propose_learning_policy(
        {"auto_route_enabled": True, "auto_route_threshold": 0.15},
        rationale="aggressive change",
    )
    assert proposal["ok"] is True
    policy_id = proposal["policy"]["policy_id"]

    readiness = os_instance.evaluate_learning_policy_readiness(policy_id, min_feedback_events=0)
    assert readiness["ok"] is True
    assert readiness["ready"] is False
    assert "too_many_should_fleet_false_positives" in readiness["reason_codes"]
    assert "candidate_threshold_below_guardrail" in readiness["reason_codes"]
    assert "candidate_threshold_delta_exceeds_guardrail" in readiness["reason_codes"]
