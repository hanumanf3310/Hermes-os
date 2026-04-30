"""Regression tests for Hermes OS chat context binding after router retirement."""

from types import SimpleNamespace
from unittest.mock import MagicMock
import json
import subprocess

import pytest

import gateway.run as gateway_run
from gateway.config import Platform
from gateway.platforms.base import MessageEvent
from gateway.session import SessionSource


def _make_event(text="/hermes_os", user_id="12345", chat_id="67890"):
    source = SessionSource(
        platform=Platform.TELEGRAM,
        user_id=user_id,
        chat_id=chat_id,
        user_name="Boss",
    )
    return MessageEvent(text=text, source=source)


def _make_runner(tmp_path, monkeypatch, global_mode="hermes_os"):
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir(parents=True, exist_ok=True)
    state_dir = hermes_home / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    mode_path = hermes_home / "gateway_hermes_os_mode.json"
    state_path = state_dir / "hermes-os.json"
    if global_mode is not None:
        state_path.write_text(json.dumps({"mode": global_mode, "rtk_enabled": global_mode == "hermes_os"}))
    monkeypatch.setattr(gateway_run.GatewayRunner, "_HERMES_OS_MODE_PATH", mode_path)
    monkeypatch.setattr(gateway_run.GatewayRunner, "_HERMES_OS_STATE_PATH", state_path, raising=False)

    runner = object.__new__(gateway_run.GatewayRunner)
    runner.session_store = None
    runner.config = SimpleNamespace(
        group_sessions_per_user=True,
        thread_sessions_per_user=False,
    )
    runner.adapters = {}
    runner.hooks = MagicMock()
    runner._hermes_os_mode = runner._load_hermes_os_modes()
    return runner, mode_path


@pytest.mark.asyncio
async def test_bare_hermes_os_command_activates_context_binding(tmp_path, monkeypatch):
    """Bare /hermes_os is an activation command, not a status command."""
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="Mode: hermes_os", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner, mode_path = _make_runner(tmp_path, monkeypatch)

    result = await runner._handle_hermes_os_command(_make_event("/hermes_os"))

    assert calls == [["hermes-os", "on"]]
    assert "Hermes OS context active for this chat" in result
    assert "Direct execution remains the default" in result
    assert "Fleet runs only on explicit /fleet or /hermes_os fleet commands" in result
    assert json.loads(mode_path.read_text()) == {"67890": "on"}


@pytest.mark.asyncio
async def test_hermes_os_status_reports_context_binding_without_enabling(tmp_path, monkeypatch):
    """Status reports runtime/chat state; it must not activate a chat by accident."""
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="Mode: hermes_os", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner, mode_path = _make_runner(tmp_path, monkeypatch)

    result = await runner._handle_hermes_os_command(_make_event("/hermes_os status"))

    assert calls == [["hermes-os", "status"]]
    assert "Hermes OS context is not active for this chat" in result
    assert not mode_path.exists()


@pytest.mark.asyncio
async def test_hermes_os_off_clears_context_binding(tmp_path, monkeypatch):
    """Turning Hermes OS off clears the per-chat context binding."""

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="Mode: hermes_off", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner, mode_path = _make_runner(tmp_path, monkeypatch)
    runner._set_hermes_os_mode("67890", "on")

    result = await runner._handle_hermes_os_command(_make_event("/hermes_os off"))

    assert "Hermes OS mode disabled for this chat" in result
    assert json.loads(mode_path.read_text()) == {"67890": "off"}


def test_context_binding_survives_runner_reload(tmp_path, monkeypatch):
    """Persisted chat context binding is loaded by a fresh gateway runner."""
    runner, mode_path = _make_runner(tmp_path, monkeypatch)
    runner._set_hermes_os_mode("67890", "on")

    reloaded = object.__new__(gateway_run.GatewayRunner)
    reloaded._hermes_os_mode = reloaded._load_hermes_os_modes()

    assert json.loads(mode_path.read_text()) == {"67890": "on"}
    assert reloaded._hermes_os_mode_for_chat("67890") == "on"


