"""Shared Hermes OS user-facing message formatting.

Keep CLI and messaging gateway wording aligned for Hermes OS control commands.
"""

from __future__ import annotations

import re

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def strip_ansi(text: str) -> str:
    """Remove terminal ANSI color/control sequences from launcher output."""
    return _ANSI_RE.sub("", text or "").strip()


def _evidence_block(output: str) -> list[str]:
    clean = strip_ansi(output)
    if not clean:
        return []
    lines = ["", "📎 **Launcher evidence**"]
    for line in clean.splitlines():
        line = line.strip()
        if line:
            lines.append(f"  • {line}")
    return lines


def format_hermes_os_on_message(output: str = "", *, chat_scoped: bool = True) -> str:
    """Format Hermes OS activation/context-binding message."""
    scope = "for this chat" if chat_scoped else ""
    lines = [
        "🛰️ **Hermes OS Context**",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"✅ **Status:** Hermes OS context active {scope}".rstrip(),
        "🧠 **Role:** nervous/control layer for policy, memory, facts, learning, and controlled actions",
        "⚡ **Execution:** Direct execution remains the default",
        "🚀 **Fleet:** Fleet runs only on explicit /fleet or /hermes_os fleet commands",
        "🦾 **Limbs:** thClaws / OMX / Fleet adapters — not the core body",
        "🔒 **Policy:** RTK-first + UTC+7 + Evidence-first",
        "",
        "🤖 **Ready:** Boss น้องเมส พร้อมทำงานใน Hermes OS context แล้วค่ะ",
    ]
    lines.extend(_evidence_block(output))
    return "\n".join(lines)


def format_hermes_os_off_message(output: str = "", *, chat_scoped: bool = True) -> str:
    """Format Hermes OS context disable message."""
    scope = "for this chat" if chat_scoped else ""
    lines = [
        "🛰️ **Hermes OS Context**",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"🛑 **Status:** Hermes OS mode disabled {scope}".rstrip(),
        "⚡ **Execution:** Standard Hermes direct path remains available",
        "🔁 **Re-enable:** `/hermes_os` or `/hermes-os on`",
    ]
    lines.extend(_evidence_block(output))
    return "\n".join(lines)


def format_hermes_os_chat_status_note(active: bool) -> str:
    """Format chat-scoped context-binding note appended to status output."""
    if active:
        return "\n".join([
            "💬 **Chat Context Binding**",
            "━━━━━━━━━━━━━━━━━━━━━",
            "✅ Hermes OS context is active for this chat.",
            "⚡ Direct execution remains the default.",
            "🚀 Fleet runs only on explicit /fleet or /hermes_os fleet commands.",
        ])
    return "\n".join([
        "💬 **Chat Context Binding**",
        "━━━━━━━━━━━━━━━━━━━━━",
        "⚪ Hermes OS context is not active for this chat.",
        "🔁 Activate with `/hermes_os` or `/hermes-os on`.",
    ])


def format_hermes_os_effective_status(global_mode: str, chat_mode: str) -> str:
    """Format combined global + chat Hermes OS effective status."""
    global_on = global_mode == "hermes_os"
    chat_on = chat_mode == "on"
    if global_on and chat_on:
        effective = "ACTIVE"
        marker = "✅"
        detail = "Hermes OS context can be injected for this chat."
    elif not global_on:
        effective = "BLOCKED by global mode"
        marker = "🛡️"
        detail = "Fail-closed: global mode blocks chat context injection."
    else:
        effective = "INACTIVE for this chat"
        marker = "⚪"
        detail = "Hermes OS context is not active for this chat."

    return "\n".join([
        "💬 **Hermes OS Context Binding**",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"🌐 Global mode: {'ON' if global_on else 'OFF'} (`{global_mode}`)",
        f"💬 This chat: {'ON' if chat_on else 'OFF'} (`{chat_mode}`)",
        f"{marker} Effective context: {effective}",
        f"🧭 Meaning: {detail}",
        "⚡ **Execution:** Direct Hermes path remains default",
        "🚀 **Fleet:** Explicit /fleet or /hermes_os fleet only",
    ])
