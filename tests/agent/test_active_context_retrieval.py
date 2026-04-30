"""
Tests for Active Context Retrieval Module (Task D).

Validates pattern detection, context building, and fail-soft behavior.
"""

import pytest
from unittest.mock import patch, MagicMock
from agent.active_context_retrieval import (
    detect_task_type,
    build_retrieval_context,
    should_trigger_retrieval,
    get_active_context_for_turn,
    build_retrieval_block_for_agent,
    CONFIDENCE_THRESHOLD,
)


class TestDetectTaskType:
    """Test task pattern detection."""

    def test_detects_code_task(self):
        """Should detect code-related tasks."""
        task_type, confidence = detect_task_type("Deploy new feature and test it")
        assert task_type == "code"
        assert confidence >= CONFIDENCE_THRESHOLD

    def test_detects_analysis_task(self):
        """Should detect analysis-related tasks."""
        task_type, confidence = detect_task_type("Check policy compliance and verify")
        assert task_type == "analysis"
        assert confidence >= CONFIDENCE_THRESHOLD

    def test_detects_config_task(self):
        """Should detect configuration tasks."""
        task_type, confidence = detect_task_type("Update dashboard nodes and settings")
        assert task_type == "config"
        assert confidence >= CONFIDENCE_THRESHOLD

    def test_detects_safety_task(self):
        """Should detect safety-related tasks."""
        task_type, confidence = detect_task_type("Backup first then restore")
        assert task_type == "safety"
        assert confidence >= CONFIDENCE_THRESHOLD

    def test_no_match_returns_none(self):
        """Should return None when no pattern matches."""
        task_type, confidence = detect_task_type("Hello how are you")
        assert task_type is None
        assert confidence == 0.0

    def test_insufficient_matches_returns_none(self):
        """Should return None when only 1 keyword matches."""
        task_type, confidence = detect_task_type("fix")  # Only 1 keyword
        assert task_type is None
        assert confidence == 0.0


class TestShouldTriggerRetrieval:
    """Test retrieval triggering logic."""

    def test_triggers_on_clear_task(self):
        """Should trigger on clear task patterns."""
        assert should_trigger_retrieval("Deploy and test new code")

    def test_no_trigger_on_generic_message(self):
        """Should not trigger on generic messages."""
        assert not should_trigger_retrieval("Hello there")

    def test_no_trigger_on_short_message(self):
        """Should not trigger on short/vague messages."""
        assert not should_trigger_retrieval("fix")


class TestBuildRetrievalContext:
    """Test context building for different task types."""

    def test_builds_code_context(self):
        """Should build context for code tasks."""
        result = build_retrieval_context("code", "Implement new feature")

        assert result.context is not None
        assert result.task_type == "code"
        assert result.error is None
        assert "TDD" in result.context
        assert "pytest" in result.context
        assert result.confidence > 0

    def test_builds_analysis_context(self):
        """Should build context for analysis tasks."""
        result = build_retrieval_context("analysis", "Check compliance")

        assert result.context is not None
        assert result.task_type == "analysis"
        assert "evidence" in result.context.lower()

    def test_builds_config_context(self):
        """Should build context for config tasks."""
        result = build_retrieval_context("config", "Update dashboard")

        assert result.context is not None
        assert result.task_type == "config"
        assert "backup" in result.context.lower()

    def test_builds_safety_context(self):
        """Should build context for safety tasks."""
        result = build_retrieval_context("safety", "Backup and restore")

        assert result.context is not None
        assert result.task_type == "safety"
        assert "rollback" in result.context.lower()

    def test_unknown_task_type_returns_error(self):
        """Should handle unknown task types gracefully."""
        result = build_retrieval_context("unknown", "Some message")

        assert result.context is None
        assert result.error is not None
        assert "Unknown task type" in result.error

    def test_includes_hermes_os_context_for_all(self):
        """All contexts should include Hermes OS context."""
        for task_type in ["code", "analysis", "config", "safety"]:
            result = build_retrieval_context(task_type, "Test message")
            assert result.context is not None
            assert "Hermes OS" in result.context
            assert "🛡️" in result.context


class TestFailSoftBehavior:
    """Test fail-soft error handling."""

    def test_handles_exception_gracefully(self):
        """Should handle exceptions without crashing."""
        with patch('agent.active_context_retrieval.TASK_PATTERNS', None):
            result = build_retrieval_context("code", "Test")

        # Should return error but not crash
        assert result.error is not None

    def test_get_active_context_returns_none_on_no_trigger(self):
        """Should return None when no trigger detected."""
        result = get_active_context_for_turn("Hello there")
        assert result is None

    def test_build_retrieval_block_returns_empty_on_no_context(self):
        """Should return empty string when no context."""
        result = build_retrieval_block_for_agent("Hello there")
        assert result == ""


class TestRetrievalBlockFormatting:
    """Test the formatted output for agent consumption."""

    def test_block_has_correct_structure(self):
        """Should produce properly structured block."""
        block = build_retrieval_block_for_agent("Deploy new code")

        assert "<context-mode-retrieval>" in block
        assert "</context-mode-retrieval>" in block
        assert "Proactively retrieved context" in block

    def test_block_includes_task_guidance(self):
        """Should include task-specific guidance."""
        block = build_retrieval_block_for_agent("Check policy compliance")

        assert "🔍" in block or "Analysis" in block
        assert "evidence" in block.lower()


class TestTokenLimits:
    """Test safety boundaries."""

    def test_context_respects_token_limit(self):
        """Context should be within token limits."""
        from agent.active_context_retrieval import MAX_CONTEXT_TOKENS

        result = build_retrieval_context("code", "Test message")

        # Rough token estimate: words / 0.75
        word_count = len(result.context.split())
        assert word_count <= MAX_CONTEXT_TOKENS * 1.5  # Allow some margin


class TestTimestampHandling:
    """Test UTC+7 timestamp compliance."""

    def test_timestamp_includes_timezone(self):
        """Should include timezone in timestamp."""
        result = build_retrieval_context("code", "Test")

        # Timestamp should be ISO format with timezone
        assert "+" in result.timestamp or "Z" in result.timestamp

    def test_timestamp_not_naive(self):
        """Timestamp should not be naive."""
        result = build_retrieval_context("code", "Test")

        # Should be parseable as datetime with timezone
        from datetime import datetime
        dt = datetime.fromisoformat(result.timestamp.replace("Z", "+00:00"))
        assert dt.tzinfo is not None or "+" in result.timestamp
