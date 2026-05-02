"""CLI compatibility wrappers for Codex GPT status bridge.

The implementation lives in :mod:`gateway.codex_bridge`; this module keeps the
older ``hermes_cli.codex_bridge`` import surface used by CLI/Gateway handlers.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from gateway.codex_bridge import CodexStatusBridge


def get_codex_status_via_exec(timeout: int = 60) -> Optional[Dict[str, Any]]:
    return CodexStatusBridge().get_status()


def compare_plans() -> Dict[str, Any]:
    from gateway import codex_bridge as _gateway_codex_bridge
    return _gateway_codex_bridge.compare_plans()


def format_status_markdown(data: Optional[Dict[str, Any]], show_source: bool = True, debug: bool = False) -> str:
    if not data:
        return (
            "🤖 **Codex GPT Status**\n\n"
            "Unable to retrieve live Codex status.\n"
            "Stale cached/session fallback is disabled.\n"
            "Source: codex exec live probe"
        )
    lines = [
        "🤖 **Codex GPT Status**",
        "",
        "📊 **Context Usage**",
        f"   {data.get('context_left_pct', 0)}% remaining ({int(data.get('context_used', 0)):,} / {int(data.get('context_window', 0)):,} tokens)",
        "",
        "⏱️ **5h Limit**",
        f"   Used: {float(data.get('used_5h_pct', 0)):.0f}% ({float(data.get('left_5h_pct', 0)):.0f}% remaining)",
        f"   Reset: {data.get('reset_5h', 'unknown')}",
        "",
        "📅 **7d Limit**",
        f"   Used: {float(data.get('used_7d_pct', 0)):.0f}% ({float(data.get('left_7d_pct', 0)):.0f}% remaining)",
        f"   Reset: {data.get('reset_7d', 'unknown')}",
        "",
        f"💎 Plan: {str(data.get('plan_type', 'unknown')).upper()}",
    ]
    if show_source:
        lines.append(f"📁 Source: {data.get('source', 'unknown')}")
    lines.append("🔎 Verify: https://chatgpt.com/codex/cloud/settings/analytics#usage")
    return "\n".join(lines)


def format_status_rich(data: Optional[Dict[str, Any]], show_source: bool = True, debug: bool = False) -> str:
    if not data:
        return (
            "🤖 Codex GPT Status\n\n"
            "Unable to retrieve live Codex status.\n"
            "Stale cached/session fallback is disabled.\n"
            "Source: codex exec live probe"
        )
    lines = [
        "🤖 Codex GPT Status",
        "",
        "📊 Context Usage",
        f"   {data.get('context_left_pct', 0)}% เหลือ ({int(data.get('context_used', 0)):,} / {int(data.get('context_window', 0)):,} tokens)",
        "",
        "5h Limit",
        f"   ใช้ไป: {float(data.get('used_5h_pct', 0)):.0f}% (เหลือ {float(data.get('left_5h_pct', 0)):.0f}%)",
        f"   รีเซ็ต: {data.get('reset_5h', 'unknown')}",
        "",
        "7d Limit",
        f"   ใช้ไป: {float(data.get('used_7d_pct', 0)):.0f}% (เหลือ {float(data.get('left_7d_pct', 0)):.0f}%)",
        f"   รีเซ็ต: {data.get('reset_7d', 'unknown')}",
        "",
        f"💎 Plan: {str(data.get('plan_type', 'unknown')).upper()}",
    ]
    if show_source:
        lines.append(f"📁 Source: {data.get('source', 'unknown')}")
    lines.append("🔎 Verify: https://chatgpt.com/codex/cloud/settings/analytics#usage")
    return "\n".join(lines)


def format_comparison_markdown(result: Dict[str, Any]) -> str:
    plan_a = result.get("plan_a", {}) if isinstance(result, dict) else {}
    plan_b = result.get("plan_b", {}) if isinstance(result, dict) else {}
    winner = result.get("winner", "N/A") if isinstance(result, dict) else "N/A"
    speedup = result.get("speedup", "N/A") if isinstance(result, dict) else "N/A"
    return "\n".join([
        "🔬 **A/B Test: เปรียบเทียบ Plan A กับ Plan B**",
        "",
        "**Plan A (Real-time Direct):**",
        f"   Status: {'OK' if plan_a.get('success') else 'FAIL'}",
        f"   Latency: {plan_a.get('latency_ms', 'n/a')} ms",
        f"📁 Source: {(plan_a.get('data') or {}).get('source', 'unknown')}",
        "",
        "**Plan B (File Bridge):**",
        f"   Status: {'OK' if plan_b.get('success') else 'FAIL'}",
        f"   Latency: {plan_b.get('latency_ms', 'n/a')} ms",
        f"📁 Source: {(plan_b.get('data') or {}).get('source', 'unknown')}",
        "",
        f"🏆 **Winner:** Plan {winner} ({speedup}x faster)",
    ])


def format_comparison_rich(result: Dict[str, Any]) -> str:
    plan_a = result.get("plan_a", {}) if isinstance(result, dict) else {}
    plan_b = result.get("plan_b", {}) if isinstance(result, dict) else {}
    winner = result.get("winner", "N/A") if isinstance(result, dict) else "N/A"
    speedup = result.get("speedup", "N/A") if isinstance(result, dict) else "N/A"
    return "\n".join([
        "🔬 A/B Test: Plan A vs Plan B",
        "",
        f"PLAN A: {'OK' if plan_a.get('success') else 'FAIL'} ({plan_a.get('latency_ms', 'n/a')} ms)",
        f"Source: {(plan_a.get('data') or {}).get('source', 'unknown')}",
        "",
        f"PLAN B: {'OK' if plan_b.get('success') else 'FAIL'} ({plan_b.get('latency_ms', 'n/a')} ms)",
        f"Source: {(plan_b.get('data') or {}).get('source', 'unknown')}",
        "",
        f"🏆 Winner: Plan {winner} ({speedup}x faster)",
    ])
