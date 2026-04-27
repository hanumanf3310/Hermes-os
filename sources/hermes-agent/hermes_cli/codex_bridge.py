"""Real-time Codex status bridge using session JSONL files.

This module provides:
- Session JSONL parsing for real-time token count data
- Plan A/B/C architecture for flexible data retrieval
- Pretty card formatting for both CLI (rich) and Gateway (markdown)

The bridge reads from ~/.codex/sessions/YYYY/MM/DD/*.jsonl to get
real-time Codex status without relying on the unreliable `codex status` CLI.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CodexRateLimit:
    """Rate limit data for primary or secondary tier."""
    used_percent: float
    resets_at: Optional[str]
    tier: str  # "primary" or "secondary"

    def clamped_percent(self) -> float:
        """Return percentage clamped to 0-100 range."""
        return max(0.0, min(100.0, self.used_percent))


@dataclass(frozen=True)
class CodexStatus:
    """Parsed Codex status from session JSONL."""
    total_tokens: int = 0
    model_context_window: int = 0
    primary_limit: Optional[CodexRateLimit] = None
    secondary_limit: Optional[CodexRateLimit] = None
    timestamp: Optional[str] = None
    session_file: Optional[str] = None
    source: str = "unknown"  # "session_jsonl", "cache", "cli"

    @property
    def context_used_percent(self) -> float:
        """Calculate context window usage percentage, clamped to 0-100."""
        if not self.model_context_window or self.model_context_window <= 0:
            return 0.0
        pct = (self.total_tokens / self.model_context_window) * 100
        return max(0.0, min(100.0, pct))

    def is_valid(self) -> bool:
        """Check if the status has meaningful data."""
        return self.total_tokens >= 0 and self.model_context_window > 0


@dataclass(frozen=True)
class PlanComparison:
    """Result of comparing Plan A, B, and C."""
    plan_a: Optional[CodexStatus]
    plan_b: Optional[CodexStatus]
    plan_c: Optional[CodexStatus]
    winner: str  # "A", "B", "C", or "none"
    speedup: Optional[float]  # Speedup ratio if comparing A vs others
    generated_at: str
    cache_ttl_seconds: int


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def clamp_percentage(value: float) -> float:
    """Clamp a percentage value to the 0-100 range."""
    return max(0.0, min(100.0, value))


# ---------------------------------------------------------------------------
# Session JSONL Parser (Plan A)
# ---------------------------------------------------------------------------

DEFAULT_CODEX_SESSIONS_DIR = Path.home() / ".codex" / "sessions"


def get_today_session_dir() -> Path:
    """Get the session directory for today's date."""
    today = datetime.now()
    return DEFAULT_CODEX_SESSIONS_DIR / f"{today.year:04d}" / f"{today.month:02d}" / f"{today.day:02d}"


