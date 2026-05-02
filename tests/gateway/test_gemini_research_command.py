"""Tests for the Gemini research workflow gateway command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from hermes_cli.gemini_workflow import GeminiWorkflowResult


class TestGeminiResearchGatewayCommand:
    @pytest.mark.asyncio
    async def test_gateway_command_returns_summary_when_available(self):
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
        event.get_command_args.return_value = '--question "What changed?" --evidence "docs updated\ncommand added"'
        event.source = SimpleNamespace(
            platform=SimpleNamespace(value="telegram"),
            user_id="123456789",
            user_name="Boss",
            chat_id="123456789",
            chat_type="dm",
            thread_id=None,
        )

        workflow_result = GeminiWorkflowResult(
            available=True,
            question="What changed?",
            evidence="docs updated\ncommand added",
            summary="summary: docs updated\nclaims: - command added\nassumptions: none\nverification_risk: low",
            verification_prompt="Verify the Gemini summary against the evidence.",
            reason="",
            binary="/usr/bin/gemini",
            model="gemini-2.5-flash",
            exit_code=0,
        )

        with patch("hermes_cli.gemini_workflow.run_gemini_research_workflow", return_value=workflow_result):
            result = await runner._handle_gemini_research_command(event)

        assert "Gemini workflow summary" in result
        assert "verification_prompt" in result

    @pytest.mark.asyncio
    async def test_gateway_command_falls_back_to_hermes_when_gemini_unavailable(self):
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
        event.get_command_args.return_value = '--question "What changed?" --evidence "docs updated\ncommand added"'
        event.source = SimpleNamespace(
            platform=SimpleNamespace(value="telegram"),
            user_id="123456789",
            user_name="Boss",
            chat_id="123456789",
            chat_type="dm",
            thread_id=None,
        )

        workflow_result = GeminiWorkflowResult(
            available=False,
            question="What changed?",
            evidence="docs updated\ncommand added",
            reason="gemini binary not found",
            fallback_prompt="Gemini CLI is unavailable. Hermes OS should answer natively using the evidence below.",
            binary="",
            model="gemini-2.5-flash",
            exit_code=None,
        )

        with patch("hermes_cli.gemini_workflow.run_gemini_research_workflow", return_value=workflow_result):
            result = await runner._handle_gemini_research_command(event)

        assert "Gemini workflow fallback to Hermes OS" in result
        assert "Hermes OS should answer natively" in result
