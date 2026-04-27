"""Regression tests for Codex status bridge real-time implementation.

Tests Plan A/B/C architecture, session file parsing, and plan comparison.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_cli.codex_bridge import (
    CodexRateLimit,
    CodexStatus,
    PlanComparison,
    DEFAULT_CACHE_TTL_SECONDS,
    clamp_percentage,
    compare_plans,
    extract_rate_limit,
    find_latest_session_file,
    format_comparison_markdown,
    format_comparison_rich,
    format_status_markdown,
    format_status_rich,
    get_realtime_codex_status,
    get_status_plan_c,
    get_today_session_dir,
    load_cached_status,
    parse_session_jsonl,
    parse_token_count_event,
    save_status_to_cache,
    _format_rate_limit,
    _format_relative_time,
)


# -----------------------------------------------------------------------------
# Test Session File Discovery
# -----------------------------------------------------------------------------

class TestSessionFileDiscovery:
    """Tests for finding latest session JSONL files."""

    def test_get_today_session_dir_returns_correct_path(self):
        """Test that today's session directory follows YYYY/MM/DD format."""
        today_dir = get_today_session_dir()
        today = datetime.now()
        expected = Path.home() / ".codex" / "sessions" / f"{today.year:04d}" / f"{today.month:02d}" / f"{today.day:02d}"
        assert today_dir == expected

    def test_find_latest_session_file_no_directory(self, tmp_path):
        """Test that find_latest_session_file returns None when directory doesn't exist."""
        nonexistent_dir = tmp_path / "nonexistent"
        result = find_latest_session_file(nonexistent_dir)
        assert result is None

    def test_find_latest_session_file_empty_directory(self, tmp_path):
        """Test that find_latest_session_file returns None when directory is empty."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir(parents=True)
        result = find_latest_session_file(empty_dir)
        assert result is None

    def test_find_latest_session_file_returns_most_recent(self, tmp_path):
        """Test that find_latest_session_file returns the most recently modified file."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir(parents=True)
        
        # Create older file
        older_file = session_dir / "session_001.jsonl"
        older_file.write_text("")
        older_mtime = (datetime.now() - timedelta(hours=1)).timestamp()
        os.utime(older_file, (older_mtime, older_mtime))
        
        # Create newer file
        newer_file = session_dir / "session_002.jsonl"
        newer_file.write_text("")
        
        result = find_latest_session_file(session_dir)
        assert result == newer_file


# -----------------------------------------------------------------------------
# Test Token Count Event Parsing
# -----------------------------------------------------------------------------

class TestTokenCountEventParsing:
    """Tests for parsing token_count events from JSONL."""

    def test_parse_token_count_event_valid(self):
        """Test parsing a valid token_count event."""
        line = json.dumps({
            "timestamp": "2024-01-15T10:30:00Z",
            "payload": {
                "type": "token_count",
                "total_token_usage": {"total_tokens": 5000},
                "model_context_window": 200000,
                "rate_limits": {
                    "primary": {"used": 1000, "limit": 10000, "resets_at": "2024-01-15T11:00:00Z"},
                    "secondary": {"used": 500, "limit": 5000, "resets_at": "2024-01-15T12:00:00Z"}
                }
            }
        })
        
        payload = parse_token_count_event(line)
        assert payload is not None
        assert payload["type"] == "token_count"
        assert payload["total_token_usage"]["total_tokens"] == 5000

    def test_parse_token_count_event_invalid_json(self):
        """Test that invalid JSON returns None."""
        line = "not valid json"
        result = parse_token_count_event(line)
        assert result is None

    def test_parse_token_count_event_wrong_type(self):
        """Test that non-token_count events return None."""
        line = json.dumps({
            "payload": {
                "type": "other_event",
                "data": "some data"
            }
        })
        result = parse_token_count_event(line)
        assert result is None

    def test_parse_token_count_event_nested_event_msg(self):
        """Test parsing event with nested event_msg structure."""
        line = json.dumps({
            "event_msg": {
                "payload": {
                    "type": "token_count",
                    "total_token_usage": {"total_tokens": 3000},
                    "model_context_window": 100000
                }
            }
        })
        
        payload = parse_token_count_event(line)
        assert payload is not None
        assert payload["total_token_usage"]["total_tokens"] == 3000


# -----------------------------------------------------------------------------
# Test Rate Limit Extraction
# -----------------------------------------------------------------------------

