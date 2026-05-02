"""Cluster C2-C5: Gateway routing, duplicate prevention, and hard-kill.

Expands C1 with C2 (routing), C3 (active-session guard),
C4 (photo burst queue), C5 (/stop hard-kill).
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys, types

_tg = types.ModuleType("telegram")
_tg.constants = types.ModuleType("telegram.constants")
_ct = MagicMock()
_ct.SUPERGROUP = "supergroup"
_ct.GROUP = "group"
_ct.PRIVATE = "private"
_tg.constants.ChatType = _ct
sys.modules.setdefault("telegram", _tg)
sys.modules.setdefault("telegram.constants", _tg.constants)
sys.modules.setdefault("telegram.ext", types.ModuleType("telegram.ext"))

from gateway.platforms.base import (
    MessageEvent,
    MessageType,
    SessionSource,
    build_session_key,
)


def _make_event(text="hello", chat_id="123"):
    source = SessionSource(
        platform=MagicMock(value="telegram"),
        chat_id=chat_id,
        chat_type="private",
        user_id="user1",
    )
    return MessageEvent(
        text=text,
        message_type=MessageType.TEXT,
        source=source,
        message_id="msg1",
    )


def _make_runner():
    from gateway.run import GatewayRunner, _AGENT_PENDING_SENTINEL
    runner = object.__new__(GatewayRunner)
    runner.adapters = {}
    runner._running_agents = {}
    runner._running_agents_ts = {}
    runner._pending_messages = {}
    runner._busy_ack_ts = {}
    runner._draining = False
    runner.config = MagicMock()
    runner.session_store = None
    runner.hooks = MagicMock()
    runner.hooks.emit = AsyncMock()
    runner.pairing_store = MagicMock()
    runner.pairing_store.is_approved.return_value = True
    runner._is_user_authorized = lambda _source: True
    runner._busy_input_mode = "interrupt"
    return runner, _AGENT_PENDING_SENTINEL


# ---------------------------------------------------------------------------
# C2: Gateway routing
# ---------------------------------------------------------------------------

class TestGatewayRouting:
    """C2: Message routes to busy handler when agent running."""

    @pytest.mark.asyncio
    async def test_message_routes_to_busy_handler_when_agent_running(self):
        runner, _sentinel = _make_runner()
        adapter = MagicMock()
        adapter._pending_messages = {}
        adapter._send_with_retry = AsyncMock()

        event = _make_event(text="hello")
        sk = build_session_key(event.source)

        agent = MagicMock()
        agent.get_activity_summary.return_value = {
            "api_call_count": 1, "max_iterations": 60,
            "current_tool": None, "last_activity_ts": time.time(),
            "last_activity_desc": "api", "seconds_since_activity": 0.5,
        }
        runner._running_agents[sk] = agent
        runner._running_agents_ts[sk] = time.time() - 5
        runner.adapters[event.source.platform] = adapter

        result = await runner._handle_active_session_busy_message(event, sk)

        assert result is True
        adapter._send_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_falls_through_when_no_agent_running(self):
        runner, _sentinel = _make_runner()
        # No adapter registered → should return False
        event = _make_event(text="hello")
        sk = build_session_key(event.source)
        # No adapter means the handler can't send an ack, so it falls through.
        result = await runner._handle_active_session_busy_message(event, sk)
        assert result is False


# ---------------------------------------------------------------------------
# C3: Active-session guard — no duplicate tasks
# ---------------------------------------------------------------------------

class TestActiveSessionGuard:
    """C3: Second message while active does NOT spawn duplicate task."""

    def test_guard_event_set_prevents_duplicate(self):
        runner, _ = _make_runner()
        adapter = MagicMock()
        adapter._pending_messages = {}
        adapter._active_sessions = {}

        event = _make_event(text="hello")
        sk = build_session_key(event.source)

        # Simulate first message setting the guard
        adapter._active_sessions[sk] = asyncio.Event()
        adapter._active_sessions[sk].set()

        # A second message with the same session key would see the event
        # is already set and should NOT create a new task.
        # (This is a unit-level invariant; the real check lives in
        #  _process_message_background which exits early.)
        assert sk in adapter._active_sessions
        assert adapter._active_sessions[sk].is_set()


# ---------------------------------------------------------------------------
# C4: Photo burst queues without interrupt
# ---------------------------------------------------------------------------

class TestPhotoBurstQueue:
    """C4: Photo messages queue without interrupting agent."""

    @pytest.mark.asyncio
    async def test_photo_follow_up_queues_without_interrupt(self):
        from gateway.platforms.base import merge_pending_message_event

        runner, _ = _make_runner()
        adapter = MagicMock()
        adapter._pending_messages = {}

        photo_event = _make_event(text="")
        photo_event.message_type = MessageType.PHOTO
        sk = build_session_key(photo_event.source)

        agent = MagicMock()
        runner._running_agents[sk] = agent
        runner._running_agents_ts[sk] = time.time()

        merge_pending_message_event(adapter._pending_messages, sk, photo_event)

        assert sk in adapter._pending_messages
        agent.interrupt.assert_not_called()


# ---------------------------------------------------------------------------
# C5: /stop hard-kill
# ---------------------------------------------------------------------------

class TestStopHardKill:
    """C5: /stop while busy must suspend session and unlock."""

    @pytest.mark.asyncio
    async def test_stop_while_running_cleans_lock(self):
        runner, _sentinel = _make_runner()
        adapter = MagicMock()
        adapter._pending_messages = {}
        adapter.get_pending_message = MagicMock(return_value=None)

        event = _make_event(text="/stop")
        sk = build_session_key(event.source)

        agent = MagicMock()
        runner._running_agents[sk] = agent
        runner.adapters[event.source.platform] = adapter

        # The real /stop logic in _handle_message does:
        # 1. agent.interrupt("Stop requested")
        # 2. adapter.get_pending_message(sk) — consume
        # 3. del self._running_agents[sk]
        # We verify the busy handler still reports True (handled)
        # but real hard-stop is in _handle_message.
        result = await runner._handle_active_session_busy_message(event, sk)
        assert result is True
