"""Helpers for running Gemini CLI with a Hermes OS fallback."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

GEMINI_CLI_TIMEOUT_SECONDS = float(os.getenv("HERMES_GEMINI_CLI_TIMEOUT_SECONDS", "120"))
GEMINI_CLI_MODEL_ENV = "HERMES_GEMINI_CLI_MODEL"
GEMINI_CLI_BIN_ENV = "HERMES_GEMINI_CLI_BIN"


@dataclass(frozen=True)
class GeminiCliRequest:
    """Parsed Gemini CLI invocation parameters."""

    prompt: str
    model: str = ""


@dataclass(frozen=True)
class GeminiCliResult:
    """Execution result for Gemini CLI."""

    available: bool
    binary: str = ""
    model: str = ""
    prompt: str = ""
    output: str = ""
    reason: str = ""
    exit_code: int | None = None


def resolve_gemini_cli_binary() -> str:
    """Return the Gemini CLI binary path if available."""
    env_bin = os.getenv(GEMINI_CLI_BIN_ENV, "").strip()
    if env_bin:
        return env_bin
    return shutil.which("gemini") or ""


def gemini_cli_is_available() -> bool:
    return bool(resolve_gemini_cli_binary())


def parse_gemini_cli_request(args_text: str) -> GeminiCliRequest:
    """Parse /gemini-cli arguments into a prompt plus optional model override.

    Supported forms:
    - ``/gemini-cli <prompt>``
    - ``/gemini-cli --model gemini-2.5-flash <prompt>``
    - ``/gemini-cli --model=gemini-2.5-flash <prompt>``

    Unknown flags are treated as part of the prompt so the helper stays forgiving.
    """
    raw = (args_text or "").strip()
    if not raw:
        return GeminiCliRequest(prompt="", model="")

    try:
        tokens = shlex.split(raw)
    except ValueError:
        # Preserve the user's text verbatim if quoting is malformed.
        tokens = raw.split()

    prompt_tokens: list[str] = []
    model = ""
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if token == "--model" and idx + 1 < len(tokens):
            model = tokens[idx + 1].strip()
            idx += 2
            continue
        if token.startswith("--model="):
            model = token.split("=", 1)[1].strip()
            idx += 1
            continue
        prompt_tokens.append(token)
        idx += 1

    prompt = " ".join(prompt_tokens).strip()
    if not model:
        model = os.getenv(GEMINI_CLI_MODEL_ENV, "").strip()
    return GeminiCliRequest(prompt=prompt, model=model)


def build_gemini_cli_args(prompt: str, model: str = "") -> list[str]:
    """Build the Gemini CLI argv tail for a prompt."""
    args = ["-p", prompt]
    cleaned_model = (model or "").strip()
    if cleaned_model:
        args.extend(["--model", cleaned_model])
    return args


def run_gemini_cli(prompt: str, model: str = "", timeout: float | None = None) -> GeminiCliResult:
    """Run Gemini CLI and return a structured result.

    If Gemini CLI is unavailable or exits non-zero, the result is marked
    unavailable so callers can fall back to Hermes OS routing.
    """
    binary = resolve_gemini_cli_binary()
    request_prompt = (prompt or "").strip()
    cleaned_model = (model or "").strip()
    if not binary:
        return GeminiCliResult(
            available=False,
            reason="gemini binary not found",
            model=cleaned_model,
            prompt=request_prompt,
        )
    if not request_prompt:
        return GeminiCliResult(
            available=False,
            binary=binary,
            model=cleaned_model,
            reason="missing prompt",
        )

    run_timeout = GEMINI_CLI_TIMEOUT_SECONDS if timeout is None else timeout
    args = [binary, *_build_args_for_exec(request_prompt, cleaned_model)]
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=run_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return GeminiCliResult(
            available=False,
            binary=binary,
            model=cleaned_model,
            prompt=request_prompt,
            reason=f"gemini timed out after {run_timeout}s",
        )
    except FileNotFoundError:
        return GeminiCliResult(
            available=False,
            binary=binary,
            model=cleaned_model,
            prompt=request_prompt,
            reason="gemini binary not executable",
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        return GeminiCliResult(
            available=False,
            binary=binary,
            model=cleaned_model,
            prompt=request_prompt,
            reason=str(exc),
        )

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    output = stdout or stderr
    if completed.returncode == 0:
        return GeminiCliResult(
            available=True,
            binary=binary,
            model=cleaned_model,
            prompt=request_prompt,
            output=output,
            exit_code=0,
        )

    reason = stderr or stdout or f"gemini exited {completed.returncode}"
    return GeminiCliResult(
        available=False,
        binary=binary,
        model=cleaned_model,
        prompt=request_prompt,
        output=output,
        reason=reason,
        exit_code=completed.returncode,
    )


def gemini_cli_fallback_message(reason: str) -> str:
    """Format a concise note when Gemini CLI falls back to Hermes OS."""
    cleaned_reason = (reason or "Gemini CLI unavailable").strip()
    return (
        f"Gemini CLI unavailable ({cleaned_reason}). "
        f"Falling back to Hermes OS native handling."
    )


def result_to_debug_dict(result: GeminiCliResult) -> dict[str, Any]:
    """Convenience helper for tests and logging."""
    return {
        "available": result.available,
        "binary": result.binary,
        "model": result.model,
        "prompt": result.prompt,
        "output": result.output,
        "reason": result.reason,
        "exit_code": result.exit_code,
    }


def _build_args_for_exec(prompt: str, model: str) -> list[str]:
    args = build_gemini_cli_args(prompt, model)
    return args