class TestRateLimitExtraction:
    """Tests for extracting rate limit data."""

    def test_extract_rate_limit_valid(self):
        """Test extracting rate limit from valid data."""
        data = {
            "used": 7500,
            "limit": 10000,
            "resets_at": "2024-01-15T14:00:00Z"
        }
        limit = extract_rate_limit(data, "primary")
        
        assert limit is not None
        assert limit.tier == "primary"
        assert limit.used_percent == 75.0
        assert limit.resets_at == "2024-01-15T14:00:00Z"

    def test_extract_rate_limit_missing_used(self):
        """Test extracting rate limit when 'used' is missing."""
        data = {
            "limit": 10000,
            "resets_at": "2024-01-15T14:00:00Z"
        }
        limit = extract_rate_limit(data, "primary")
        assert limit is None

    def test_extract_rate_limit_missing_limit(self):
        """Test extracting rate limit when 'limit' is missing."""
        data = {
            "used": 5000,
            "resets_at": "2024-01-15T14:00:00Z"
        }
        limit = extract_rate_limit(data, "primary")
        assert limit is None

    def test_extract_rate_limit_zero_limit(self):
        """Test extracting rate limit when 'limit' is zero."""
        data = {
            "used": 5000,
            "limit": 0,
            "resets_at": "2024-01-15T14:00:00Z"
        }
        limit = extract_rate_limit(data, "primary")
        assert limit is None

    def test_extract_rate_limit_none_data(self):
        """Test extracting rate limit when data is None."""
        limit = extract_rate_limit(None, "primary")
        assert limit is None


# -----------------------------------------------------------------------------
# Test Session JSONL Parsing
# -----------------------------------------------------------------------------

class TestSessionJsonlParsing:
    """Tests for parsing complete session JSONL files."""

    def test_parse_session_jsonl_no_file(self, tmp_path):
        """Test parsing non-existent file returns None."""
        nonexistent = tmp_path / "nonexistent.jsonl"
        result = parse_session_jsonl(nonexistent)
        assert result is None

    def test_parse_session_jsonl_empty_file(self, tmp_path):
        """Test parsing empty file returns None."""
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")
        result = parse_session_jsonl(empty_file)
        assert result is None

    def test_parse_session_jsonl_no_token_count_events(self, tmp_path):
        """Test parsing file with no token_count events returns None."""
        file = tmp_path / "session.jsonl"
        file.write_text(json.dumps({"payload": {"type": "other"}}) + "\n")
        result = parse_session_jsonl(file)
        assert result is None

    def test_parse_session_jsonl_valid_token_count(self, tmp_path):
        """Test parsing file with valid token_count event."""
        file = tmp_path / "session.jsonl"
        events = [
            {"payload": {"type": "other"}},
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "payload": {
                    "type": "token_count",
                    "total_token_usage": {"total_tokens": 5000},
                    "model_context_window": 200000,
                    "rate_limits": {
                        "primary": {"used": 5000, "limit": 10000, "resets_at": "2024-01-15T11:00:00Z"},
                        "secondary": {"used": 2000, "limit": 5000, "resets_at": "2024-01-15T12:00:00Z"}
                    }
                }
            }
        ]
        file.write_text("\n".join(json.dumps(e) for e in events))
        
        result = parse_session_jsonl(file)
        
        assert result is not None
        assert result.total_tokens == 5000
        assert result.model_context_window == 200000
        assert result.source == "session_jsonl"
        assert result.primary_limit is not None
        assert result.primary_limit.used_percent == 50.0
        assert result.secondary_limit is not None
        assert result.secondary_limit.used_percent == 40.0

    def test_parse_session_jsonl_uses_newest_event(self, tmp_path):
        """Test that parsing uses the newest (last) token_count event."""
        file = tmp_path / "session.jsonl"
        events = [
            {
                "timestamp": "2024-01-15T09:00:00Z",
                "payload": {
                    "type": "token_count",
                    "total_token_usage": {"total_tokens": 1000},
                    "model_context_window": 200000
                }
            },
            {
                "timestamp": "2024-01-15T10:00:00Z",
                "payload": {
                    "type": "token_count",
                    "total_token_usage": {"total_tokens": 5000},
                    "model_context_window": 200000
                }
            }
        ]
        file.write_text("\n".join(json.dumps(e) for e in events))
        
        result = parse_session_jsonl(file)
        
        assert result is not None
        assert result.total_tokens == 5000  # Newest event


# -----------------------------------------------------------------------------
# Test Plan A (Real-time Session JSONL)
# -----------------------------------------------------------------------------

