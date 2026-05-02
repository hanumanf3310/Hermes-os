"""Tests for the Gemini research workflow helper."""

from unittest.mock import patch

from hermes_cli.gemini_cli import GeminiCliResult
from hermes_cli.gemini_workflow import (
    build_gemini_research_prompt,
    format_gemini_workflow_result,
    parse_gemini_research_request,
    run_gemini_research_workflow,
)


class TestGeminiResearchWorkflow:
    def test_parse_request_supports_question_evidence_and_model(self):
        request = parse_gemini_research_request(
            '--question "What changed?" --evidence "Line 1: docs updated\nLine 2: command added" --model gemini-2.5-flash'
        )

        assert request.question == "What changed?"
        assert "docs updated" in request.evidence
        assert request.model == "gemini-2.5-flash"

    def test_build_prompt_includes_question_and_evidence(self):
        prompt = build_gemini_research_prompt(
            "What changed?",
            "Line 1: docs updated\nLine 2: command added",
        )

        assert "Question:" in prompt
        assert "What changed?" in prompt
        assert "docs updated" in prompt
        assert "verification_risk:" in prompt

    def test_workflow_returns_summary_and_verification_prompt_when_gemini_available(self):
        gemini_result = GeminiCliResult(
            available=True,
            binary="/usr/bin/gemini",
            model="gemini-2.5-flash",
            prompt="ignored",
            output="summary: docs updated\nclaims: - command added\nassumptions: none\nverification_risk: low",
            exit_code=0,
        )

        with patch("hermes_cli.gemini_workflow.run_gemini_cli", return_value=gemini_result):
            result = run_gemini_research_workflow(
                "What changed?",
                "Line 1: docs updated\nLine 2: command added",
                model="gemini-2.5-flash",
            )

        assert result.available is True
        assert result.summary.startswith("summary:")
        assert "Verify the Gemini summary against the evidence" in result.verification_prompt
        assert "docs updated" in result.verification_prompt
        assert result.fallback_prompt == ""
        rendered = format_gemini_workflow_result(result)
        assert "Gemini workflow summary" in rendered

    def test_workflow_falls_back_to_hermes_when_gemini_unavailable(self):
        gemini_result = GeminiCliResult(
            available=False,
            binary="",
            model="gemini-2.5-flash",
            prompt="ignored",
            reason="gemini binary not found",
            exit_code=None,
        )

        with patch("hermes_cli.gemini_workflow.run_gemini_cli", return_value=gemini_result):
            result = run_gemini_research_workflow(
                "What changed?",
                "Line 1: docs updated\nLine 2: command added",
            )

        assert result.available is False
        assert result.summary == ""
        assert "Gemini CLI is unavailable" in result.fallback_prompt
        assert "docs updated" in result.fallback_prompt
        rendered = format_gemini_workflow_result(result)
        assert "Gemini workflow fallback to Hermes OS" in rendered
