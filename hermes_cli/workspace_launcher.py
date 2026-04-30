"""Shared helper for the Hermes Workspace launcher slash command."""

from __future__ import annotations

import subprocess

_VALID_SUBCOMMANDS = {"up", "status", "down"}
_USAGE = "Usage: /hermes-workspace [up|status|down]"


def parse_workspace_launcher_args(raw_args: str | None) -> tuple[str | None, str | None]:
    """Return (subcommand, error). Defaults to ``status`` for empty args."""
    parts = (raw_args or "").strip().split(maxsplit=1)
    subcmd = (parts[0].lower() if parts else "status") or "status"
    if subcmd not in _VALID_SUBCOMMANDS:
        return None, _USAGE
    return subcmd, None


def run_workspace_launcher(raw_args: str | None, *, timeout: int = 120) -> str:
    """Run ``hermes-workspace`` and return a compact user-facing message."""
    subcmd, error = parse_workspace_launcher_args(raw_args)
    if error:
        return error

    try:
        result = subprocess.run(
            ["hermes-workspace", subcmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return "❌ hermes-workspace command not found. Install the hermes-workspace-launcher skill first."
    except subprocess.TimeoutExpired:
        return f"⏳ hermes-workspace {subcmd} timed out after {timeout}s"
    except Exception as exc:
        return f"❌ hermes-workspace {subcmd} failed: {exc}"

    output = (result.stdout or result.stderr or "").strip()
    if result.returncode == 0:
        return output or f"✅ hermes-workspace {subcmd} completed"
    return f"❌ hermes-workspace {subcmd} failed\n{output}".strip()