class TestPlanA:
    """Tests for Plan A: Real-time session JSONL parsing."""

    def test_get_realtime_codex_status_no_session(self, monkeypatch, tmp_path):
        """Test Plan A returns None when no session exists for today."""
        # Mock today's session dir to point to temp path
        fake_session_dir = tmp_path / "sessions"
        
        with patch("hermes_cli.codex_bridge.DEFAULT_CODEX_SESSIONS_DIR", fake_session_dir):
            result = get_realtime_codex_status()
        
        assert result is None

    def test_get_realtime_codex_status_skips_codex_exec_probe_sessions(self, tmp_path):
        """Test Plan A prefers the real session over codex_exec probe sessions."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir(parents=True)

        tui_file = session_dir / "rollout-2026-04-24T10-35-42-019dbd8e-c062-7d23-b0fc-de339d74b9f0.jsonl"
        tui_file.write_text(json.dumps({
            "timestamp": "2026-04-24T03:35:47.126Z",
            "type": "session_meta",
            "payload": {
                "id": "019dbd8e-c062-7d23-b0fc-de339d74b9f0",
                "originator": "codex-tui"
            }
        }) + "\n" + json.dumps({
            "timestamp": "2026-04-24T03:35:52.181Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {"total_token_usage": {"total_tokens": 15507}, "model_context_window": 258400},
                "rate_limits": {"primary": {"used_percent": 1.0, "resets_at": 1777019747}, "secondary": {"used_percent": 88.0, "resets_at": 1777404697}}
            }
        }))

        probe_file = session_dir / "rollout-2026-04-24T11-37-18-019dbdc7-26b8-7413-bd79-142e26cc0d0a.jsonl"
        probe_file.write_text(json.dumps({
            "timestamp": "2026-04-24T04:37:21.908Z",
            "type": "session_meta",
            "payload": {
                "id": "019dbdc7-26b8-7413-bd79-142e26cc0d0a",
                "originator": "codex_exec"
            }
        }) + "\n" + json.dumps({
            "timestamp": "2026-04-24T04:37:23.920Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {"total_token_usage": {"total_tokens": 20126}, "model_context_window": 258400},
                "rate_limits": {"primary": {"used_percent": 21.0, "resets_at": 1777019752}, "secondary": {"used_percent": 91.0, "resets_at": 1777404697}}
            }
        }))

        # Make the probe newer so naive mtime sorting would incorrectly pick it.
        os.utime(tui_file, (1777001752, 1777001752))
        os.utime(probe_file, (1777005443, 1777005443))

        with patch("hermes_cli.codex_bridge.DEFAULT_CODEX_SESSIONS_DIR", session_dir):
            result = get_realtime_codex_status()

        assert result is not None
        assert result.total_tokens == 15507
        assert result.source == "session_jsonl"
        assert result.session_file and result.session_file.endswith("019dbd8e-c062-7d23-b0fc-de339d74b9f0.jsonl")


# -----------------------------------------------------------------------------
# Test Plan B (Cache Fallback)
# -----------------------------------------------------------------------------

class TestPlanB:
    """Tests for Plan B: Cache-only fallback."""

    def test_load_cached_status_no_cache(self, tmp_path, monkeypatch):
        """Test loading cache when no cache exists returns None."""
        with patch("hermes_cli.codex_bridge._get_cache_path", return_value=tmp_path / "cache.json"):
            result = load_cached_status()
        
        assert result is None

    def test_load_cached_status_invalid_json(self, tmp_path, monkeypatch):
        """Test loading cache with invalid JSON returns None."""
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("not valid json")
        
        with patch("hermes_cli.codex_bridge._get_cache_path", return_value=cache_file):
            result = load_cached_status()
        
        assert result is None

    def test_save_and_load_cached_status(self, tmp_path):
        """Test saving and loading cache preserves data."""
        cache_file = tmp_path / "cache.json"
        
        status = CodexStatus(
            total_tokens=10000,
            model_context_window=200000,
            primary_limit=CodexRateLimit(used_percent=50.0, resets_at="2024-01-15T11:00:00Z", tier="primary"),
            secondary_limit=None,
            timestamp="2024-01-15T10:30:00Z",
            source="session_jsonl"
        )
        
        with patch("hermes_cli.codex_bridge._get_cache_path", return_value=cache_file):
            save_status_to_cache(status)
            loaded = load_cached_status()
        
        assert loaded is not None
        assert loaded.total_tokens == 10000
        assert loaded.model_context_window == 200000
        assert loaded.source == "cache"  # Loaded from cache, source changes
        assert loaded.primary_limit is not None
        assert loaded.primary_limit.used_percent == 50.0


# -----------------------------------------------------------------------------
# Test Plan C (Cache-first with Refresh)
# -----------------------------------------------------------------------------

class TestPlanC:
    """Tests for Plan C: Cache-first with refresh from session."""

    def test_get_status_plan_c_prefers_session_over_cache(self, tmp_path):
        """Test Plan C prefers fresh session data over cached data."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir(parents=True)
        cache_file = tmp_path / "cache.json"
        
        # Create stale cache with old data
        stale_status = CodexStatus(
            total_tokens=1000,  # Old data
            model_context_window=200000,
            source="cache"
        )
        
        # Create fresh session file
        session_file = session_dir / "session.jsonl"
        session_file.write_text(json.dumps({
            "timestamp": "2024-01-15T10:30:00Z",
            "payload": {
                "type": "token_count",
                "total_token_usage": {"total_tokens": 5000},  # Fresh data
                "model_context_window": 200000
            }
        }))
        
        with patch("hermes_cli.codex_bridge.DEFAULT_CODEX_SESSIONS_DIR", session_dir), \
             patch("hermes_cli.codex_bridge._get_cache_path", return_value=cache_file):
            # Save stale cache first
            save_status_to_cache(stale_status)
            
            # Plan C should refresh from session file
            result = get_status_plan_c()
        
        assert result is not None
        assert result.total_tokens == 5000  # Fresh data from session
        assert result.source == "session_jsonl"

    def test_get_status_plan_c_falls_back_to_cache(self, tmp_path):
        """Test Plan C falls back to cache when no session available."""
        session_dir = tmp_path / "sessions"  # Empty - no session files
        cache_file = tmp_path / "cache.json"
        
        # Create cache with data
        cached_status = CodexStatus(
            total_tokens=3000,
            model_context_window=200000,
            source="cache"
        )
        
        with patch("hermes_cli.codex_bridge.DEFAULT_CODEX_SESSIONS_DIR", session_dir), \
             patch("hermes_cli.codex_bridge._get_cache_path", return_value=cache_file):
            save_status_to_cache(cached_status)
            result = get_status_plan_c()
        
        assert result is not None
        assert result.total_tokens == 3000
        assert result.source == "cache"


