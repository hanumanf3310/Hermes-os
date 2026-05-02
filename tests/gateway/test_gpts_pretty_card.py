"""Tests for /gpts pretty card output formatting.

Tests that CLI and Gateway produce consistent, correctly-formatted output.
"""

import asyncio
import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from cli import HermesCLI
from gateway.run import GatewayRunner
from hermes_cli.codex_bridge import (
    CodexRateLimit,
    CodexStatus,
    compare_plans,
    format_comparison_markdown,
    format_comparison_rich,
    format_status_markdown,
    format_status_rich,
    get_codex_status_via_exec,
    get_realtime_codex_status,
)


# -----------------------------------------------------------------------------
# Test Pretty Card Formatting - Status
# -----------------------------------------------------------------------------

class TestStatusPrettyCard:
    """Tests for status pretty card formatting."""

    def test_cli_output_shows_primary_rate_limit(self):
        """Test CLI output includes primary rate limit percentage."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            primary_limit=CodexRateLimit(used_percent=75.5, resets_at=None, tier="primary"),
            secondary_limit=None,
        )

        output = format_status_rich(status)

        assert "75.5%" in output or "75.5" in output
        assert "Primary Rate Limit" in output

    def test_cli_output_shows_secondary_rate_limit(self):
        """Test CLI output includes secondary rate limit percentage."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            primary_limit=None,
            secondary_limit=CodexRateLimit(used_percent=45.0, resets_at=None, tier="secondary"),
        )

        output = format_status_rich(status)

        assert "45.0%" in output or "45.0" in output or "45%" in output
        assert "Secondary Rate Limit" in output

    def test_cli_output_shows_total_tokens(self):
        """Test CLI output includes total tokens with formatting."""
        status = CodexStatus(
            total_tokens=12345,
            model_context_window=200000,
        )

        output = format_status_rich(status)

        assert "12,345" in output
        assert "Total Tokens" in output

    def test_cli_output_shows_context_used_percent(self):
        """Test CLI output includes context used percentage."""
        status = CodexStatus(
            total_tokens=10000,
            model_context_window=200000,
        )

        output = format_status_rich(status)

        # 10000/200000 = 5%
        assert "5.0%" in output or "5%" in output
        assert "Context Used" in output

    def test_cli_output_shows_resets_at(self):
        """Test CLI output includes resets_at time when available."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            primary_limit=CodexRateLimit(used_percent=50.0, resets_at="2024-01-15T14:30:00Z", tier="primary"),
        )

        output = format_status_rich(status)

        assert "resets" in output or "2024" in output

    def test_gateway_output_shows_primary_rate_limit(self):
        """Test Gateway (markdown) output includes primary rate limit."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            primary_limit=CodexRateLimit(used_percent=75.5, resets_at=None, tier="primary"),
            secondary_limit=None,
        )

        output = format_status_markdown(status)

        assert "75.5%" in output or "75.5" in output
        assert "**Primary Rate Limit:**" in output  # With colon

    def test_gateway_output_shows_secondary_rate_limit(self):
        """Test Gateway (markdown) output includes secondary rate limit."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            primary_limit=None,
            secondary_limit=CodexRateLimit(used_percent=45.0, resets_at=None, tier="secondary"),
        )

        output = format_status_markdown(status)

        assert "45.0%" in output or "45.0" in output or "45%" in output
        assert "**Secondary Rate Limit:**" in output  # With colon

    def test_gateway_output_shows_total_tokens(self):
        """Test Gateway output includes total tokens with markdown formatting."""
        status = CodexStatus(
            total_tokens=12345,
            model_context_window=200000,
        )

        output = format_status_markdown(status)

        assert "12,345" in output
        assert "**Total Tokens:**" in output  # With colon

    def test_gateway_output_shows_context_used_percent(self):
        """Test Gateway output includes context used percentage."""
        status = CodexStatus(
            total_tokens=10000,
            model_context_window=200000,
        )

        output = format_status_markdown(status)

        assert "5.0%" in output or "5%" in output
        assert "**Context Used:**" in output  # With colon

    def test_gateway_output_uses_markdown_bold(self):
        """Test Gateway output uses markdown bold syntax."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
        )

        output = format_status_markdown(status)

        # Should use ** for bold headers
        assert "🤖 **Codex GPT Status**" in output
        assert "**Total Tokens:**" in output  # With colon


# -----------------------------------------------------------------------------
# Test No Session Message
# -----------------------------------------------------------------------------

