from types import SimpleNamespace

import pytest

import gateway.run as gateway_run
from gateway.config import Platform
from gateway.platforms.base import MessageEvent
from gateway.session import SessionSource

from hermes_cli.core_update_impact_gate import CoreUpdateImpactRequest, CoreUpdateImpactResult


def _make_event(text="/hermes-core-update-impact-gate", user_id="12345", chat_id="67890"):
    source = SessionSource(
        platform=Platform.TELEGRAM,
        user_id=user_id,
        chat_id=chat_id,
        user_name="Boss",
    )
    return MessageEvent(text=text, source=source)


@pytest.mark.asyncio
async def test_core_update_impact_gate_handler_returns_report(monkeypatch):
    runner = object.__new__(gateway_run.GatewayRunner)
    runner.name = "test"
    runner.session_store = None
    runner.config = SimpleNamespace(group_sessions_per_user=True, thread_sessions_per_user=False)
    runner.adapters = {}
    runner.hooks = SimpleNamespace()

    import hermes_cli.core_update_impact_gate as helper

    monkeypatch.setattr(helper, "parse_core_update_impact_request", lambda raw_args: (CoreUpdateImpactRequest(), None))
    monkeypatch.setattr(helper, "run_core_update_impact_gate", lambda request: CoreUpdateImpactResult(ok=True))
    monkeypatch.setattr(helper, "format_core_update_impact_result", lambda result: "GATE REPORT")

    result = await runner._handle_core_update_impact_gate_command(_make_event())

    assert result == "GATE REPORT"
