"""Tests for the Hermes Memory Graph gateway command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


class TestHermesMemoryGraphGatewayCommand:
    @pytest.mark.asyncio
    async def test_gateway_handler_returns_public_link(self):
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
        event.get_command.return_value = "hermes_memory_graph"
        event.get_command_args.return_value = ""
        event.source = SimpleNamespace(
            platform=SimpleNamespace(value="telegram"),
            user_id="123456789",
            user_name="Boss",
            chat_id="123456789",
            chat_type="dm",
            thread_id=None,
        )

        status = {
            "already_running": True,
            "public_dashboard_url": "https://reveals-sit-considering-edward.trycloudflare.com/dashboard.html",
            "local_dashboard_url": "http://127.0.0.1:9130/dashboard.html",
            "api_url": "http://127.0.0.1:9130/api/fact-graph",
        }

        with patch("hermes_cli.memory_graph.ensure_memory_graph_ready", return_value=status):
            result = await runner._handle_memory_graph_command(event)

        assert "https://reveals-sit-considering-edward.trycloudflare.com/dashboard.html" in result
        assert "http://127.0.0.1:9130/api/fact-graph" in result
