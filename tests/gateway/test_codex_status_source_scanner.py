"""Regression tests for realtime Codex status source scanning."""

import json
import os
from pathlib import Path

from gateway.codex_bridge import CodexStatusBridge, CodexStatusSourceScanner


def _token_event(total_tokens: int, *, event_at: str = "2026-04-25T08:00:00Z", originator: str = "vscode") -> dict:
    return {
        "type": "event_msg",
        "timestamp": event_at,
        "originator": originator,
        "payload": {
            "type": "token_count",
            "rate_limits": {
                "primary": {"used_percent": 21, "resets_at": 1777100000},
                "secondary": {"used_percent": 34, "resets_at": 1777600000},
                "plan_type": "pro",
            },
            "info": {
                "total_token_usage": {"total_tokens": total_tokens},
                "model_context_window": 272000,
            },
        },
    }


def _write_jsonl(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")


def test_scanner_reads_windows_codex_sessions(tmp_path):
    """Scanner should read Windows-style Codex session roots, not only WSL today's path."""
    windows_root = tmp_path / "mnt" / "c" / "Users" / "Boss" / ".codex" / "sessions"
    session_file = windows_root / "2026" / "04" / "25" / "session.jsonl"
    _write_jsonl(session_file, [_token_event(1234, originator="vscode")])

    scanner = CodexStatusSourceScanner(session_roots=[windows_root], vscode_roots=[])
    result = scanner.find_latest_status()

    assert result is not None
    assert result["context_used"] == 1234
    assert result["context_window"] == 272000
    assert result["source"] == "session_files"
    assert result["source_path"] == str(session_file)
    assert result["originator"] == "vscode"
    assert result["is_realtime"] is True


def test_scanner_prefers_latest_valid_token_count_not_newest_file_without_token_count(tmp_path):
    root = tmp_path / ".codex" / "sessions"
    valid_file = root / "2026" / "04" / "25" / "valid.jsonl"
    empty_newer_file = root / "2026" / "04" / "25" / "newer-no-token.jsonl"

    _write_jsonl(valid_file, [_token_event(2000, event_at="2026-04-25T08:00:00Z")])
    _write_jsonl(empty_newer_file, [{"type": "event_msg", "payload": {"type": "other"}}])
    os.utime(valid_file, (1000, 1000))
    os.utime(empty_newer_file, (2000, 2000))

    scanner = CodexStatusSourceScanner(session_roots=[root], vscode_roots=[])
    result = scanner.find_latest_status()

    assert result is not None
    assert result["context_used"] == 2000
    assert result["source_path"] == str(valid_file)


def test_realtime_context_advances_after_new_token_count_event(tmp_path):
    root = tmp_path / ".codex" / "sessions"
    session_file = root / "2026" / "04" / "25" / "session.jsonl"
    _write_jsonl(session_file, [_token_event(1000, event_at="2026-04-25T08:00:00Z")])

    bridge = CodexStatusBridge(plan="A")
    bridge._source_scanner = CodexStatusSourceScanner(session_roots=[root], vscode_roots=[])
    first = bridge.get_status()

    with session_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(_token_event(1500, event_at="2026-04-25T08:01:00Z")) + "\n")
    os.utime(session_file, (3000, 3000))

    second = bridge.get_status(expect_advance=True)

    assert first is not None and second is not None
    assert second["context_used"] == 1500
    assert second["context_used"] != first["context_used"]
    assert second["event_timestamp"] != first["event_timestamp"]
    assert second["line_offset"] != first["line_offset"]
    assert second["realtime_fingerprint"] != first["realtime_fingerprint"]
    assert not second.get("freshness_warning")


def test_unchanged_realtime_fingerprint_warns_when_activity_expected(tmp_path):
    root = tmp_path / ".codex" / "sessions"
    session_file = root / "2026" / "04" / "25" / "session.jsonl"
    _write_jsonl(session_file, [_token_event(1000, event_at="2026-04-25T08:00:00Z")])

    bridge = CodexStatusBridge(plan="A")
    bridge._source_scanner = CodexStatusSourceScanner(session_roots=[root], vscode_roots=[])
    first = bridge.get_status()
    second = bridge.get_status(expect_advance=True)

    assert first is not None and second is not None
    assert second["realtime_fingerprint"] == first["realtime_fingerprint"]
    assert second.get("freshness_warning")
    assert "did not advance" in second["freshness_warning"].lower()