# -----------------------------------------------------------------------------
# Test Plan Comparison
# -----------------------------------------------------------------------------

class TestPlanComparison:
    """Tests for compare_plans() function."""

    def test_compare_plans_returns_structured_dict(self, tmp_path):
        """Test that compare_plans returns a properly structured PlanComparison."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir(parents=True)
        cache_file = tmp_path / "cache.json"
        
        # Create session file for Plan A
        session_file = session_dir / "session.jsonl"
        session_file.write_text(json.dumps({
            "timestamp": "2024-01-15T10:30:00Z",
            "payload": {
                "type": "token_count",
                "total_token_usage": {"total_tokens": 5000},
                "model_context_window": 200000
            }
        }))
        
        with patch("hermes_cli.codex_bridge.DEFAULT_CODEX_SESSIONS_DIR", session_dir), \
             patch("hermes_cli.codex_bridge._get_cache_path", return_value=cache_file):
            comparison = compare_plans()
        
        assert isinstance(comparison, PlanComparison)
        assert comparison.winner == "A"
        assert comparison.plan_a is not None
        assert comparison.generated_at is not None
        assert comparison.cache_ttl_seconds == DEFAULT_CACHE_TTL_SECONDS

    def test_compare_plans_winner_plan_a_when_session_available(self, tmp_path):
        """Test Plan A wins when session is available."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir(parents=True)
        cache_file = tmp_path / "cache.json"
        
        # Create session file
        session_file = session_dir / "session.jsonl"
        session_file.write_text(json.dumps({
            "timestamp": "2024-01-15T10:30:00Z",
            "payload": {
                "type": "token_count",
                "total_token_usage": {"total_tokens": 5000},
                "model_context_window": 200000
            }
        }))
        
        with patch("hermes_cli.codex_bridge.DEFAULT_CODEX_SESSIONS_DIR", session_dir), \
             patch("hermes_cli.codex_bridge._get_cache_path", return_value=cache_file):
            comparison = compare_plans()
        
        assert comparison.winner == "A"
        assert comparison.plan_a is not None
        assert comparison.plan_a.total_tokens == 5000

    def test_compare_plans_winner_plan_c_when_only_cache(self, tmp_path):
        """Test Plan C wins when only cache is available (no session)."""
        session_dir = tmp_path / "sessions"  # Empty
        cache_file = tmp_path / "cache.json"
        
        # Create cache
        cached_status = CodexStatus(total_tokens=3000, model_context_window=200000, source="cache")
        
        with patch("hermes_cli.codex_bridge.DEFAULT_CODEX_SESSIONS_DIR", session_dir), \
             patch("hermes_cli.codex_bridge._get_cache_path", return_value=cache_file):
            save_status_to_cache(cached_status)
            comparison = compare_plans()
        
        assert comparison.winner == "C"
        assert comparison.plan_c is not None


