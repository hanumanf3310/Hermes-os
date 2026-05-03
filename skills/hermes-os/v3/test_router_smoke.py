import types

from v3.analyzer import TaskAnalyzer
from v3.router import Phase3RoutingAdapter


def test_phase3_router_maps_direct_and_direct_with_suggestion():
    adapter = Phase3RoutingAdapter(analyzer=TaskAnalyzer())

    direct = adapter.analyze("Hello")
    assert direct.route.value == "hermes_direct"
    assert direct.phase3["raw_route"] == "direct"

    suggestive = adapter.analyze("Refactor all files in the project")
    assert suggestive.route.value == "hermes_direct"
    assert suggestive.phase3["raw_route"] == "direct_with_suggestion"


def test_phase3_router_maps_fleet():
    adapter = Phase3RoutingAdapter(analyzer=TaskAnalyzer())
    fleet = adapter.analyze("Build a web app with React, Node.js, and database")
    assert fleet.route.value == "fleet_complex"
    assert fleet.phase3["raw_route"] == "fleet"
    assert fleet.phase3["score"] >= 8


def test_hermes_os_execute_respects_analyze_only():
    from hermes_os import HermesOS

    os = HermesOS()
    os.phase3_config["analyze_only"] = True
    os.phase3_config["auto_route_enabled"] = False
    result = os.execute("Create a Python script to rename files", {"boss_id": "test-boss"})

    assert result["route"] == "hermes_direct"
    assert result["result"]["via"] == "hermes_direct"


def test_hermes_os_execute_routes_fleet_when_auto_enabled_with_fake_fleet(monkeypatch):
    from hermes_os import HermesOS

    class FakeFleet:
        def __init__(self):
            self.main_agents = 1
            self.sub_agents = 1
            self.calls = []

        def execute_task(self, task_description, division=None, safety_critical=False, context=None):
            self.calls.append((task_description, division, safety_critical, context))
            return {
                "status": "completed",
                "result": {
                    "via": "fleet",
                    "division": division,
                    "safety_critical": safety_critical,
                },
                "execution_time_seconds": 0.0,
                "safety_passed": True,
                "qa_passed": True,
            }

        def health(self):
            return {"ok": True}

    os = HermesOS()
    os.phase3_config["analyze_only"] = False
    os.phase3_config["auto_route_enabled"] = True
    os.phase3_config["auto_route_threshold"] = 0.0
    os.fleet = FakeFleet()

    result = os.execute("Build a web app with React, Node.js, and database", {"boss_id": "test-boss"})

    assert result["route"] == "fleet_complex"
    assert result["result"]["via"] == "fleet"
    assert os.fleet.calls, "Expected fake fleet to be invoked"


def test_hermes_os_status_includes_phase3_contract():
    from hermes_os import HermesOS

    os = HermesOS()

    status = os.status()
    phase3 = status.get("phase3", {})

    assert phase3.get("enabled") is True
    assert "analyze_only" in phase3
    assert "auto_route_enabled" in phase3
    assert "auto_route_threshold" in phase3


def test_hermes_os_execute_uses_manual_override_prefix_for_fleet():
    from hermes_os import HermesOS

    class FakeFleet:
        def __init__(self):
            self.calls = 0

        def execute_task(self, task_description, division=None, safety_critical=False, context=None):
            self.calls += 1
            return {
                "status": "completed",
                "result": {
                    "via": "fleet",
                    "division": division,
                    "safety_critical": safety_critical,
                },
                "execution_time_seconds": 0.0,
                "safety_passed": True,
                "qa_passed": True,
                "route": "fleet_complex",
                "routing_contract": {"execution_decision": "fleet_complex"},
            }

        def health(self):
            return {"ok": True}

    os = HermesOS()
    os.phase3_config["analyze_only"] = True
    os.phase3_config["auto_route_enabled"] = False
    os.phase3_config["manual_override_prefixes"] = ["/fleet", "/hermes-os fleet", "/hermes-os"]
    os.fleet = FakeFleet()

    result = os.execute("/fleet build a dashboard", {"boss_id": "test-boss"})

    assert result["route"] == "fleet_complex"
    assert result["result"]["via"] == "fleet"
    assert os.fleet.calls == 1