def test_bound_normal_message_injects_context_once_without_auto_routing(tmp_path, monkeypatch):
    """Normal chat stays direct; binding only injects Hermes OS policy/control context."""
    from agent import skill_commands

    def fake_build_skill_invocation_message(cmd_key, user_instruction="", task_id=None, runtime_note=""):
        assert cmd_key == "/hermes-os"
        assert user_instruction == "ช่วยดูสถานะให้หน่อย"
        assert task_id == "telegram:67890"
        return (
            '[SYSTEM: The user has invoked the "hermes-os" skill]\n'
            f"[Runtime note: {runtime_note}]\n"
            f"{user_instruction}"
        )

    monkeypatch.setattr(skill_commands, "build_skill_invocation_message", fake_build_skill_invocation_message)
    runner, _ = _make_runner(tmp_path, monkeypatch)
    runner._set_hermes_os_mode("67890", "on")
    event = _make_event("ช่วยดูสถานะให้หน่อย")

    injected = runner._inject_hermes_os_mode_if_needed(event, history=[], session_key="telegram:67890")

    assert injected is True
    assert '[SYSTEM: The user has invoked the "hermes-os" skill' in event.text
    assert "Hermes OS context is active for this chat" in event.text
    assert "direct execution remains the default" in event.text
    assert "Do not auto-route normal messages" in event.text
    assert "ช่วยดูสถานะให้หน่อย" in event.text

    second_event = _make_event("ข้อความถัดไป")
    injected_again = runner._inject_hermes_os_mode_if_needed(
        second_event,
        history=[{"role": "user", "content": event.text}],
        session_key="telegram:67890",
    )

    assert injected_again is False
    assert second_event.text == "ข้อความถัดไป"


def test_global_off_blocks_chat_on_context_injection(tmp_path, monkeypatch):
    """Global OFF is the fail-closed source of truth even if a chat binding says ON."""
    runner, _ = _make_runner(tmp_path, monkeypatch, global_mode="hermes_off")
    runner._set_hermes_os_mode("67890", "on")
    event = _make_event("ช่วยดูสถานะให้หน่อย")

    injected = runner._inject_hermes_os_mode_if_needed(event, history=[], session_key="telegram:67890")

    assert injected is False
    assert event.text == "ช่วยดูสถานะให้หน่อย"


def test_missing_global_state_fails_closed_for_context_injection(tmp_path, monkeypatch):
    """Missing global state must not allow a stale chat binding to inject Hermes OS context."""
    runner, _ = _make_runner(tmp_path, monkeypatch, global_mode=None)
    runner._set_hermes_os_mode("67890", "on")
    event = _make_event("ช่วยดูสถานะให้หน่อย")

    injected = runner._inject_hermes_os_mode_if_needed(event, history=[], session_key="telegram:67890")

    assert injected is False
    assert event.text == "ช่วยดูสถานะให้หน่อย"


def test_global_on_chat_off_does_not_inject_context(tmp_path, monkeypatch):
    """Chat binding remains an opt-in under a globally enabled Hermes OS mode."""
    runner, _ = _make_runner(tmp_path, monkeypatch, global_mode="hermes_os")
    runner._set_hermes_os_mode("67890", "off")
    event = _make_event("ช่วยดูสถานะให้หน่อย")

    injected = runner._inject_hermes_os_mode_if_needed(event, history=[], session_key="telegram:67890")

    assert injected is False
    assert event.text == "ช่วยดูสถานะให้หน่อย"


@pytest.mark.asyncio
async def test_hermes_os_status_reports_global_and_chat_effective_state(tmp_path, monkeypatch):
    """Status reports global mode, chat binding, and effective context without enabling a chat."""
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="Mode: hermes_off", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner, mode_path = _make_runner(tmp_path, monkeypatch, global_mode="hermes_off")
    runner._set_hermes_os_mode("67890", "on")

    result = await runner._handle_hermes_os_command(_make_event("/hermes_os status"))

    assert calls == [["hermes-os", "status"]]
    assert "Global mode: OFF" in result
    assert "This chat: ON" in result
    assert "Effective context: BLOCKED by global mode" in result
    assert json.loads(mode_path.read_text()) == {"67890": "on"}


def test_hermes_os_response_includes_emoji_prefix_when_active(tmp_path, monkeypatch):
    """Responses should include 🛡️ prefix when Hermes OS is active for the chat."""
    runner, _ = _make_runner(tmp_path, monkeypatch, global_mode="hermes_os")
    chat_id = "1002"

    # Not active (chat binding off) - no prefix
    assert runner._is_hermes_os_active_for_chat(chat_id) is False
    response = runner._format_response_with_hermes_os_prefix("Hello Boss", chat_id)
    assert not response.startswith("🛡️")

    # Activate chat binding
    runner._set_hermes_os_mode(chat_id, "on")
    assert runner._is_hermes_os_active_for_chat(chat_id) is True

    # Active - should have prefix
    response = runner._format_response_with_hermes_os_prefix("Hello Boss", chat_id)
    assert response.startswith("🛡️")
    assert response == "🛡️ Hello Boss"

    # Double prefix prevention
    response2 = runner._format_response_with_hermes_os_prefix(response, chat_id)
    assert response2 == "🛡️ Hello Boss"  # No double emoji

    # Empty string handling
    assert runner._format_response_with_hermes_os_prefix("", chat_id) == ""
