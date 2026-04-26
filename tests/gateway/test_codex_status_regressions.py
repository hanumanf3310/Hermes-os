import json
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from gateway.codex_bridge import CodexStatusBridge
import gateway.codex_bridge as codex_bridge
import gateway.codex_tracker as codex_tracker


def _write_state(path: Path, data: dict, timestamp: float) -> None:
    path.write_text(json.dumps({"timestamp": timestamp, "data": data}), encoding="utf-8")


def _write_probe_session(root: Path, session_id: str, *, used_5h: int = 6, used_7d: int = 8) -> Path:
    session_file = root / "2026" / "04" / "25" / f"rollout-2026-04-25T10-00-00-{session_id}.jsonl"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(
        json.dumps(
            {
                "timestamp": "2026-04-25T10:00:00Z",
                "type": "session_meta",
                "payload": {"id": session_id, "originator": "codex_exec", "source": "exec"},
            }
        )
        + "\n"
        + json.dumps(
            {
                "timestamp": "2026-04-25T10:00:02Z",
                "type": "event_msg",
                "originator": "codex_exec",
                "payload": {
                    "type": "token_count",
                    "rate_limits": {
                        "primary": {"used_percent": used_5h, "resets_at": 1777100000},
                        "secondary": {"used_percent": used_7d, "resets_at": 1777600000},
                        "plan_type": "pro",
                    },
                    "info": {
                        "total_token_usage": {"total_tokens": 123},
                        "model_context_window": 258400,
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return session_file


def test_validate_status_data_clamps_impossible_percentages():
    bridge = CodexStatusBridge(plan="A")

    validated = bridge._validate_status_data(
        {
            "context_used": 999999,
            "context_window": 1000,
            "used_5h_pct": 137,
            "left_5h_pct": -37,
            "used_7d_pct": -12,
            "left_7d_pct": 112,
            "plan_type": "pro",
        }
    )

    assert validated is not None
    assert validated["context_window"] == 1000
    assert validated["context_used"] == 1000
    assert validated["context_left_pct"] == 0
    assert validated["used_5h_pct"] == 100
    assert validated["left_5h_pct"] == 0
    assert validated["used_7d_pct"] == 0
    assert validated["left_7d_pct"] == 100


def test_get_latest_session_file_prefers_today_and_parse_latest_data_ignores_yesterday(tmp_path):
    tracker = codex_tracker.CodexRateLimitTracker(sessions_path=str(tmp_path))

    now = datetime.now()
    today_dir = tmp_path / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
    yesterday = now - timedelta(days=1)
    yesterday_dir = tmp_path / yesterday.strftime("%Y") / yesterday.strftime("%m") / yesterday.strftime("%d")
    today_dir.mkdir(parents=True, exist_ok=True)
    yesterday_dir.mkdir(parents=True, exist_ok=True)

    yesterday_file = yesterday_dir / "yesterday.jsonl"
    yesterday_file.write_text(
        json.dumps(
            {
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "rate_limits": {
                        "primary": {"used_percent": 99, "resets_at": 1},
                        "secondary": {"used_percent": 88, "resets_at": 2},
                    },
                    "info": {"total_token_usage": {"total_tokens": 9999}, "model_context_window": 1000},
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    today_file = today_dir / "today.jsonl"
    today_file.write_text(
        json.dumps(
            {
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "rate_limits": {
                        "primary": {"used_percent": 12, "resets_at": 3},
                        "secondary": {"used_percent": 34, "resets_at": 4},
                    },
                    "info": {"total_token_usage": {"total_tokens": 321}, "model_context_window": 1000},
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert tracker.get_latest_session_file() == str(today_file)
    parsed = tracker.parse_latest_data()
    assert parsed is not None
    assert parsed["context_used"] == 321
    assert parsed["used_5h_pct"] == 12
    assert parsed["used_7d_pct"] == 34


def test_plan_a_ignores_stale_bogus_cache_and_uses_live_status(monkeypatch, tmp_path):
    cache_file = tmp_path / "codex_ratelimit.json"
    monkeypatch.setattr(codex_bridge, "CODEX_STATUS_FILE", cache_file)

    stale_bogus = {
        "context_used": 999999,
        "context_window": 1,
        "context_left_pct": 999,
        "used_5h_pct": 999,
        "left_5h_pct": -899,
        "used_7d_pct": -50,
        "left_7d_pct": 150,
        "plan_type": "stale",
    }
    _write_state(cache_file, stale_bogus, time.time() - 10_000)

    class FakeScanner:
        checked_paths = [str(tmp_path / "sessions")]

        def find_latest_status(self):
            return {
                "context_used": 40,
                "context_window": 200,
                "context_left_pct": 80,
                "used_5h_pct": 12,
                "left_5h_pct": 88,
                "used_7d_pct": 33,
                "left_7d_pct": 67,
                "reset_5h": "01:23 น.",
                "reset_7d": "unknown",
                "plan_type": "pro",
                "source": "session_files",
                "is_realtime": True,
                "is_stale": False,
            }

    monkeypatch.setattr(codex_bridge.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("live codex should not run for Plan A")))

    bridge = CodexStatusBridge(plan="A")
    bridge._source_scanner = FakeScanner()
    result = bridge.get_status()

    assert result is not None
    assert result["source"] == "session_files"
    assert result["plan"] == "A"
    assert result["context_used"] == 40
    assert result["context_window"] == 200
    assert result["context_left_pct"] == 80
    assert result["used_5h_pct"] == 12
    assert result["left_5h_pct"] == 88
    assert result["used_7d_pct"] == 33
    assert result["left_7d_pct"] == 67
    assert "cache_age_seconds" not in result


def test_plan_c_active_probe_is_default_primary_source(monkeypatch, tmp_path):
    cache_file = tmp_path / "codex_ratelimit.json"
    monkeypatch.setattr(codex_bridge, "CODEX_STATUS_FILE", cache_file)
    session_id = "019dbdda-aaaa-bbbb-cccc-1fb040ba93e7"
    session_root = tmp_path / ".codex" / "sessions"
    session_file = _write_probe_session(session_root, session_id, used_5h=6, used_7d=8)
    probe_calls = []

    def fake_run(cmd, **kwargs):
        probe_calls.append(cmd)
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps({"session_id": session_id}) + "\n",
            stderr="",
        )

    monkeypatch.setattr(codex_bridge.subprocess, "run", fake_run)
    monkeypatch.setattr(CodexStatusBridge, "_resolve_codex_command", lambda self: ["codex"])

    bridge = CodexStatusBridge(plan="C")
    bridge._source_scanner = codex_bridge.CodexStatusSourceScanner(session_roots=[session_root], vscode_roots=[])

    result = bridge.get_status()

    assert result is not None
    assert probe_calls == [["codex", "exec", "--json", "--skip-git-repo-check", "--color=never", "Hello"]]
    assert result["source"] == "codex_exec_probe"
    assert result["plan"] == "C"
    assert result["source_path"] == str(session_file)
    assert result["originator"] == "codex_exec"
    assert result["used_5h_pct"] == 6
    assert result["left_5h_pct"] == 94
    assert result["used_7d_pct"] == 8
    assert result["left_7d_pct"] == 92
    assert result["probe_consumes_quota"] is True


def test_plan_c_does_not_return_stale_session_as_primary_when_probe_fails(monkeypatch, tmp_path):
    session_root = tmp_path / ".codex" / "sessions"
    _write_probe_session(session_root, "019dbdda-old0-0000-0000-1fb040ba93e7", used_5h=1, used_7d=5)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="auth failed")

    monkeypatch.setattr(codex_bridge.subprocess, "run", fake_run)
    monkeypatch.setattr(CodexStatusBridge, "_resolve_codex_command", lambda self: ["codex"])

    bridge = CodexStatusBridge(plan="C")
    bridge._source_scanner = codex_bridge.CodexStatusSourceScanner(session_roots=[session_root], vscode_roots=[])

    result = bridge.get_status()

    assert result is None
    assert bridge.last_probe_error
    assert "auth failed" in bridge.last_probe_error


def test_stale_cache_is_not_returned_when_refresh_fails(monkeypatch, tmp_path):
    cache_file = tmp_path / "codex_ratelimit.json"
    monkeypatch.setattr(codex_bridge, "CODEX_STATUS_FILE", cache_file)

    _write_state(
        cache_file,
        {
            "context_used": 888888,
            "context_window": 1000,
            "context_left_pct": 888,
            "used_5h_pct": 250,
            "left_5h_pct": -150,
            "used_7d_pct": -25,
            "left_7d_pct": 125,
            "plan_type": "stale",
        },
        time.time() - 10_000,
    )

    bridge = CodexStatusBridge(plan="C")
    monkeypatch.setattr(bridge, "_get_status_via_exec_probe", lambda: None)

    result = bridge.get_status()

    assert result is None


def test_validate_status_data_restores_7d_date_from_cached_source_event(tmp_path):
    session_file = _write_probe_session(tmp_path, "019dc93c-f788-7972-a947-c98bb265bf0e")
    bridge = CodexStatusBridge(plan="B")

    validated = bridge._validate_status_data(
        {
            "context_used": 123,
            "context_window": 258400,
            "used_5h_pct": 2,
            "used_7d_pct": 12,
            "reset_5h": "08:30 PM",
            "reset_7d": "02:31 AM",
            "plan_type": "pro",
            "source_path": str(session_file),
            "line_offset": 1,
        }
    )

    assert validated is not None
    assert validated["reset_7d"] != "02:31 AM"
    assert validated["reset_7d"].startswith("2026-")
    assert validated["reset_7d"].endswith("AM") or validated["reset_7d"].endswith("PM")



def test_compare_plans_returns_structured_result(monkeypatch):
    calls = []

    def fake_get_status(self):
        calls.append(self.plan)
        if self.plan == "A":
            return {
                "context_used": 10,
                "context_window": 100,
                "context_left_pct": 90,
                "used_5h_pct": 10,
                "left_5h_pct": 90,
                "used_7d_pct": 5,
                "left_7d_pct": 95,
                "reset_5h": "unknown",
                "reset_7d": "unknown",
                "plan_type": "pro",
                "source": "session_files",
            }
        return {
            "context_used": 10,
            "context_window": 100,
            "context_left_pct": 90,
            "used_5h_pct": 10,
            "left_5h_pct": 90,
            "used_7d_pct": 5,
            "left_7d_pct": 95,
            "reset_5h": "unknown",
            "reset_7d": "unknown",
            "plan_type": "pro",
            "source": "cache",
        }

    monkeypatch.setattr(CodexStatusBridge, "get_status", fake_get_status)

    comparison = codex_bridge.compare_plans()

    assert comparison["winner"] in {"A", "B"}
    assert set(comparison) >= {"plan_a", "plan_b", "winner", "speedup"}
    assert comparison["plan_a"]["plan"] == "A"
    assert comparison["plan_b"]["plan"] == "B"
    assert comparison["plan_a"]["data"]["source"] == "session_files"
    assert comparison["plan_b"]["data"]["source"] == "cache"
    assert calls == ["A", "B"]
    assert comparison["plan_a"]["latency_ms"] >= 0
    assert comparison["plan_b"]["latency_ms"] >= 0