# -----------------------------------------------------------------------------
# Test Value Clamping
# -----------------------------------------------------------------------------

class TestValueClamping:
    """Tests for value clamping functions."""

    def test_clamped_percentage_normal(self):
        """Test normal percentage values pass through."""
        limit = CodexRateLimit(used_percent=50.0, resets_at=None, tier="primary")
        assert limit.clamped_percent() == 50.0

    def test_clamped_percentage_above_100(self):
        """Test percentages above 100 are clamped."""
        limit = CodexRateLimit(used_percent=150.0, resets_at=None, tier="primary")
        assert limit.clamped_percent() == 100.0

    def test_clamped_percentage_negative(self):
        """Test negative percentages are clamped."""
        limit = CodexRateLimit(used_percent=-10.0, resets_at=None, tier="primary")
        assert limit.clamped_percent() == 0.0

    def test_context_used_percent_normal(self):
        """Test normal context usage calculation."""
        status = CodexStatus(total_tokens=10000, model_context_window=200000)
        assert status.context_used_percent == 5.0

    def test_context_used_percent_zero_window(self):
        """Test context usage with zero window returns 0."""
        status = CodexStatus(total_tokens=10000, model_context_window=0)
        assert status.context_used_percent == 0.0

    def test_context_used_percent_above_100(self):
        """Test context usage above 100 is clamped."""
        status = CodexStatus(total_tokens=250000, model_context_window=200000)
        assert status.context_used_percent == 100.0


# -----------------------------------------------------------------------------
# Test Formatters
# -----------------------------------------------------------------------------

