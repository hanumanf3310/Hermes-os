"""Helpers for a Hermes → Gemini → Hermes verification workflow.

This module keeps the workflow narrow and testable:
- Hermes collects evidence elsewhere (search/fetch/browser)
- Gemini summarizes the evidence when available
- Hermes receives a verification prompt or a fallback prompt when Gemini is unavailable
"""

from __future__ import annotations

from dataclasses import dataclass
import shlex
from textwrap import shorten

from hermes_cli.gemini_cli import GeminiCliResult, run_gemini_cli


WORKFLOW_DEFAULT_MODEL = "gemini-2.5-flash"
WORKFLOW_MAX_EVIDENCE_CHARS = 12_000


@dataclass(frozen=True)
class GeminiResearchRequest:
    """Parsed arguments for the research workflow command."""

    question: str
    evidence: str
    model: str = ""


@dataclass(frozen=True)
class GeminiWorkflowResult:
    """Structured result for the research/summarize/verify workflow."""

    available: bool
    question: str
    evidence: str
    summary: str = ""
    verification_prompt: str = ""
    fallback_prompt: str = ""
    reason: str = ""
    binary: str = ""
    model: str = ""
    exit_code: int | None = None


def _normalize_text(text: str) -> str:
    return (text or "").strip()


def parse_gemini_research_request(args_text: str) -> GeminiResearchRequest:
    """Parse `/gemini-research` arguments.

    Supported input styles:
    - ``--question <q> --evidence <e> [--model <m>]``
    - ``--question=<q> --evidence=<e> [--model=<m>]``
    - ``<question> ||| <evidence> [--model <m>]``
    - ``<question> || <evidence> [--model <m>]``

    Unknown fragments are treated conservatively as part of the question when
    possible so the command stays forgiving in chat clients.
    """
    raw = (args_text or "").strip()
    if not raw:
        return GeminiResearchRequest(question="", evidence="", model="")

    try:
        tokens = shlex.split(raw)
    except ValueError:
        tokens = raw.split()

    model = ""
    question_tokens: list[str] = []
    evidence_tokens: list[str] = []
    current = question_tokens
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if token in {"--question", "-q"} and idx + 1 < len(tokens):
            question_tokens = [tokens[idx + 1]]
            current = question_tokens
            idx += 2
            continue
        if token.startswith("--question="):
            question_tokens = [token.split("=", 1)[1]]
            current = question_tokens
            idx += 1
            continue
        if token in {"--evidence", "-e"} and idx + 1 < len(tokens):
            evidence_tokens = [tokens[idx + 1]]
            current = evidence_tokens
            idx += 2
            continue
        if token.startswith("--evidence="):
            evidence_tokens = [token.split("=", 1)[1]]
            current = evidence_tokens
            idx += 1
            continue
        if token == "--model" and idx + 1 < len(tokens):
            model = tokens[idx + 1].strip()
            idx += 2
            continue
        if token.startswith("--model="):
            model = token.split("=", 1)[1].strip()
            idx += 1
            continue
        if token in {"|||", "||"}:
            current = evidence_tokens
            idx += 1
            continue
        current.append(token)
        idx += 1

    question = _normalize_text(" ".join(question_tokens))
    evidence = _normalize_text(" ".join(evidence_tokens))
    if not question or not evidence:
        # Try the separator form on the original text if flag parsing did not
        # populate both fields.
        for separator in ("|||", "||"):
            if separator in raw:
                left, right = raw.split(separator, 1)
                left = left.strip()
                right = right.strip()
                if not question:
                    question = _normalize_text(left)
                if not evidence:
                    evidence = _normalize_text(right)
                break

    return GeminiResearchRequest(question=question, evidence=evidence, model=model)


def _trim_evidence(evidence: str) -> str:
    cleaned = _normalize_text(evidence)
    if len(cleaned) <= WORKFLOW_MAX_EVIDENCE_CHARS:
        return cleaned
    return cleaned[:WORKFLOW_MAX_EVIDENCE_CHARS].rstrip() + "\n[truncated]"


