"""Tests for the Gemini CLI gateway command and fallback routing."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


class _FakeProc:
    def __init__(self, returncode=0, stdout=b"GEMINI_OK", stderr=b""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self):
        return self._stdout, self._stderr


class TestGeminiCLIGatewayCommand:
    @pytest.mark.asyncio
    async def test_gateway_command_uses_gemini_when_available(self):
        from gateway.run import GatewayRunner

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.name = "telegram"
        runner.config = {}
        runner._draining = False
        runner._running_agents = {}
        runner._pending_messages = {}
        runner.adapters = {}
        runner.session_store = MagicMock()

        event = MagicMock()
        event.get_command_args.return_value = "Reply exactly: GEMINI_OK"
        event.text = ""
        event.source = SimpleNamespace(
            platform=SimpleNamespace(value="telegram"),
            user_id="123456789",
            user_name="Boss",
            chat_id="123456789",
            chat_type="dm",
            thread_id=None,
        )

        with patch("hermes_cli.gemini_cli.resolve_gemini_cli_binary", return_value="/usr/bin/gemini"), \
             patch("gateway.run.asyncio.create_subprocess_exec", return_value=_FakeProc()):
            result = await runner._handle_gemini_cli_command(event)

        assert result == "GEMINI_OK"

    @pytest.mark.asyncio
    async def test_gateway_command_falls_back_to_hermes_os_when_gemini_unavailable(self):
        from gateway.run import GatewayRunner

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.name = "telegram"
        runner.config = {}
        runner._draining = False
        runner._running_agents = {}
        runner._pending_messages = {}
        runner.adapters = {}
        runner.session_store = MagicMock()

        event = MagicMock()
        event.get_command_args.return_value = "Explain the change"
        event.source = SimpleNamespace(
            platform=SimpleNamespace(value="telegram"),
            user_id="123456789",
            user_name="Boss",
            chat_id="123456789",
            chat_type="dm",
            thread_id=None,
        )

        with patch("hermes_cli.gemini_cli.resolve_gemini_cli_binary", return_value=""):
            result = await runner._handle_gemini_cli_command(event)

        assert result is None
        assert event.text == "Explain the change"
