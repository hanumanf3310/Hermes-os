"""Helpers for launching and reporting Hermes Memory Graph status."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

MEMORY_GRAPH_HOST = os.getenv("HERMES_MEMORY_GRAPH_HOST", "127.0.0.1")
MEMORY_GRAPH_PORT = int(os.getenv("HERMES_MEMORY_GRAPH_PORT", "9130"))
MEMORY_GRAPH_BASE = f"http://{MEMORY_GRAPH_HOST}:{MEMORY_GRAPH_PORT}"
MEMORY_GRAPH_DASHBOARD_URL = f"{MEMORY_GRAPH_BASE}/dashboard.html"
MEMORY_GRAPH_API_URL = f"{MEMORY_GRAPH_BASE}/api/fact-graph"
MEMORY_GRAPH_HEALTH_URL = f"{MEMORY_GRAPH_BASE}/health"
MEMORY_GRAPH_RUNTIME_DIR = Path.home() / ".hermes" / "memory-graph"
MEMORY_GRAPH_URL_FILE = MEMORY_GRAPH_RUNTIME_DIR / "cloudflared.url"
MEMORY_GRAPH_LAUNCHER = Path.home() / ".local" / "bin" / "hermes-memory-graph"

_URL_RE = re.compile(r"https://[^\s]+?\.trycloudflare\.com")


def _read_public_base_url() -> str:
    """Return the current public tunnel base URL, if available."""
    try:
        if MEMORY_GRAPH_URL_FILE.exists():
            value = MEMORY_GRAPH_URL_FILE.read_text(encoding="utf-8").strip()
            if value:
                return value.rstrip("/")
    except OSError:
        pass
    return ""


def _extract_public_base_url(text: str) -> str:
    """Extract a trycloudflare URL from launcher output or logs."""
    match = _URL_RE.search(text or "")
    return match.group(0).rstrip("/") if match else ""


def _is_local_healthy(timeout: float = 2.0) -> bool:
    try:
        with urlopen(MEMORY_GRAPH_HEALTH_URL, timeout=timeout) as response:
            return 200 <= getattr(response, "status", 200) < 300
    except (URLError, OSError, ValueError):
        return False


def ensure_memory_graph_ready(timeout: int = 180) -> dict[str, str | bool]:
    """Ensure the memory graph is running and return status details.

    If the local dashboard already responds and a public URL is cached, the
    launcher is not restarted. Otherwise the launcher is invoked in ``up`` mode
    so it can start the backend and/or refresh the tunnel.
    """
    already_running = _is_local_healthy()
    public_base = _read_public_base_url()
    launcher_output = ""

    if not (already_running and public_base):
        if not MEMORY_GRAPH_LAUNCHER.exists():
            raise FileNotFoundError(f"Memory graph launcher not found: {MEMORY_GRAPH_LAUNCHER}")
        result = subprocess.run(
            [str(MEMORY_GRAPH_LAUNCHER), "up"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        launcher_output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        if result.returncode != 0:
            raise RuntimeError((launcher_output or f"Launcher exited with code {result.returncode}").strip())
        if not public_base:
            public_base = _extract_public_base_url(launcher_output) or _read_public_base_url()

    if not public_base:
        public_base = _extract_public_base_url(launcher_output) or _read_public_base_url()

    dashboard_url = f"{public_base}/dashboard.html" if public_base else MEMORY_GRAPH_DASHBOARD_URL
    return {
        "already_running": already_running,
        "public_base_url": public_base,
        "public_dashboard_url": dashboard_url,
        "local_dashboard_url": MEMORY_GRAPH_DASHBOARD_URL,
        "api_url": MEMORY_GRAPH_API_URL,
    }


def format_memory_graph_message(status: dict[str, str | bool]) -> str:
    """Format a user-facing status message for CLI/chat surfaces."""
    lines = ["🧠 Hermes Memory Graph"]
    if status.get("already_running"):
        lines.append("✅ ระบบกำลังทำงานอยู่แล้ว")
    else:
        lines.append("✅ เปิดระบบเรียบร้อยแล้ว")

    public_url = str(status.get("public_dashboard_url") or "").strip()
    if public_url:
        lines.append(f"🌐 Public: {public_url}")
    lines.append(f"🖥 Local: {status.get('local_dashboard_url')}")
    lines.append(f"🔌 API: {status.get('api_url')}")
    return "\n".join(lines)
