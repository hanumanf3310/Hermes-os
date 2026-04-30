"""Helpers for launching/reporting Hermes Workspace from CLI and Gateway."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_WORKSPACE_LAUNCHER = Path.home() / ".local" / "bin" / "hermes-workspace"
_VALID_ACTIONS = {"up", "start", "status", "down", "stop", "restart"}
_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_URL_RE = re.compile(r"https://[^\s]+")


@dataclass(frozen=True)
class WorkspaceLauncherRequest:
    action: str = "up"


@dataclass(frozen=True)
class WorkspaceLauncherResult:
    ok: bool
    action: str
    output: str
    exit_code: int | None = None
    error: str = ""
    launcher: str = str(_WORKSPACE_LAUNCHER)


def strip_ansi(text: str) -> str:
    """Remove ANSI color/control sequences from launcher output."""
    return _ANSI_RE.sub("", text or "")


def parse_workspace_launcher_request(raw_args: str) -> tuple[WorkspaceLauncherRequest | None, str | None]:
    """Parse `/hermes_workspace [up|status|down|restart]` arguments."""
    args = (raw_args or "").strip().split()
    action = args[0].lower() if args else "up"
    if action == "launch":
        action = "up"
    if action == "shutdown":
        action = "down"
    if action not in _VALID_ACTIONS:
        return None, "Usage: /hermes_workspace [up|status|down|restart]"
    return WorkspaceLauncherRequest(action=action), None


def run_workspace_launcher(request: WorkspaceLauncherRequest, timeout: int = 180) -> WorkspaceLauncherResult:
    """Run the installed Hermes Workspace launcher and capture clean output."""
    launcher = _WORKSPACE_LAUNCHER
    if not launcher.exists():
        return WorkspaceLauncherResult(
            ok=False,
            action=request.action,
            output="",
            exit_code=None,
            error=f"Hermes Workspace launcher not found: {launcher}",
            launcher=str(launcher),
        )

    proc = subprocess.run(
        [str(launcher), request.action],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = strip_ansi(((proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")).strip())
    return WorkspaceLauncherResult(
        ok=proc.returncode == 0,
        action=request.action,
        output=output,
        exit_code=proc.returncode,
        launcher=str(launcher),
    )


def format_workspace_launcher_message(result: WorkspaceLauncherResult) -> str:
    """Format launcher result compactly for Telegram/CLI."""
    title = "🧰 Hermes Workspace"
    if not result.ok:
        detail = result.error or result.output or "Command failed"
        suffix = f"\nExit code: {result.exit_code}" if result.exit_code not in (None, 0) else ""
        return f"{title}\n❌ เปิด/ตรวจ Workspace ไม่สำเร็จ\n{detail}{suffix}"

    action_label = {
        "up": "เปิดระบบ/ลิงก์มือถือแล้ว",
        "start": "เปิดระบบ/ลิงก์มือถือแล้ว",
        "status": "สถานะปัจจุบัน",
        "down": "ปิดระบบแล้ว",
        "stop": "ปิดระบบแล้ว",
        "restart": "รีสตาร์ทระบบแล้ว",
    }.get(result.action, result.action)

    lines = [title, f"✅ {action_label}"]
    if result.output:
        lines.append("")
        lines.append(result.output.strip())

    urls = _URL_RE.findall(result.output or "")
    if urls:
        lines.append("")
        lines.append("📱 Mobile URLs:")
        for url in dict.fromkeys(urls):
            lines.append(f"• {url}")

    return "\n".join(lines).strip()


__all__ = [
    "WorkspaceLauncherRequest",
    "WorkspaceLauncherResult",
    "format_workspace_launcher_message",
    "parse_workspace_launcher_request",
    "run_workspace_launcher",
    "strip_ansi",
]
