"""Tests for the checkpoint / go-no-go gateway command."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from hermes_cli.checkpoint_gate import CheckpointRequest, format_checkpoint_result, run_checkpoint_gate


class TestCheckpointGatewayCommand:
    @pytest.mark.asyncio
    async def test_gateway_command_returns_decision_card(self):
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
        event.get_command_args.return_value = '--goal "Finish dashboard" --current "audited current page" --evidence "browser console + tests"'
        event.source = SimpleNamespace(
            platform=SimpleNamespace(value="telegram"),
            user_id="123456789",
            user_name="Boss",
            chat_id="123456789",
            chat_type="dm",
            thread_id=None,
        )

        result = await runner._handle_checkpoint_command(event)

        assert "Checkpoint / Go-No-Go" in result
        assert "Decision: GO" in result
        assert "Finish dashboard" in result

    @pytest.mark.asyncio
    async def test_gateway_command_returns_usage_when_empty(self):
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
        event.get_command_args.return_value = ""
        event.source = SimpleNamespace(
            platform=SimpleNamespace(value="telegram"),
            user_id="123456789",
            user_name="Boss",
            chat_id="123456789",
            chat_type="dm",
            thread_id=None,
        )

        result = await runner._handle_checkpoint_command(event)

        assert "Usage: /checkpoint" in result
        assert "GO = continue" in result