def build_gemini_research_prompt(question: str, evidence: str) -> str:
    """Build the Gemini prompt for summarizing evidence.

    The prompt explicitly asks for a compact answer, a bullet list of claims,
    and a separate assumptions section so Hermes can verify the output.
    """
    cleaned_question = _normalize_text(question)
    cleaned_evidence = _trim_evidence(evidence)

    return (
        "You are helping Hermes OS summarize evidence for later verification.\n\n"
        f"Question:\n{cleaned_question or '(none provided)'}\n\n"
        "Evidence:\n"
        f"{cleaned_evidence or '(no evidence provided)'}\n\n"
        "Instructions:\n"
        "1. Summarize only what is directly supported by the evidence.\n"
        "2. Separate facts from assumptions.\n"
        "3. If evidence is insufficient, say exactly what is missing.\n"
        "4. Keep the answer concise and grounded.\n\n"
        "Return exactly this structure:\n"
        "summary: <1-3 sentences>\n"
        "claims: <bullet list or 'none'>\n"
        "assumptions: <bullet list or 'none'>\n"
        "verification_risk: <low|medium|high>\n"
    )


def build_hermes_verification_prompt(question: str, evidence: str, summary: str) -> str:
    """Build a verification prompt for Hermes after Gemini summarizes evidence."""
    cleaned_question = _normalize_text(question)
    cleaned_evidence = _trim_evidence(evidence)
    cleaned_summary = _normalize_text(summary)

    return (
        "Verify the Gemini summary against the evidence.\n\n"
        f"Question:\n{cleaned_question or '(none provided)'}\n\n"
        f"Summary to verify:\n{cleaned_summary or '(no summary provided)'}\n\n"
        f"Evidence:\n{cleaned_evidence or '(no evidence provided)'}\n\n"
        "Return a concise verdict with this structure:\n"
        "verdict: PASS or FAIL\n"
        "unsupported_claims: <bullet list or 'none'>\n"
        "notes: <short explanation>\n"
        "If the summary is unsupported, do not promote it to a fact.\n"
    )


def build_hermes_fallback_prompt(question: str, evidence: str) -> str:
    """Build a Hermes-native prompt used when Gemini is unavailable."""
    cleaned_question = _normalize_text(question)
    cleaned_evidence = _trim_evidence(evidence)

    return (
        "Gemini CLI is unavailable. Hermes OS should answer natively using the evidence below.\n\n"
        f"Question:\n{cleaned_question or '(none provided)'}\n\n"
        f"Evidence:\n{cleaned_evidence or '(no evidence provided)'}\n\n"
        "Give a short grounded answer, then list any missing evidence.\n"
    )


def run_gemini_research_workflow(
    question: str,
    evidence: str,
    *,
    model: str = "",
    timeout: float | None = None,
) -> GeminiWorkflowResult:
    """Run the summarize-and-verify workflow.

    If Gemini is available, the returned result contains:
    - the Gemini summary output
    - a Hermes verification prompt that can be fed back into Hermes OS

    If Gemini is unavailable, the returned result contains a Hermes fallback
    prompt so the caller can continue the workflow without UI changes.
    """
    cleaned_question = _normalize_text(question)
    cleaned_evidence = _trim_evidence(evidence)
    chosen_model = _normalize_text(model) or WORKFLOW_DEFAULT_MODEL

    prompt = build_gemini_research_prompt(cleaned_question, cleaned_evidence)
    gemini_result: GeminiCliResult = run_gemini_cli(prompt, model=chosen_model, timeout=timeout)

    if not gemini_result.available:
        return GeminiWorkflowResult(
            available=False,
            question=cleaned_question,
            evidence=cleaned_evidence,
            reason=gemini_result.reason,
            binary=gemini_result.binary,
            model=chosen_model,
            exit_code=gemini_result.exit_code,
            fallback_prompt=build_hermes_fallback_prompt(cleaned_question, cleaned_evidence),
        )

    summary = _normalize_text(gemini_result.output)
    verification_prompt = build_hermes_verification_prompt(cleaned_question, cleaned_evidence, summary)
    return GeminiWorkflowResult(
        available=True,
        question=cleaned_question,
        evidence=cleaned_evidence,
        summary=summary,
        verification_prompt=verification_prompt,
        reason=gemini_result.reason,
        binary=gemini_result.binary,
        model=chosen_model,
        exit_code=gemini_result.exit_code,
    )


def format_gemini_workflow_result(result: GeminiWorkflowResult) -> str:
    """Format the workflow result for terminal or chat output."""
    if not result.available:
        reason = result.reason or "Gemini CLI unavailable"
        return (
            "Gemini workflow fallback to Hermes OS\n"
            f"reason: {reason}\n"
            f"prompt: {shorten(result.fallback_prompt, width=500, placeholder='…')}"
        )

    return (
        "Gemini workflow summary\n"
        f"summary: {result.summary}\n"
        f"verification_prompt: {shorten(result.verification_prompt, width=500, placeholder='…')}"
    )