def _get_session_originator(session_file: Path) -> Optional[str]:
    """Return the originator recorded in the session meta line, if available."""
    try:
        with session_file.open("r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        if not first_line:
            return None
        data = json.loads(first_line)
        payload = data.get("payload") if isinstance(data, dict) else None
        if isinstance(payload, dict):
            originator = payload.get("originator")
            if originator:
                return str(originator)
        originator = data.get("originator") if isinstance(data, dict) else None
        return str(originator) if originator else None
    except (OSError, IOError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def find_latest_session_file(
    session_dir: Optional[Path] = None,
    exclude_originators: Optional[set[str]] = None,
) -> Optional[Path]:
    """Find the most recent session JSONL file.
    
    Looks for sessions in the specified directory, or searches all dates
    to find the most recent session file.
    Returns None if no session exists.
    """
    exclude_originators = exclude_originators or set()
    
    if session_dir is not None:
        # Specific directory requested
        if not session_dir.exists():
            return None
        jsonl_files = list(session_dir.glob("*.jsonl"))
    else:
        # Search all session directories for most recent
        all_sessions = list(DEFAULT_CODEX_SESSIONS_DIR.rglob("*.jsonl"))
        if not all_sessions:
            return None
        # Sort by modification time, newest first
        all_sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        if exclude_originators:
            for candidate in all_sessions:
                if _get_session_originator(candidate) not in exclude_originators:
                    return candidate
        return all_sessions[0] if all_sessions else None
    
    if not jsonl_files:
        return None
    
    # Sort by modification time, newest first
    jsonl_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if exclude_originators:
        for candidate in jsonl_files:
            if _get_session_originator(candidate) not in exclude_originators:
                return candidate
    return jsonl_files[0]


def parse_token_count_event(line: str) -> Optional[dict[str, Any]]:
    """Parse a single JSONL line looking for token_count events.
    
    Returns the payload if it's a token_count event, None otherwise.
    """
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None
    
    # Look for payload directly
    payload = data.get("payload") if isinstance(data, dict) else None
    if isinstance(payload, dict) and payload.get("type") == "token_count":
        return payload
    
    # Check nested event_msg structure
    event_msg = data.get("event_msg") if isinstance(data, dict) else None
    if isinstance(event_msg, dict):
        event_payload = event_msg.get("payload")
        if isinstance(event_payload, dict) and event_payload.get("type") == "token_count":
            return event_payload
    
    return None


def extract_rate_limit(limit_data: Optional[dict[str, Any]], tier: str) -> Optional[CodexRateLimit]:
    """Extract rate limit data from a limit dictionary."""
    if not isinstance(limit_data, dict):
        return None
    
    # Try to get used_percent directly first (from session files)
    used_percent = limit_data.get("used_percent")
    if used_percent is not None:
        resets_at = limit_data.get("resets_at")
        return CodexRateLimit(
            used_percent=float(used_percent),
            resets_at=str(resets_at) if resets_at else None,
            tier=tier,
        )
    
    # Fallback: calculate from used/limit
    used = limit_data.get("used")
    limit = limit_data.get("limit")
    resets_at = limit_data.get("resets_at")
    
    if used is None or limit is None or limit <= 0:
        return None
    
    used_percent = (used / limit) * 100
    return CodexRateLimit(
        used_percent=used_percent,
        resets_at=resets_at,
        tier=tier,
    )


def parse_session_jsonl(session_file: Path) -> Optional[CodexStatus]:
    """Parse a session JSONL file and extract the latest token_count event.
    
    Scans from newest to oldest to find the most recent token_count event.
    """
    if not session_file.exists():
        return None
    
    try:
        lines = session_file.read_text().strip().split("\n")
    except (IOError, OSError):
        return None
    
    # Scan from newest (last lines) to oldest
    for line in reversed(lines):
        if not line.strip():
            continue
        
        payload = parse_token_count_event(line)
        if payload is None:
            continue
        
        # Extract token usage from nested info structure, with top-level fallback
        info = payload.get("info", {}) if isinstance(payload, dict) else {}
        token_usage = info.get("total_token_usage", {}) if isinstance(info, dict) else {}
        if not token_usage and isinstance(payload, dict):
            token_usage = payload.get("total_token_usage", {})
        total_tokens = token_usage.get("total_tokens", 0) if isinstance(token_usage, dict) else 0
        model_context_window = info.get("model_context_window", 0) if isinstance(info, dict) else 0
        if not model_context_window and isinstance(payload, dict):
            model_context_window = payload.get("model_context_window", 0)
        
        # Extract rate limits
        rate_limits = payload.get("rate_limits", {})
        primary_data = rate_limits.get("primary") if isinstance(rate_limits, dict) else None
        secondary_data = rate_limits.get("secondary") if isinstance(rate_limits, dict) else None
        
        primary_limit = extract_rate_limit(primary_data, "primary")
        secondary_limit = extract_rate_limit(secondary_data, "secondary")
        
        # Extract timestamp from the event
        timestamp = None
        event_data = json.loads(line)
        if isinstance(event_data, dict):
            # Try to get timestamp from various locations
            timestamp = event_data.get("timestamp") or event_data.get("time")
            event_msg = event_data.get("event_msg", {})
            if isinstance(event_msg, dict):
                timestamp = timestamp or event_msg.get("timestamp") or event_msg.get("time")
        
        return CodexStatus(
            total_tokens=total_tokens,
            model_context_window=model_context_window,
            primary_limit=primary_limit,
            secondary_limit=secondary_limit,
            timestamp=timestamp,
            session_file=str(session_file),
            source="session_jsonl",
        )
    
    return None


def get_codex_status_via_exec(timeout: int = 60) -> Optional[CodexStatus]:
    """Get real-time Codex status by running 'codex exec' and reading session JSONL.
    
    This is the recommended method because:
    - Provides complete data including rate limits
    - More stable than parsing stdout
    - Creates a fresh session to get real-time data
    
    Args:
        timeout: Maximum time to wait for codex exec to complete
        
    Returns:
        CodexStatus with real-time data or None if failed
    """
    import subprocess
    import time
    
    try:
        # Step 1: Run codex exec to create a fresh probe session.
        result = subprocess.run(
            ['codex', 'exec', '--json', '--skip-git-repo-check', '--color=never', 'Hello'],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Step 2: Extract the probe thread ID from stdout.
        session_id = None
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get('type') == 'thread.started':
                session_id = data.get('thread_id')
                if session_id:
                    session_id = str(session_id)
                    break
        
        if not session_id:
            return None
        
        # Step 3: Wait briefly for the probe session JSONL to flush, then read
        # the session file that matches this thread_id.
        sessions_dir = DEFAULT_CODEX_SESSIONS_DIR
        session_file = None
        deadline = time.time() + min(5.0, max(1.0, timeout / 12.0))
        while time.time() < deadline:
            matching = list(sessions_dir.rglob(f"*{session_id}*.jsonl"))
            if matching:
                matching.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                session_file = matching[0]
                break
            time.sleep(0.2)
        
        if session_file is None:
            matching = list(sessions_dir.rglob(f"*{session_id}*.jsonl"))
            if matching:
                matching.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                session_file = matching[0]
        
        if session_file is None:
            return None
        
        # Step 4: Parse the probe session file.
        return parse_session_jsonl(session_file)
        
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def get_realtime_codex_status() -> Optional[CodexStatus]:
    """Get real-time Codex status from today's session JSONL files (Plan A).
    
    Returns None if no session exists for today - this is intentional
    to avoid returning stale data.
    """
    session_file = find_latest_session_file(exclude_originators={"codex_exec"})
    if session_file is None:
        session_file = find_latest_session_file()
    if session_file is None:
        return None
    
    return parse_session_jsonl(session_file)


# ---------------------------------------------------------------------------
# Cache Fallback (Plan B)
# ---------------------------------------------------------------------------

DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_cache_path() -> Path:
    """Get the path to the Codex status cache file."""
    # Use a cache in ~/.hermes for consistency with other Hermes data
    hermes_home = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
    cache_dir = hermes_home / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "codex_status.json"


def load_cached_status() -> Optional[CodexStatus]:
    """Load Codex status from cache (Plan B)."""
    cache_path = _get_cache_path()
    if not cache_path.exists():
        return None
    
    try:
        data = json.loads(cache_path.read_text())
    except (json.JSONDecodeError, IOError):
        return None
    
    if not isinstance(data, dict):
        return None
    
    primary_data = data.get("primary_limit")
    secondary_data = data.get("secondary_limit")
    
    return CodexStatus(
        total_tokens=data.get("total_tokens", 0),
        model_context_window=data.get("model_context_window", 0),
        primary_limit=CodexRateLimit(**primary_data) if primary_data else None,
        secondary_limit=CodexRateLimit(**secondary_data) if secondary_data else None,
        timestamp=data.get("timestamp"),
        session_file=data.get("session_file"),
        source="cache",
    )


def save_status_to_cache(status: CodexStatus) -> None:
    """Save Codex status to cache."""
    cache_path = _get_cache_path()
    
    data = {
        "total_tokens": status.total_tokens,
        "model_context_window": status.model_context_window,
        "timestamp": status.timestamp,
        "session_file": status.session_file,
        "source": status.source,
        "primary_limit": {
            "used_percent": status.primary_limit.used_percent if status.primary_limit else None,
            "resets_at": status.primary_limit.resets_at if status.primary_limit else None,
            "tier": "primary",
        } if status.primary_limit else None,
        "secondary_limit": {
            "used_percent": status.secondary_limit.used_percent if status.secondary_limit else None,
            "resets_at": status.secondary_limit.resets_at if status.secondary_limit else None,
            "tier": "secondary",
        } if status.secondary_limit else None,
    }
    
    try:
        cache_path.write_text(json.dumps(data, indent=2))
    except IOError:
        pass  # Cache write failure is non-fatal


# ---------------------------------------------------------------------------
# Plan C: Cache-first with refresh
# ---------------------------------------------------------------------------

def get_status_plan_c() -> Optional[CodexStatus]:
    """Get status using Plan C: cache-first with refresh from session file.
    
    Returns cached data if fresh, otherwise tries to refresh from session.
    Falls back to stale cache if session unavailable.
    """
    # First try to get fresh data from session (Plan A)
    fresh_status = get_realtime_codex_status()
    if fresh_status is not None:
        save_status_to_cache(fresh_status)
        return fresh_status
    
    # Fall back to cache (Plan B)
    cached = load_cached_status()
    if cached is not None:
        return cached
    
    return None


# ---------------------------------------------------------------------------
# Plan Comparison
# ---------------------------------------------------------------------------

import time


def compare_plans() -> PlanComparison:
    """Compare Plan A, B, and C and return structured comparison.
    
    This helps evaluate which approach is fastest and most reliable.
    """
    generated_at = datetime.now().isoformat()
    
    # Plan A: Real-time session JSONL parsing
    start_a = time.perf_counter()
    plan_a = get_realtime_codex_status()
    elapsed_a = time.perf_counter() - start_a
    
    # Plan B: Cache-only
    start_b = time.perf_counter()
    plan_b = load_cached_status()
    elapsed_b = time.perf_counter() - start_b
    
    # Plan C: Cache-first with refresh
    start_c = time.perf_counter()
    plan_c = get_status_plan_c()
    elapsed_c = time.perf_counter() - start_c
    
    # Determine winner based on availability and speed
    # Plan A wins if available (it's real-time)
    # Plan B wins if Plan A unavailable but cache exists
    # Plan C wins if it successfully refreshed
    
    if plan_a is not None:
        winner = "A"
        speedup_b = elapsed_b / elapsed_a if elapsed_a > 0 and elapsed_b > 0 else None
        speedup_c = elapsed_c / elapsed_a if elapsed_a > 0 and elapsed_c > 0 else None
        speedup = min(s for s in [speedup_b, speedup_c] if s is not None) if any([speedup_b, speedup_c]) else None
    elif plan_c is not None:
        winner = "C"
        speedup = None
    elif plan_b is not None:
        winner = "B"
        speedup = None
    else:
        winner = "none"
        speedup = None
    
    return PlanComparison(
        plan_a=plan_a,
        plan_b=plan_b,
        plan_c=plan_c,
        winner=winner,
        speedup=speedup,
        generated_at=generated_at,
        cache_ttl_seconds=DEFAULT_CACHE_TTL_SECONDS,
    )


# ---------------------------------------------------------------------------
# Pretty Card Formatters
# ---------------------------------------------------------------------------

def _format_rate_limit(limit: Optional[CodexRateLimit]) -> str:
    """Format a rate limit for display."""
    if limit is None:
        return "N/A"
    
    pct = limit.clamped_percent()
    pct_str = f"{pct:.1f}%"
    
    if limit.resets_at:
        return f"{pct_str} (resets: {limit.resets_at})"
    return pct_str


def _format_relative_time(timestamp: Optional[str]) -> str:
    """Format a timestamp as relative time."""
    if not timestamp:
        return "unknown"
    
    try:
        # Try ISO format
        if "T" in timestamp:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            delta = datetime.now(ts.tzinfo) - ts
            seconds = delta.total_seconds()
        else:
            # Try unix timestamp
            ts_float = float(timestamp)
            delta = datetime.now().timestamp() - ts_float
            seconds = delta
        
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds / 3600)}h ago"
        else:
            return f"{int(seconds / 86400)}d ago"
    except (ValueError, TypeError):
        return str(timestamp)


def _format_debug_status_lines(status: CodexStatus) -> list[str]:
    """Format detailed debug lines for /gpts --debug output."""
    lines: list[str] = []
    if status.session_file:
        session_path = Path(status.session_file)
        lines.append(f"Session File: {status.session_file}")
        lines.append(f"Session File Name: {session_path.name}")
        lines.append(f"Session Date: {'/'.join(session_path.parts[-4:-1]) if len(session_path.parts) >= 4 else 'unknown'}")
        originator = _get_session_originator(session_path)
        lines.append(f"Originator: {originator or 'unknown'}")
        try:
            mtime = datetime.fromtimestamp(session_path.stat().st_mtime)
            lines.append(f"File Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        except OSError:
            lines.append("File Modified: unavailable")
    else:
        lines.append("Session File: unknown")
    
    if status.timestamp:
        lines.append(f"Event Timestamp: {status.timestamp}")
        lines.append(f"Event Age: {_format_relative_time(status.timestamp)}")
    else:
        lines.append("Event Timestamp: unknown")
    
    lines.append(f"Source: {status.source}")
    return lines


def format_status_markdown(status: Optional[CodexStatus], show_source: bool = False, debug: bool = False) -> str:
    """Format Codex status as a markdown card for gateway display.
    
    Returns a message indicating no session if status is None.
    """
    if status is None:
        return (
            "🤖 **Codex GPT Status**\n\n"
            "No Codex session found for today.\n\n"
            "Start a Codex session with: `codex`"
        )
    
    lines = [
        "🤖 **Codex GPT Status**",
        "",
        f"**Primary Rate Limit:** {_format_rate_limit(status.primary_limit)}",
        f"**Secondary Rate Limit:** {_format_rate_limit(status.secondary_limit)}",
        f"**Total Tokens:** {status.total_tokens:,}",
        f"**Context Used:** {status.context_used_percent:.1f}%",
    ]
    
    if show_source:
        lines.extend([
            "",
            f"_Source: {status.source}_",
        ])
    
    if status.timestamp:
        lines.append(f"_Updated: {_format_relative_time(status.timestamp)}_")
    
    if debug:
        lines.extend(["", "**Debug:**"])
        lines.extend([f"- {line}" for line in _format_debug_status_lines(status)])
    
    return "\n".join(lines)


def format_status_rich(status: Optional[CodexStatus], show_source: bool = False, debug: bool = False) -> str:
    """Format Codex status as a rich text card for CLI display.
    
    Uses simple text formatting that works with rich library or plain terminal.
    """
    if status is None:
        return (
            "🤖 Codex GPT Status\n\n"
            "No Codex session found for today.\n\n"
            "Start a Codex session with: codex"
        )
    
    lines = [
        "🤖 Codex GPT Status",
        "",
        f"Primary Rate Limit:   {_format_rate_limit(status.primary_limit)}",
        f"Secondary Rate Limit: {_format_rate_limit(status.secondary_limit)}",
        f"Total Tokens:         {status.total_tokens:,}",
        f"Context Used:         {status.context_used_percent:.1f}%",
    ]
    
    if show_source:
        lines.extend([
            "",
            f"Source: {status.source}",
        ])
    
    if status.timestamp:
        lines.append(f"Updated: {_format_relative_time(status.timestamp)}")
    
    if debug:
        lines.extend(["", "Debug:"])
        lines.extend([f"- {line}" for line in _format_debug_status_lines(status)])
    
    return "\n".join(lines)


def format_comparison_markdown(comparison: PlanComparison) -> str:
    """Format Plan A/B/C comparison as markdown."""
    lines = [
        "⚡ **Codex Status Plan Comparison**",
        "",
        f"**Winner:** Plan {comparison.winner}",
    ]
    
    if comparison.speedup is not None:
        lines.append(f"**Speedup:** {comparison.speedup:.2f}x")
    
    lines.extend([
        "",
        "**Plan A (Session JSONL):**",
        f"  Available: {'✓' if comparison.plan_a else '✗'}",
    ])
    
    if comparison.plan_a:
        lines.append(f"  Tokens: {comparison.plan_a.total_tokens:,}")
    
    lines.extend([
        "",
        "**Plan B (Cache):**",
        f"  Available: {'✓' if comparison.plan_b else '✗'}",
    ])
    
    if comparison.plan_b:
        lines.append(f"  Tokens: {comparison.plan_b.total_tokens:,}")
    
    lines.extend([
        "",
        "**Plan C (Cache+Refresh):**",
        f"  Available: {'✓' if comparison.plan_c else '✗'}",
    ])
    
    if comparison.plan_c:
        lines.append(f"  Tokens: {comparison.plan_c.total_tokens:,}")
    
    lines.extend([
        "",
        f"_Cache TTL: {comparison.cache_ttl_seconds}s_",
        f"_Generated: {comparison.generated_at}_",
    ])
    
    return "\n".join(lines)


def format_comparison_rich(comparison: PlanComparison) -> str:
    """Format Plan A/B/C comparison for CLI display."""
    lines = [
        "⚡ Codex Status Plan Comparison",
        "",
        f"Winner: Plan {comparison.winner}",
    ]
    
    if comparison.speedup is not None:
        lines.append(f"Speedup: {comparison.speedup:.2f}x")
    
    lines.extend([
        "",
        "Plan A (Session JSONL):",
        f"  Available: {'Yes' if comparison.plan_a else 'No'}",
    ])
    
    if comparison.plan_a:
        lines.append(f"  Tokens: {comparison.plan_a.total_tokens:,}")
    
    lines.extend([
        "",
        "Plan B (Cache):",
        f"  Available: {'Yes' if comparison.plan_b else 'No'}",
    ])
    
    if comparison.plan_b:
        lines.append(f"  Tokens: {comparison.plan_b.total_tokens:,}")
    
    lines.extend([
        "",
        "Plan C (Cache+Refresh):",
        f"  Available: {'Yes' if comparison.plan_c else 'No'}",
    ])
    
    if comparison.plan_c:
        lines.append(f"  Tokens: {comparison.plan_c.total_tokens:,}")
    
    lines.extend([
        "",
        f"Cache TTL: {comparison.cache_ttl_seconds}s",
        f"Generated: {comparison.generated_at}",
    ])
    
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_codex_status(use_cache: bool = False, refresh: bool = True) -> Optional[CodexStatus]:
    """Get Codex status with specified strategy.
    
    Args:
        use_cache: If True, use cache-only (Plan B). If False, use real-time (Plan A).
        refresh: If True and use_cache is False, use Plan C (cache-first with refresh).
    
    Returns:
        CodexStatus if available, None otherwise (no session found for today).
    """
    if use_cache:
        return load_cached_status()
    
    if refresh:
        return get_status_plan_c()
    
    return get_realtime_codex_status()


def format_status(status: Optional[CodexStatus], format: str = "rich", show_source: bool = False) -> str:
    """Format status for the specified output format.
    
    Args:
        status: The CodexStatus to format, or None for "no session" message.
        format: Either "rich" (CLI) or "markdown" (gateway).
        show_source: Whether to include the data source in output.
    
    Returns:
        Formatted status string.
    """
    if format == "markdown":
        return format_status_markdown(status, show_source)
    return format_status_rich(status, show_source)