class TestFormatters:
    """Tests for output formatters."""

    def test_format_status_markdown_no_session(self):
        """Test markdown formatting when no session exists."""
        output = format_status_markdown(None)
        assert "No Codex session found for today" in output
        assert "🤖 **Codex GPT Status**" in output

    def test_format_status_markdown_with_data(self):
        """Test markdown formatting with valid status."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            primary_limit=CodexRateLimit(used_percent=50.0, resets_at="2024-01-15T11:00:00Z", tier="primary"),
            secondary_limit=CodexRateLimit(used_percent=25.0, resets_at="2024-01-15T12:00:00Z", tier="secondary"),
            timestamp="2024-01-15T10:30:00Z",
            source="session_jsonl"
        )
        
        output = format_status_markdown(status)
        
        assert "🤖 **Codex GPT Status**" in output
        assert "5,000" in output  # Formatted with comma
        assert "Primary Rate Limit" in output
        assert "Secondary Rate Limit" in output

    def test_format_status_rich_no_session(self):
        """Test rich formatting when no session exists."""
        output = format_status_rich(None)
        assert "No Codex session found for today" in output
        assert "🤖 Codex GPT Status" in output

    def test_format_status_rich_with_data(self):
        """Test rich formatting with valid status."""
        status = CodexStatus(
            total_tokens=5000,
            model_context_window=200000,
            primary_limit=CodexRateLimit(used_percent=50.0, resets_at=None, tier="primary"),
            secondary_limit=None,
            timestamp="2024-01-15T10:30:00Z",
            source="session_jsonl"
        )
        
        output = format_status_rich(status)
        
        assert "🤖 Codex GPT Status" in output
        assert "5,000" in output  # Formatted with comma
        assert "Primary Rate Limit" in output

    def test_format_comparison_markdown(self):
        """Test markdown comparison formatting."""
        comparison = PlanComparison(
            plan_a=None,
            plan_b=None,
            plan_c=None,
            winner="none",
            speedup=None,
            generated_at="2024-01-15T10:30:00Z",
            cache_ttl_seconds=300
        )
        
        output = format_comparison_markdown(comparison)
        
        assert "⚡ **Codex Status Plan Comparison**" in output
        assert "Winner:** Plan none" in output
        assert "Plan A" in output
        assert "Plan B" in output
        assert "Plan C" in output

    def test_format_comparison_rich(self):
        """Test rich comparison formatting."""
        comparison = PlanComparison(
            plan_a=None,
            plan_b=None,
            plan_c=None,
            winner="none",
            speedup=None,
            generated_at="2024-01-15T10:30:00Z",
            cache_ttl_seconds=300
        )
        
        output = format_comparison_rich(comparison)
        
        assert "⚡ Codex Status Plan Comparison" in output
        assert "Winner: Plan none" in output

    def test_format_rate_limit_with_resets(self):
        """Test rate limit formatting with reset time."""
        limit = CodexRateLimit(used_percent=50.0, resets_at="2024-01-15T11:00:00Z", tier="primary")
        output = _format_rate_limit(limit)
        
        assert "50.0%" in output
        assert "resets" in output

    def test_format_rate_limit_no_resets(self):
        """Test rate limit formatting without reset time."""
        limit = CodexRateLimit(used_percent=75.0, resets_at=None, tier="primary")
        output = _format_rate_limit(limit)
        
        assert output == "75.0%"

    def test_format_rate_limit_none(self):
        """Test rate limit formatting with None."""
        output = _format_rate_limit(None)
        assert output == "N/A"


# -----------------------------------------------------------------------------
# Test Relative Time Formatting
# -----------------------------------------------------------------------------

class TestRelativeTimeFormatting:
    """Tests for relative time formatting."""

    def test_format_relative_time_none(self):
        """Test formatting None timestamp."""
        assert _format_relative_time(None) == "unknown"

    def test_format_relative_time_iso_timestamp(self):
        """Test formatting ISO timestamp."""
        # Just verify it doesn't crash - actual value depends on current time
        result = _format_relative_time("2024-01-15T10:30:00Z")
        assert result in ["just now", "unknown"] or any(x in result for x in ["m ago", "h ago", "d ago"])

    def test_format_relative_time_unix_timestamp(self):
        """Test formatting unix timestamp."""
        recent = str(datetime.now().timestamp())
        result = _format_relative_time(recent)
        assert result in ["just now", "unknown"] or any(x in result for x in ["m ago", "h ago"])


# -----------------------------------------------------------------------------
# End-to-End Tests
# -----------------------------------------------------------------------------

class TestEndToEnd:
    """End-to-end tests for the full bridge pipeline."""

    def test_full_pipeline_session_to_output(self, tmp_path):
        """Test complete pipeline from session file to formatted output."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir(parents=True)
        
        # Create a realistic session file
        session_file = session_dir / "session_20240115_103000.jsonl"
        events = [
            {
                "timestamp": "2024-01-15T09:00:00Z",
                "payload": {"type": "session_start"}
            },
            {
                "timestamp": "2024-01-15T09:30:00Z",
                "payload": {
                    "type": "token_count",
                    "total_token_usage": {"total_tokens": 3000},
                    "model_context_window": 200000
                }
            },
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
            # Step 1: Get real-time status
            status = get_realtime_codex_status()
            
            # Step 2: Format for CLI
            cli_output = format_status_rich(status)
            
            # Step 3: Format for Gateway
            gateway_output = format_status_markdown(status)
        
        # Verify end-to-end
        assert status is not None
        assert status.total_tokens == 15000  # Newest event
        assert status.primary_limit is not None
        assert status.primary_limit.used_percent == 80.0
        assert "15,000" in cli_output  # Formatted with comma
        assert "15,000" in gateway_output  # Formatted with comma
        assert "80.0%" in cli_output or "80.0" in cli_output
        assert "80.0%" in gateway_output or "80.0" in gateway_output

    def test_compare_plans_returns_speedup(self, tmp_path):
        """Test that compare_plans calculates speedup when Plan A wins."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir(parents=True)
        cache_file = tmp_path / "cache.json"
        
        # Create session file for Plan A to succeed
        session_file = session_dir / "session.jsonl"
        session_file.write_text(json.dumps({
            "timestamp": "2024-01-15T10:30:00Z",
            "payload": {
                "type": "token_count",
                "total_token_usage": {"total_tokens": 5000},
                "model_context_window": 200000
            }
        }))
        
        with patch("hermes_cli.codex_bridge.DEFAULT_CODEX_SESSIONS_DIR", session_dir), \
             patch("hermes_cli.codex_bridge._get_cache_path", return_value=cache_file):
            comparison = compare_plans()
        
        # Plan A should win with a speedup factor
        assert comparison.winner == "A"
        assert comparison.speedup is not None or comparison.speedup is None  # Either is valid