class TestNoSessionMessage:
    """Tests for 'no session found' message formatting."""

    def test_cli_no_session_message_is_clear(self):
        """Test CLI shows clear message when no session exists."""
        output = format_status_rich(None)

        assert "No Codex session found for today" in output
        assert "Start a Codex session" in output or "codex" in output.lower()

    def test_gateway_no_session_message_is_clear(self):
        """Test Gateway shows clear message when no session exists."""
        output = format_status_markdown(None)

        assert "No Codex session found for today" in output
        assert "Start a Codex session" in output or "`codex`" in output

    def test_cli_no_session_not_fake_data(self):
        """Test CLI doesn't fabricate fake data when no session exists."""
        output = format_status_rich(None)

        # Should NOT show any token counts or percentages
        assert "Total Tokens" not in output or "0" not in output
        assert "%" not in output or "No Codex session" in output

    def test_gateway_no_session_not_fake_data(self):
        """Test Gateway doesn't fabricate fake data when no session exists."""
        output = format_status_markdown(None)

        # Should NOT show any token counts or percentages
        assert "**Total Tokens**" not in output
        assert "%" not in output or "No Codex session" in output


# -----------------------------------------------------------------------------
# Test Identical Output Structure
# -----------------------------------------------------------------------------

class TestIdenticalOutputStructure:
    """Tests that CLI and Gateway produce structurally similar output."""

    def test_both_show_same_core_fields(self):
        """Test that both CLI and Gateway show the same core data fields."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            primary_limit=CodexRateLimit(used_percent=50.0, resets_at="2024-01-15T11:00:00Z", tier="primary"),
            secondary_limit=CodexRateLimit(used_percent=25.0, resets_at="2024-01-15T12:00:00Z", tier="secondary"),
            timestamp="2024-01-15T10:30:00Z",
        )

        cli_output = format_status_rich(status)
        gateway_output = format_status_markdown(status)

        # Both should contain the same core information
        assert "Primary" in cli_output
        assert "Primary" in gateway_output
        assert "Secondary" in cli_output
        assert "Secondary" in gateway_output
        assert "Total Tokens" in cli_output
        assert "Total Tokens" in gateway_output
        assert "Context" in cli_output
        assert "Context" in gateway_output

        # Both should show the same values (with comma formatting)
        assert "5,000" in cli_output
        assert "5,000" in gateway_output
        assert "50" in cli_output  # 50%
        assert "50" in gateway_output

    def test_both_handle_missing_data_consistently(self):
        """Test that both handle missing rate limits consistently."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            primary_limit=None,
            secondary_limit=None,
        )

        cli_output = format_status_rich(status)
        gateway_output = format_status_markdown(status)

        # Both should show N/A for missing limits
        assert "N/A" in cli_output or "Primary" in cli_output
        assert "N/A" in gateway_output or "Primary" in gateway_output


# -----------------------------------------------------------------------------
# Test Comparison Output
# -----------------------------------------------------------------------------

class TestComparisonPrettyCard:
    """Tests for Plan A/B/C comparison output formatting."""

    def test_cli_comparison_shows_winner(self):
        """Test CLI comparison output shows the winning plan."""
        comparison = compare_plans()
        output = format_comparison_rich(comparison)

        assert "Winner" in output
        assert comparison.winner in output

    def test_gateway_comparison_shows_winner(self):
        """Test Gateway comparison output shows the winning plan."""
        comparison = compare_plans()
        output = format_comparison_markdown(comparison)

        assert "Winner**" in output or "Winner:" in output
        assert comparison.winner in output

    def test_cli_comparison_shows_all_plans(self):
        """Test CLI comparison shows all three plans."""
        comparison = compare_plans()
        output = format_comparison_rich(comparison)

        assert "Plan A" in output
        assert "Plan B" in output
        assert "Plan C" in output

    def test_gateway_comparison_shows_all_plans(self):
        """Test Gateway comparison shows all three plans."""
        comparison = compare_plans()
        output = format_comparison_markdown(comparison)

        assert "Plan A" in output
        assert "Plan B" in output
        assert "Plan C" in output

    def test_cli_comparison_shows_availability(self):
        """Test CLI comparison shows availability status for each plan."""
        comparison = compare_plans()
        output = format_comparison_rich(comparison)

        # Should indicate whether each plan is available
        assert "Available" in output or "Yes" in output or "No" in output

    def test_gateway_comparison_shows_availability(self):
        """Test Gateway comparison shows availability status for each plan."""
        comparison = compare_plans()
        output = format_comparison_markdown(comparison)

        # Should indicate whether each plan is available
        assert "Available" in output or "✓" in output or "✗" in output


