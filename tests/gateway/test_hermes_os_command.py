"""Tests for the Hermes OS gateway command activation flow."""

from types import SimpleNamespace
from unittest.mock import patch
import json

import pytest

import gateway.run as gateway_run
from gateway.config import Platform
from gateway.platforms.base import MessageEvent
from gateway.session import SessionSource


def _make_event(text="/hermes_os", platform=Platform.TELEGRAM, user_id="12345", chat_id="67890"):
    source = SessionSource(
        platform=platform,
        user_id=user_id,
        chat_id=chat_id,
        user_name="testuser",
    )
    return MessageEvent(text=text, source=source)


def _make_runner(tmp_path):
    runner = object.__new__(gateway_run.GatewayRunner)
    runner._hermes_os_mode = {}
    runner._HERMES_OS_MODE_PATH = tmp_path / "gateway_hermes_os_mode.json"
    runner._session_db = None
    runner.session_store = SimpleNamespace(load_transcript=lambda _session_id: [])
    return runner


@pytest.fixture
def runner(tmp_path):
    return _make_runner(tmp_path)


@pytest.mark.asyncio
async def test_root_command_activates_hermes_os_mode_and_reports_ready(runner):
    """The root Telegram command should activate Hermes OS immediately."""
    event = _make_event("/hermes_os")

    fake_stdout = "🛰️ Hermes OS\n✓ Hermes OS mode: ON\n  Mode: hermes_os\n  RTK: enabled\n"
    fake_result = SimpleNamespace(returncode=0, stdout=fake_stdout, stderr="")

    with patch("subprocess.run", return_value=fake_result) as mock_run:
        result = await runner._handle_hermes_os_command(event)

    assert mock_run.call_count == 1
    assert mock_run.call_args.args[0] == ["hermes-os", "on"]
    assert "Mode: hermes_os" in result
    assert "ready to work" in result.lower()
    assert "Hermes OS context active" in result
    assert "Direct execution remains the default" in result
    assert "Fleet runs only on explicit" in result
    assert "bound to Hermes OS mode" not in result
    assert runner._hermes_os_mode["67890"] == "on"
    persisted = json.loads(runner._HERMES_OS_MODE_PATH.read_text())
    assert persisted == {"67890": "on"}


@pytest.mark.asyncio
async def test_explicit_off_disables_and_persists(runner):
    """Explicit /hermes_os off should disable the chat binding."""
    runner._hermes_os_mode["67890"] = "on"
    event = _make_event("/hermes_os off")

    fake_stdout = "🛰️ Hermes OS\n✗ Hermes OS mode: OFF\n  Mode: hermes_off\n"
    fake_result = SimpleNamespace(returncode=0, stdout=fake_stdout, stderr="")

    with patch("subprocess.run", return_value=fake_result) as mock_run:
        result = await runner._handle_hermes_os_command(event)

    assert mock_run.call_count == 1
    assert mock_run.call_args.args[0] == ["hermes-os", "off"]
    assert "disabled for this chat" in result.lower()
    assert runner._hermes_os_mode["67890"] == "off"
    persisted = json.loads(runner._HERMES_OS_MODE_PATH.read_text())
    assert persisted == {"67890": "off"}


@pytest.mark.asyncio
async def test_explicit_status_reports_chat_binding_state(runner):
    """Explicit /hermes_os status should report chat binding state."""
    runner._hermes_os_mode["67890"] = "on"
    event = _make_event("/hermes_os status")

    fake_stdout = "Status:\n  Mode: hermes_os\n  Gateway: running\n"
    fake_result = SimpleNamespace(returncode=0, stdout=fake_stdout, stderr="")

    with patch("subprocess.run", return_value=fake_result) as mock_run:
        result = await runner._handle_hermes_os_command(event)

    assert mock_run.call_count == 1
    assert mock_run.call_args.args[0] == ["hermes-os", "status"]
    assert "Mode: hermes_os" in result
    assert "Hermes OS context is active for this chat" in result
    assert "Direct execution remains the default" in result
    assert "ready to work" not in result.lower()


def test_restart_loads_persisted_mode(tmp_path):
    """Gateway restart should restore persisted Hermes OS mode state."""
    runner = _make_runner(tmp_path)
    runner._HERMES_OS_MODE_PATH.write_text(json.dumps({"123": "on", "456": "off", "789": "bogus"}))

    loaded = runner._load_hermes_os_modes()

    assert loaded == {"123": "on", "456": "off"}


def test_injects_hermes_os_skill_once_per_session(runner):
    """Active chat should inject Hermes OS skill once until transcript already has it."""
    runner._hermes_os_mode["67890"] = "on"
    event = _make_event("Please help me plan this")

    injected = runner._inject_hermes_os_mode_if_needed(event, [], "session-1")

    assert injected is True
    assert 'Hermes OS context is active for this chat' in event.text
    assert 'direct execution remains the default' in event.text.lower()
    assert 'do not auto-route normal messages' in event.text.lower()
    assert 'thClaws and OMX are execution limbs' in event.text
    assert '/hermes-os' in event.text

    # Once the transcript already contains the injected skill marker, skip it.
    history = [{"role": "user", "content": event.text}]
    second = _make_event("Try again")
    injected_again = runner._inject_hermes_os_mode_if_needed(second, history, "session-1")

    assert injected_again is False
    assert second.text == "Try again"
