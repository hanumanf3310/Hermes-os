import json

from hermes_os import HermesOS


class _Route:
    def __init__(self, value):
        self.value = value


class _Decision:
    def __init__(self, route_value, confidence=0.5, contract_route="test_route"):
        self.route = _Route(route_value)
        self.suggested_division = None
        self.confidence = confidence
        self.phase3 = {
            "contract_route": contract_route,
            "source": "test",
            "suggestion": "unit test decision",
            "score": confidence,
            "factors": {"test": "case"},
        }
        self.reason = ""
        self.resolution_reason = ""


class _Router:
    def __init__(self, route_value="hermes_direct", confidence=0.5, contract_route="test_route"):
        self.route_value = route_value
        self.confidence = confidence
        self.contract_route = contract_route

    def analyze(self, task: str, context: dict) -> _Decision:
        return _Decision(self.route_value, confidence=self.confidence, contract_route=self.contract_route)


class _Fleet:
    def __init__(self):
        self.main_agents = 1
        self.sub_agents = 0
        self.calls = []

    def execute_task(self, task_description=None, division=None, safety_critical=False, context=None):
        self.calls.append((task_description, division, safety_critical, context or {}))
        return {
            "status": "completed",
            "qa_passed": True,
            "execution_time_seconds": 0.22,
            "result": {
                "via": "fleet",
                "division": division,
            },
        }


def _setup_os_for_feedback_test(tmp_path):
    os_instance = HermesOS()
    os_instance.router = _Router(route_value="hermes_direct", confidence=0.99, contract_route="hermes_direct")
    os_instance.fleet = _Fleet()
    os_instance._telemetry_window = []
    os_instance._telemetry_max_window = 200
    os_instance.routing_telemetry_path = tmp_path / "hermes_os_route_telemetry.jsonl"
    os_instance.phase3_config["analyze_only"] = True
    os_instance.phase3_config["auto_route_enabled"] = False
    os_instance.phase3_config["auto_route_threshold"] = 0.92
    return os_instance


def test_capture_routing_feedback_writes_event(tmp_path):
    os_instance = _setup_os_for_feedback_test(tmp_path)
    task = os_instance.execute("simple direct task", context={"raw_task": "simple direct task"})

    result = os_instance.capture_routing_feedback(
        task_id=task["task_id"],
        label="correct",
        note="looks good",
    )

    assert result["ok"] is True
    assert result["task_id"] == task["task_id"]

    lines = os_instance.routing_telemetry_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    feedback_event = json.loads(lines[-1])
    assert feedback_event["event_type"] == "routing_feedback"
    assert feedback_event["task_id"] == task["task_id"]
    assert feedback_event["label"] == "correct"
    assert feedback_event["routing_snapshot"]["execution_route"] == "hermes_direct"


def test_capture_feedback_validation(tmp_path):
    os_instance = _setup_os_for_feedback_test(tmp_path)
    task = os_instance.execute("direct task", context={"raw_task": "direct task"})

    invalid = os_instance.capture_routing_feedback(task_id=task["task_id"], label="not_supported")
    assert invalid["ok"] is False
    assert "invalid feedback label" in invalid["error"]

    missing = os_instance.capture_routing_feedback(task_id="hermes_does_not_exist", label="correct")
    assert missing["ok"] is False
    assert "no routing decision" in missing["error"]


def test_feedback_metrics_and_false_positive_signal(tmp_path):
    os_instance = _setup_os_for_feedback_test(tmp_path)

    direct = os_instance.execute("direct task", context={"raw_task": "direct task"})

    os_instance.router = _Router(route_value="hermes_direct", confidence=0.99, contract_route="direct_with_suggestion")
    suggestion = os_instance.execute(
        "design a lightweight sync flow",
        context={"raw_task": "design a lightweight sync flow"},
    )

    os_instance.phase3_config["analyze_only"] = False
    os_instance.phase3_config["auto_route_enabled"] = True
    os_instance.phase3_config["auto_route_threshold"] = 0.0
    os_instance.router = _Router(route_value="fleet_complex", confidence=0.99, contract_route="fleet_complex")
    fleet = os_instance.execute("build worker service", context={"raw_task": "build worker service"})

    # Feedback signals for routing correctness
    os_instance.capture_routing_feedback(fleet["task_id"], "should_direct", "Should be direct")
    os_instance.capture_routing_feedback(direct["task_id"], "should_fleet", "Should be fleet")
    os_instance.capture_routing_feedback(suggestion["task_id"], "correct", "Suggestion looks good")

    metrics = os_instance.get_routing_feedback_metrics()
    assert metrics["routing_total"] == 3
    assert metrics["route_mix"] == {
        "direct": 1,
        "fleet": 1,
        "direct_with_suggestion": 1,
        "unknown": 0,
    }
    assert metrics["manual_override_rate"] == 0.0

    labels = metrics["feedback"]["labels"]
    assert labels["correct"] == 1
    assert labels["should_direct"] == 1
    assert labels["should_fleet"] == 1

    fp = metrics["feedback"]["false_positive"]
    assert fp["should_direct"]["count"] == 1
    assert fp["should_fleet"]["count"] == 1
    assert fp["total"] == 2


def test_iter_feedback_handles_corrupt_lines(tmp_path):
    os_instance = _setup_os_for_feedback_test(tmp_path)
    os_instance.routing_telemetry_path.write_text("{invalid-json\n", encoding="utf-8")

    direct = os_instance.execute("direct task", context={"raw_task": "direct task"})
    os_instance.capture_routing_feedback(direct["task_id"], "correct")

    metrics = os_instance.get_routing_feedback_metrics()
    assert metrics["routing_total"] == 1
    assert metrics["feedback_total"] == 1
    assert metrics["route_mix"]["direct"] == 1


def test_bridge_handle_feedback_command(tmp_path, monkeypatch):
    # Lightweight command-path sanity check through Hermes Bridge command handler.
    from integrations.telegram_bridge import handle_hermes_os_command

    class _FakeBridge:
        def __init__(self, os_instance):
            self._os = os_instance
            self._mode = "hermes_os"

        def is_os_mode_active(self):
            return True

        def refresh_mode(self):
            return False

        def capture_routing_feedback(self, task_id, label, note="", source="telegram"):
            return self._os.capture_routing_feedback(task_id=task_id, label=label, note=note, source=source)

        def get_feedback_metrics(self, limit=None):
            metrics = self._os.get_routing_feedback_metrics(limit=limit)
            metrics["ok"] = True
            return metrics

    bridge = _FakeBridge(_setup_os_for_feedback_test(tmp_path))
    monkeypatch.setattr("integrations.telegram_bridge.get_bridge", lambda: bridge)

    # capture command
    task = bridge._os.execute("simple for command", context={"raw_task": "simple for command"})
    response = handle_hermes_os_command("feedback", f"{task['task_id']} should_fleet this should have been fleet")
    assert "✅ Feedback captured" in response

    # metrics command
    bridge._os.capture_routing_feedback(task["task_id"], "should_fleet", "forced fleet")
    response_metrics = handle_hermes_os_command("metrics", "")
    assert "Hermes OS Routing Feedback Metrics" in response_metrics
    assert "should_fleet" in response_metrics
