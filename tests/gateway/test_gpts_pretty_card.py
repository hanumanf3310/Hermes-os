import asyncio
from unittest.mock import AsyncMock

import pytest

import cli as cli_mod
import gateway.codex_bridge as codex_bridge
import gateway.run as gateway_run
from gateway.config import Platform
from gateway.platforms.base import MessageEvent
from gateway.session import SessionSource
from hermes_cli.commands import COMMAND_REGISTRY, resolve_command


def test_gpts_command_registered_for_gateway_and_cli():
    names = {cmd.name for cmd in COMMAND_REGISTRY}
    assert "gpts" in names
    assert resolve_command("gpts").name == "gpts"
    assert resolve_command("/gpts").name == "gpts"
    assert hasattr(gateway_run.GatewayRunner, "_handle_gpts_command")
    assert hasattr(cli_mod.HermesCLI, "_handle_gpts_command")


def _make_event(text: str = "/gpts --plan A --debug") -> MessageEvent:
    return MessageEvent(text=text, source=SessionSource(platform=Platform.TELEGRAM, user_id="123", chat_id="456"))


def _fake_status(plan: str = "A", source: str = "session_files"):
    return {
        "context_used": 36745,
        "context_window": 258400,
        "context_left_pct": 86,
        "used_5h_pct": 69,
        "left_5h_pct": 31,
        "reset_5h": "11:37 PM",
        "used_7d_pct": 63,
        "left_7d_pct": 37,
        "reset_7d": "2026-04-26 11:59 PM",
        "plan_type": "plus",
        "source": source,
        "plan": plan,
        "latency_ms": 0.31,
    }


@pytest.mark.asyncio
async def test_gateway_gpts_status_returns_pretty_card(monkeypatch):
    monkeypatch.setattr(codex_bridge.CodexStatusBridge, "get_status", lambda self: _fake_status())

    runner = object.__new__(gateway_run.GatewayRunner)
    result = await runner._handle_gpts_command(_make_event())

    assert "🤖 **Codex GPT Status**" in result
    assert "📊 **Context Usage**" in result
    assert "86% remaining" in result
    assert "⏱️ **5h Limit**" in result
    assert "📅 **7d Limit**" in result
    assert "2026-04-26 11:59 PM" in result
    assert "💎 Plan: PLUS" in result
    assert "https://chatgpt.com/codex/cloud/settings/analytics#usage" in result


@pytest.mark.asyncio
async def test_gateway_gpts_compare_returns_pretty_card(monkeypatch):
    async def fake_compare(self):
        return {
            "plan_a": {
                "plan": "A",
                "success": True,
                "latency_ms": 0.31,
                "data": _fake_status(plan="A", source="session_files"),
                "error": None,
            },
            "plan_b": {
                "plan": "B",
                "success": True,
                "latency_ms": 0.53,
                "data": _fake_status(plan="B", source="cache"),
                "error": None,
            },
            "winner": "A",
            "speedup": 1.71,
            "cache_ttl_seconds": 300,
            "generated_at": "2026-04-24T00:00:00+07:00",
        }

    monkeypatch.setattr(codex_bridge.CodexStatusBridge, "compare_plans_async", fake_compare)

    runner = object.__new__(gateway_run.GatewayRunner)
    result = await runner._handle_gpts_command(_make_event("/gpts --compare"))

    assert "🔬 **A/B Test: เปรียบเทียบ Plan A กับ Plan B**" in result
    assert "**Plan A (Real-time Direct):**" in result
    assert "📁 Source: session_files" in result
    assert "**Plan B (File Bridge):**" in result
    assert "📁 Source: cache" in result
    assert "🏆 **Winner:** Plan A (1.71x faster)" in result


def test_cli_gpts_status_prints_pretty_card(monkeypatch):
    monkeypatch.setattr(codex_bridge.CodexStatusBridge, "get_status", lambda self: _fake_status())

    cli = object.__new__(cli_mod.HermesCLI)
    lines = []
    cli._console_print = lambda *args, **kwargs: lines.append(" ".join(str(arg) for arg in args) if args else "")

    cli._handle_gpts_command("/gpts --plan A --debug")

    output = "\n".join(lines)
    assert "🤖 Codex GPT Status" in output
    assert "📊 Context Usage" in output
    assert "86% เหลือ" in output
    assert "5h Limit" in output
    assert "7d Limit" in output
    assert "2026-04-26 11:59 PM" in output
    assert "💎 Plan: PLUS" in output
    assert "https://chatgpt.com/codex/cloud/settings/analytics#usage" in output


def test_cli_gpts_compare_prints_pretty_card(monkeypatch):
    monkeypatch.setattr(
        codex_bridge,
        "compare_plans",
        lambda: {
            "plan_a": {
                "plan": "A",
                "success": True,
                "latency_ms": 0.31,
                "data": _fake_status(plan="A", source="session_files"),
                "error": None,
            },
            "plan_b": {
                "plan": "B",
                "success": True,
                "latency_ms": 0.53,
                "data": _fake_status(plan="B", source="cache"),
                "error": None,
            },
            "winner": "A",
            "speedup": 1.71,
            "cache_ttl_seconds": 300,
            "generated_at": "2026-04-24T00:00:00+07:00",
        },
    )

    cli = object.__new__(cli_mod.HermesCLI)
    lines = []
    cli._console_print = lambda *args, **kwargs: lines.append(" ".join(str(arg) for arg in args) if args else "")

    cli._handle_gpts_command("/gpts --compare")

    output = "\n".join(lines)
    assert "🔬 A/B Test: Plan A vs Plan B" in output
    assert "PLAN A" in output
    assert "PLAN B" in output
    assert "🏆 Winner: Plan A (1.71x faster)" in output
