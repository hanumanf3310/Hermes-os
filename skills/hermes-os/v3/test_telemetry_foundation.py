import json

import pytest

from hermes_os import HermesOS


class _Route:
    def __init__(self, value):
        self.value = value


class _Decision:
    def __init__(self, route_value, confidence=0.5):
        self.route = _Route(route_value)
        self.suggested_division = None
        self.confidence = confidence
        self.phase3 = {
            "contract_route": "test_route",
            "source": "test",
            "suggestion": "unit test decision",
            "score": confidence,
            "factors": {"test": "case"},
        }
        self.reason = ""
        self.resolution_reason = ""


class _Router:
    def __init__(self, route_value="hermes_direct", confidence=0.5):
        self.route_value = route_value
        self.confidence = confidence

    def analyze(self, task: str, context: dict) -> _Decision:
        return _Decision(self.route_value, confidence=self.confidence)


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


def _setup_os_for_telemetry_test(tmp_path):
    os_instance = HermesOS()
    os_instance.router = _Router(route_value="hermes_direct", confidence=0.99)
    os_instance.fleet = _Fleet()
    os_instance._telemetry_window = []
    os_instance._telemetry_max_window = 200
    os_instance.routing_telemetry_path = tmp_path / "hermes_os_route_telemetry.jsonl"
    os_instance.phase3_config["analyze_only"] = True
    os_instance.phase3_config["auto_route_enabled"] = False
    os_instance.phase3_config["auto_route_threshold"] = 0.92
    return os_instance


def test_execute_records_telemetry_for_direct_route(tmp_path, monkeypatch):
    os_instance = _setup_os_for_telemetry_test(tmp_path)

    def fake_direct(task, context):
        return {
            "status": "completed",
            "qa_passed": True,
            "execution_time_seconds": 0.11,
            "result": {"via": "direct"},
            "safety_passed": True,
        }

    monkeypatch.setattr(os_instance, "_execute_hermes_direct", fake_direct)

    result = os_instance.execute("Summarize today's sync report", context={"raw_task": "สรุปข้อความนี้"})

    assert result["route"] == "hermes_direct"
    assert result["routing_contract"]["auto_route_threshold"] == 0.92
    assert os_instance.routing_telemetry_path.exists()

    lines = os_instance.routing_telemetry_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    event = json.loads(lines[0])
    assert event["task_id"] == result["task_id"]
    assert event["decision"]["execution"]["route"] == "hermes_direct"
    assert event["outcome"]["status"] == "completed"
    assert event["timing"]["routing_latency_ms"] >= 0


def test_execute_manual_override_forces_fleet_and_logs_resolution(tmp_path, monkeypatch):
    os_instance = _setup_os_for_telemetry_test(tmp_path)
    os_instance.router = _Router(route_value="hermes_direct", confidence=0.99)
    os_instance.fleet = _Fleet()
    os_instance.phase3_config["analyze_only"] = True

    # force manual override to fleet via raw_task prefix
    result = os_instance.execute("any", context={"raw_task": "/fleet handle task"})

    assert result["route"] == "fleet_complex"
    event = json.loads(os_instance.routing_telemetry_path.read_text(encoding="utf-8").splitlines()[-1])
    assert event["manual_override"] == "fleet"
    assert event["decision"]["execution"]["route"] == "fleet_complex"
    assert event["outcome"]["status"] == "completed"