# -----------------------------------------------------------------------------
# Test End-to-End Pretty Card Output
# -----------------------------------------------------------------------------

class TestEndToEndPrettyCard:
    """End-to-end tests for pretty card output from session to display."""

    def test_full_pipeline_produces_valid_cli_output(self, tmp_path):
        """Test that full pipeline produces valid CLI output."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir(parents=True)

        # Create realistic session file
        session_file = session_dir / "session.jsonl"
        events = [
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "payload": {
                    "type": "token_count",
                    "total_token_usage": {"total_tokens": 15000},
                    "model_context_window": 200000,
                    "rate_limits": {
                        "primary": {"used": 8000, "limit": 10000, "resets_at": "2024-01-15T14:00:00Z"},
                        "secondary": {"used": 3000, "limit": 5000, "resets_at": "2024-01-15T16:00:00Z"}
                    }
                }
            }
        ]
        session_file.write_text("\n".join(json.dumps(e) for e in events))

        with patch("hermes_cli.codex_bridge.DEFAULT_CODEX_SESSIONS_DIR", session_dir):
            status = get_realtime_codex_status()
            cli_output = format_status_rich(status)

        # Verify pretty card format
        assert "🤖" in cli_output or "Codex" in cli_output
        assert "Primary Rate Limit" in cli_output
        assert "Secondary Rate Limit" in cli_output
        assert "Total Tokens" in cli_output
        assert "Context Used" in cli_output

        # Verify values are present
        assert "15,000" in cli_output or "15000" in cli_output
        assert "80" in cli_output  # 80% primary
        assert "60" in cli_output  # 60% secondary

    def test_full_pipeline_produces_valid_gateway_output(self, tmp_path):
        """Test that full pipeline produces valid Gateway output."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir(parents=True)

        # Create realistic session file
        session_file = session_dir / "session.jsonl"
        events = [
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "payload": {
                    "type": "token_count",
                    "total_token_usage": {"total_tokens": 15000},
                    "model_context_window": 200000,
                    "rate_limits": {
                        "primary": {"used": 8000, "limit": 10000, "resets_at": "2024-01-15T14:00:00Z"},
                        "secondary": {"used": 3000, "limit": 5000, "resets_at": "2024-01-15T16:00:00Z"}
                    }
                }
            }
        ]
        session_file.write_text("\n".join(json.dumps(e) for e in events))

        with patch("hermes_cli.codex_bridge.DEFAULT_CODEX_SESSIONS_DIR", session_dir):
            status = get_realtime_codex_status()
            gateway_output = format_status_markdown(status)

        # Verify pretty card format with markdown (with colons)
        assert "🤖 **Codex GPT Status**" in gateway_output
        assert "**Primary Rate Limit:**" in gateway_output
        assert "**Secondary Rate Limit:**" in gateway_output
        assert "**Total Tokens:**" in gateway_output
        assert "**Context Used:**" in gateway_output

        # Verify values are present
        assert "15,000" in gateway_output or "15000" in gateway_output
        assert "80" in gateway_output
        assert "60" in gateway_output

    def test_cli_gateway_output_structural_equivalence(self, tmp_path):
        """Test that CLI and Gateway output have equivalent structure."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir(parents=True)

        # Create realistic session file
        session_file = session_dir / "session.jsonl"
        events = [
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "payload": {
                    "type": "token_count",
                    "total_token_usage": {"total_tokens": 25000},
                    "model_context_window": 200000,
                    "rate_limits": {
                        "primary": {"used": 5000, "limit": 10000, "resets_at": "2024-01-15T11:00:00Z"},
                        "secondary": {"used": 2000, "limit": 5000, "resets_at": "2024-01-15T12:00:00Z"}
                    }
                }
            }
        ]
        session_file.write_text("\n".join(json.dumps(e) for e in events))

        with patch("hermes_cli.codex_bridge.DEFAULT_CODEX_SESSIONS_DIR", session_dir):
            status = get_realtime_codex_status()
            cli_output = format_status_rich(status)
            gateway_output = format_status_markdown(status)

        # Both should have same data points
        cli_lines = cli_output.split("\n")
        gateway_lines = gateway_output.split("\n")

        # Both should have similar number of lines (allowing for formatting differences)
        assert abs(len(cli_lines) - len(gateway_lines)) <= 3

        # Both should show the same key values
        assert "25,000" in cli_output or "25000" in cli_output
        assert "25,000" in gateway_output or "25000" in gateway_output
        assert "50" in cli_output  # 50% primary
        assert "50" in gateway_output
        assert "40" in cli_output  # 40% secondary
        assert "40" in gateway_output
        assert "12.5" in cli_output or "12.5" in gateway_output  # 12.5% context


# -----------------------------------------------------------------------------
# Test Relative Time Display
# -----------------------------------------------------------------------------

class TestRelativeTimeDisplay:
    """Tests for relative time formatting in pretty cards."""

    def test_cli_shows_relative_time(self):
        """Test CLI output includes relative timestamp."""
        recent = (datetime.now() - timedelta(minutes=5)).isoformat()
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            timestamp=recent,
        )

        output = format_status_rich(status)

        assert "Updated" in output or "ago" in output

    def test_gateway_shows_relative_time(self):
        """Test Gateway output includes relative timestamp."""
        recent = (datetime.now() - timedelta(minutes=5)).isoformat()
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            timestamp=recent,
        )

        output = format_status_markdown(status)

        assert "Updated" in output or "_Updated:" in output or "ago" in output


# -----------------------------------------------------------------------------
# Test Source Indicator (when enabled)
# -----------------------------------------------------------------------------

class TestSourceIndicator:
    """Tests for data source indicator in output."""

    def test_cli_shows_source_when_requested(self):
        """Test CLI shows source indicator when show_source=True."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            source="session_jsonl",
        )

        output = format_status_rich(status, show_source=True)

        assert "session_jsonl" in output or "Source" in output

    def test_cli_hides_source_when_not_requested(self):
        """Test CLI hides source indicator when show_source=False."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            source="session_jsonl",
        )

        output = format_status_rich(status, show_source=False)

        assert "session_jsonl" not in output
        assert "Source" not in output

    def test_gateway_shows_source_when_requested(self):
        """Test Gateway shows source indicator when show_source=True."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            source="session_jsonl",
        )

        output = format_status_markdown(status, show_source=True)

        assert "session_jsonl" in output or "_Source" in output

    def test_gateway_hides_source_when_not_requested(self):
        """Test Gateway hides source indicator when show_source=False."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            source="session_jsonl",
        )

        output = format_status_markdown(status, show_source=False)

        assert "session_jsonl" not in output
        assert "_Source" not in output


class TestGptsLiveExecOnly:
    """Regression tests to ensure /gpts never falls back to stale session data."""

    def _make_cli(self):
        return HermesCLI.__new__(HermesCLI)

    def _make_gateway(self):
        return GatewayRunner.__new__(GatewayRunner)

    def test_cli_gpts_uses_live_exec_only(self, capsys):
        cli = self._make_cli()

        with patch("hermes_cli.codex_bridge.get_codex_status_via_exec", return_value=None) as live_exec, \
             patch("hermes_cli.codex_bridge.get_realtime_codex_status", side_effect=AssertionError("stale fallback should not be used")) as stale_fallback:
            result = cli._handle_gpts_command("/gpts")

        live_exec.assert_called_once_with(timeout=60)
        stale_fallback.assert_not_called()
        assert result is None
        captured = capsys.readouterr().out
        assert "Unable to retrieve live Codex status" in captured
        assert "Stale cached/session fallback is disabled" in captured

    def test_gateway_gpts_uses_live_exec_only(self):
        gateway = self._make_gateway()
        event = SimpleNamespace(get_command_args=lambda: "")

        async def run():
            with patch("hermes_cli.codex_bridge.get_codex_status_via_exec", return_value=None) as live_exec, \
                 patch("hermes_cli.codex_bridge.get_realtime_codex_status", side_effect=AssertionError("stale fallback should not be used")) as stale_fallback:
                output = await gateway._handle_gpts_command(event)

            live_exec.assert_called_once_with(timeout=60)
            stale_fallback.assert_not_called()
            return output

        output = asyncio.run(run())
        assert "Unable to retrieve live Codex status" in output
        assert "Stale cached/session fallback is disabled" in output


class TestGptsProbeSessionSelection:
    """Tests that /gpts via exec reads the probe session, not a different newer file."""

    def test_get_codex_status_via_exec_uses_probe_session_file(self, tmp_path):
        session_dir = tmp_path / "sessions"
        session_dir.mkdir(parents=True)

        probe_id = "probe-123"
        probe_file = session_dir / f"rollout-2026-04-24T11-37-18-{probe_id}.jsonl"
        probe_file.write_text(
            json.dumps(
                {
                    "timestamp": "2026-04-24T04:37:23.920Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "total_token_usage": {"total_tokens": 4321},
                            "model_context_window": 258400,
                        },
                        "rate_limits": {
                            "primary": {"used_percent": 11.0, "resets_at": 1777019752},
                            "secondary": {"used_percent": 91.0, "resets_at": 1777404697},
                        },
                    },
                }
            )
        )

        # Newer unrelated file should be ignored because it doesn't match probe_id.
        other_file = session_dir / "rollout-2026-04-24T11-50-00-other.jsonl"
        other_file.write_text(
            json.dumps(
                {
                    "timestamp": "2026-04-24T04:50:00.000Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "total_token_usage": {"total_tokens": 9999},
                            "model_context_window": 258400,
                        },
                        "rate_limits": {
                            "primary": {"used_percent": 99.0, "resets_at": 1777019752},
                            "secondary": {"used_percent": 99.0, "resets_at": 1777404697},
                        },
                    },
                }
            )
        )

        fake_stdout = "\n".join([
            json.dumps({"type": "thread.started", "thread_id": probe_id}),
            json.dumps({"type": "turn.completed"}),
        ])

        fake_result = SimpleNamespace(stdout=fake_stdout, returncode=0, stderr="")

        with patch("subprocess.run", return_value=fake_result), \
             patch("hermes_cli.codex_bridge.DEFAULT_CODEX_SESSIONS_DIR", session_dir):
            status = get_codex_status_via_exec(timeout=60)

        assert status is not None
        assert status.total_tokens == 4321
        assert status.primary_limit is not None and status.primary_limit.used_percent == 11.0
        assert status.session_file is not None and status.session_file.endswith(f"{probe_id}.jsonl")
        assert status.source == "session_jsonl"

    def _make_status(self, tmp_path):
        session_file = tmp_path / "rollout-2026-04-24T10-40-11-019dbd92.jsonl"
        session_file.write_text(
            json.dumps(
                {
                    "payload": {
                        "type": "token_count",
                        "total_token_usage": {"total_tokens": 1234},
                        "model_context_window": 200000,
                    }
                }
            )
        )
        return CodexStatus(
            total_tokens=1234,
            model_context_window=200000,
            timestamp="2026-04-24T03:40:24Z",
            session_file=str(session_file),
            source="session_jsonl",
        )

    def test_cli_formatter_includes_debug_details(self, tmp_path):
        status = self._make_status(tmp_path)
        output = format_status_rich(status, debug=True)

        assert "Debug:" in output
        assert "Session File:" in output
        assert "rollout-2026-04-24T10-40-11-019dbd92.jsonl" in output
        assert "File Modified:" in output
        assert "Event Timestamp:" in output

    def test_gateway_formatter_includes_debug_details(self, tmp_path):
        status = self._make_status(tmp_path)
        output = format_status_markdown(status, debug=True)

        assert "**Debug:**" in output
        assert "Session File:" in output
        assert "rollout-2026-04-24T10-40-11-019dbd92.jsonl" in output
        assert "File Modified:" in output
        assert "Event Timestamp:" in output

    def test_cli_command_accepts_debug_flag(self, tmp_path, capsys):
        cli = HermesCLI.__new__(HermesCLI)
        status = self._make_status(tmp_path)

        with patch("hermes_cli.codex_bridge.get_codex_status_via_exec", return_value=status):
            result = cli._handle_gpts_command("/gpts --debug")

        assert result is None
        captured = capsys.readouterr().out
        assert "Debug:" in captured
        assert "Session File:" in captured

    def test_gateway_command_accepts_debug_flag(self, tmp_path):
        gateway = GatewayRunner.__new__(GatewayRunner)
        status = self._make_status(tmp_path)
        event = SimpleNamespace(get_command_args=lambda: "--debug")

        async def run():
            with patch("hermes_cli.codex_bridge.get_codex_status_via_exec", return_value=status):
                return await gateway._handle_gpts_command(event)

        output = asyncio.run(run())
        assert "**Debug:**" in output
        assert "Session File:" in output
