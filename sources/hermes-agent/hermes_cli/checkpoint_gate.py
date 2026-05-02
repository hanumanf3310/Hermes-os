"""Checkpoint / go-no-go helper for Hermes workflows.

This helper turns a compact checkpoint prompt into a structured decision card.
It is intentionally dependency-free so CLI and gateway dispatch can share it.
"""

from __future__ import annotations

from dataclasses import dataclass
import shlex


@dataclass(frozen=True)
class CheckpointRequest:
    goal: str = ""
    current_state: str = ""
    evidence: str = ""
    alternatives: str = ""


@dataclass(frozen=True)
class CheckpointResult:
    decision: str
    reason: str
    next_action: str
    goal: str
    current_state: str
    evidence: str
    alternatives: str
    loop_risk: bool = False


_LOOP_MARKERS = (
    "loop",
    "วนลูป",
    "endless",
    "stuck",
    "same context",
    "old context",
    "re-audit",
    "recheck old",
    "no new data",
    "no progress",
    "repeat",
)


def _clean(value: str | None) -> str:
    return " ".join(str(value or "").strip().split())


def _contains_loop_marker(*values: str) -> bool:
    haystack = " ".join(_clean(value).lower() for value in values if value)
    return any(marker in haystack for marker in _LOOP_MARKERS)


def parse_checkpoint_request(args_text: str) -> CheckpointRequest:
    """Parse checkpoint args from flags or a compact shorthand.

    Supported forms:
    - /checkpoint --goal "..." --current "..." --evidence "..." --alternatives "..."
    - /checkpoint goal ||| current ||| evidence ||| alternatives
    - /checkpoint freeform goal text
    """

    raw = _clean(args_text)
    if not raw:
        return CheckpointRequest()

    if "|||" in raw:
        parts = [part.strip() for part in raw.split("|||")]
        parts += [""] * (4 - len(parts))
        return CheckpointRequest(
            goal=parts[0],
            current_state=parts[1],
            evidence=parts[2],
            alternatives=parts[3],
        )

    tokens = shlex.split(raw)
    if not tokens:
        return CheckpointRequest()

    fields = {"goal": [], "current": [], "evidence": [], "alternatives": []}
    positional: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in {"--goal", "-g"} and i + 1 < len(tokens):
            fields["goal"] = [tokens[i + 1]]
            i += 2
            continue
        if token in {"--current", "--state", "-c"} and i + 1 < len(tokens):
            fields["current"] = [tokens[i + 1]]
            i += 2
            continue
        if token in {"--evidence", "-e"} and i + 1 < len(tokens):
            fields["evidence"] = [tokens[i + 1]]
            i += 2
            continue
        if token in {"--alternatives", "--alt", "-a"} and i + 1 < len(tokens):
            fields["alternatives"] = [tokens[i + 1]]
            i += 2
            continue
        positional.append(token)
        i += 1

    if not fields["goal"] and positional:
        fields["goal"] = [" ".join(positional)]

    return CheckpointRequest(
        goal=_clean(" ".join(fields["goal"])),
        current_state=_clean(" ".join(fields["current"])),
        evidence=_clean(" ".join(fields["evidence"])),
        alternatives=_clean(" ".join(fields["alternatives"])),
    )


def run_checkpoint_gate(request: CheckpointRequest) -> CheckpointResult:
    """Evaluate a checkpoint and return a GO/HOLD/REDIRECT decision."""

    goal = _clean(request.goal)
    current_state = _clean(request.current_state)
    evidence = _clean(request.evidence)
    alternatives = _clean(request.alternatives)
    loop_risk = _contains_loop_marker(goal, current_state, evidence, alternatives)

    if not goal and not current_state and not evidence and not alternatives:
        return CheckpointResult(
            decision="HOLD",
            reason="No checkpoint context was provided yet.",
            next_action="Provide a goal + current state + evidence, or keep the work in read-only inspect mode until you have a checkpoint.",
            goal=goal,
            current_state=current_state,
            evidence=evidence,
            alternatives=alternatives,
            loop_risk=False,
        )

    if loop_risk:
        return CheckpointResult(
            decision="REDIRECT",
            reason="The checkpoint contains loop / re-audit signals, so continuing the same path risks endless repetition.",
            next_action="Switch to an alternative path, narrow the scope, or stop and record the checkpoint before continuing.",
            goal=goal,
            current_state=current_state,
            evidence=evidence,
            alternatives=alternatives,
            loop_risk=True,
        )

    if goal and (evidence or current_state):
        return CheckpointResult(
            decision="GO",
            reason="The checkpoint has a clear goal and fresh supporting context.",
            next_action="Continue with the smallest verified next step and keep the next checkpoint explicit.",
            goal=goal,
            current_state=current_state,
            evidence=evidence,
            alternatives=alternatives,
            loop_risk=False,
        )

    return CheckpointResult(
        decision="HOLD",
        reason="The checkpoint is missing either evidence or current-state detail, so the safe move is to pause.",
        next_action="Add the missing evidence or current-state summary, or choose an alternate route if the current one is stale.",
        goal=goal,
        current_state=current_state,
        evidence=evidence,
        alternatives=alternatives,
        loop_risk=False,
    )


def format_checkpoint_result(result: CheckpointResult) -> str:
    """Render a concise decision card for CLI / gateway output."""

    lines = [
        "⏸️ Checkpoint / Go-No-Go",
        f"Decision: {result.decision}",
        f"Reason: {result.reason}",
        f"Next: {result.next_action}",
    ]
    if result.goal:
        lines.append(f"Goal: {result.goal}")
    if result.current_state:
        lines.append(f"Current: {result.current_state}")
    if result.evidence:
        lines.append(f"Evidence: {result.evidence}")
    if result.alternatives:
        lines.append(f"Alternatives: {result.alternatives}")
    if result.loop_risk:
        lines.append("Loop risk: YES")
    return "\n".join(lines)


def checkpoint_usage() -> str:
    return (
        "Usage: /checkpoint --goal <goal> --current <state> --evidence <evidence> [--alternatives <route>]\n"
        "Short form: /checkpoint <goal> ||| <current> ||| <evidence> ||| <alternatives>\n"
        "Decision rules: GO = continue, HOLD = gather/check, REDIRECT = switch path or stop looping."
    )
