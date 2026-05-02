"""Codex status bridge.

Provides three plan modes:
- Plan A: live `codex status` only
- Plan B: cached-file only
- Plan C: smart cache with refresh + stale fallback

Also exposes a real `compare_plans()` helper for CLI/gateway compare mode.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from hermes_constants import get_hermes_home

CACHE_TTL_SECONDS = 300
DEFAULT_CONTEXT_WINDOW = 258400
DEFAULT_CACHE_NAME = "codex_ratelimit.json"
DEFAULT_LOG_NAME = "codex_bridge.log"


def _default_status_file() -> Path:
    return get_hermes_home() / DEFAULT_CACHE_NAME


def _default_log_file() -> Path:
    return get_hermes_home() / DEFAULT_LOG_NAME


# Module-level defaults remain monkeypatch-friendly for tests.
CODEX_STATUS_FILE = _default_status_file()
BRIDGE_LOG_FILE = _default_log_file()


def _status_file() -> Path:
    return Path(globals().get("CODEX_STATUS_FILE", _default_status_file()))


def _log_file() -> Path:
    return Path(globals().get("BRIDGE_LOG_FILE", _default_log_file()))


def _clamp_int(value: Any, low: int, high: int, default: int = 0) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def _parse_event_ts(value: Any) -> float:
    """Parse event timestamps for candidate ordering; return 0 on failure."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        text = value.strip()
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            return datetime.fromisoformat(text).timestamp()
        except ValueError:
            return 0.0
    return 0.0


class CodexStatusSourceScanner:
    """Find realtime Codex token_count events across WSL/Windows session roots."""

    def __init__(
        self,
        session_roots: Optional[Iterable[str | Path]] = None,
        vscode_roots: Optional[Iterable[str | Path]] = None,
    ):
        self.session_roots = [Path(p).expanduser() for p in (session_roots if session_roots is not None else self.default_session_roots())]
        self.vscode_roots = [Path(p).expanduser() for p in (vscode_roots if vscode_roots is not None else self.default_vscode_roots())]
        self.checked_paths: list[str] = []

    @staticmethod
    def default_session_roots() -> list[Path]:
        roots: list[Path] = []
        codex_home = os.environ.get("CODEX_HOME", "").strip()
        if codex_home:
            roots.append(Path(codex_home).expanduser() / "sessions")
        roots.append(Path.home() / ".codex" / "sessions")
        users_root = Path("/mnt/c/Users")
        if users_root.exists():
            for user_dir in users_root.iterdir():
                roots.append(user_dir / ".codex" / "sessions")
        return roots

    @staticmethod
    def default_vscode_roots() -> list[Path]:
        roots: list[Path] = []
        users_root = Path("/mnt/c/Users")
        if users_root.exists():
            for user_dir in users_root.iterdir():
                roots.extend([
                    user_dir / "AppData" / "Roaming" / "Code" / "User" / "globalStorage",
                    user_dir / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage",
                ])
        return roots

    def _candidate_files(self) -> list[Path]:
        files: list[Path] = []
        self.checked_paths = []
        for root in [*self.session_roots, *self.vscode_roots]:
            self.checked_paths.append(str(root))
            if not root.exists():
                continue
            try:
                files.extend(p for p in root.rglob("*.jsonl") if p.is_file())
            except OSError:
                continue
        # Prefer recently modified files for efficient parse ordering, but still
        # parse all candidates so a newer file without token_count cannot hide an
        # older valid realtime source.
        files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        return files

    def _extract_from_file(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            stat = path.stat()
        except OSError:
            return None

        session_id = None
        session_originator = None
        for raw_meta in lines[:20]:
            try:
                meta = json.loads(raw_meta)
            except json.JSONDecodeError:
                continue
            if meta.get("type") == "session_meta":
                payload = meta.get("payload", {}) or {}
                session_id = payload.get("id") or session_id
                session_originator = payload.get("originator") or payload.get("source") or session_originator
                break

        for idx in range(len(lines) - 1, -1, -1):
            raw = lines[idx].strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "event_msg":
                continue
            payload = event.get("payload", {}) or {}
            if payload.get("type") != "token_count":
                continue
            data = self._transform_payload(payload)
            event_timestamp = event.get("timestamp") or payload.get("timestamp") or payload.get("created_at")
            event_timestamp_sort = _parse_event_ts(event_timestamp)
            age_seconds = None
            if event_timestamp_sort:
                age_seconds = max(0.0, time.time() - event_timestamp_sort)
            data.update({
                "source": "session_files",
                "source_path": str(path),
                "source_mtime": stat.st_mtime,
                "source_age_seconds": round(age_seconds, 1) if age_seconds is not None else None,
                "event_timestamp": event_timestamp,
                "event_timestamp_sort": event_timestamp_sort,
                "session_id": session_id,
                "originator": event.get("originator") or payload.get("originator") or session_originator or "unknown",
                "line_offset": idx,
                "is_realtime": True,
                "is_stale": bool(age_seconds is not None and age_seconds > CACHE_TTL_SECONDS),
            })
            data["realtime_fingerprint"] = {
                "source_path": data["source_path"],
                "source_mtime": data["source_mtime"],
                "event_timestamp": data["event_timestamp"],
                "context_used": data["context_used"],
                "line_offset": data["line_offset"],
            }
            return data
        return None

    def _transform_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        rate_limits = payload.get("rate_limits", {}) or {}
        primary = rate_limits.get("primary", {}) or rate_limits.get("5h", {}) or {}
        secondary = rate_limits.get("secondary", {}) or rate_limits.get("7d", {}) or {}
        info = payload.get("info", {}) or {}
        token_usage = info.get("total_token_usage", {}) or payload.get("total_token_usage", {}) or {}
        context_window = info.get("model_context_window", payload.get("model_context_window", DEFAULT_CONTEXT_WINDOW))
        context_used = token_usage.get("total_tokens", payload.get("total_tokens", 0))
        return {
            "context_used": context_used,
            "context_window": context_window,
            "context_left_pct": 100,
            "used_5h_pct": primary.get("used_percent", 0),
            "left_5h_pct": 100 - _clamp_int(primary.get("used_percent", 0), 0, 100, 0),
            "reset_5h": CodexStatusBridge._format_reset_time_static(primary.get("resets_at"), include_date=False),
            "used_7d_pct": secondary.get("used_percent", 0),
            "left_7d_pct": 100 - _clamp_int(secondary.get("used_percent", 0), 0, 100, 0),
            "reset_7d": CodexStatusBridge._format_reset_time_static(secondary.get("resets_at"), include_date=True),
            "plan_type": rate_limits.get("plan_type", "unknown"),
        }

    def find_latest_status(self, session_id: str | None = None, min_mtime: float | None = None) -> Optional[Dict[str, Any]]:
        candidates = []
        for path in self._candidate_files():
            if min_mtime is not None:
                try:
                    if path.stat().st_mtime < min_mtime:
                        continue
                except OSError:
                    continue
            if session_id and session_id not in path.name:
                # Some Codex builds include the id only in session_meta, so parse
                # and filter below instead of skipping the file unconditionally.
                parsed = self._extract_from_file(path)
                if not parsed or parsed.get("session_id") != session_id:
                    continue
            else:
                parsed = self._extract_from_file(path)
            if parsed:
                candidates.append(parsed)
        if not candidates:
            return None
        candidates.sort(
            key=lambda item: (
                item.get("event_timestamp_sort") or 0,
                item.get("source_mtime") or 0,
                item.get("line_offset") or 0,
            ),
            reverse=True,
        )
        result = dict(candidates[0])
        result.pop("event_timestamp_sort", None)
        return result


class CodexStatusBridge:
    """Fetch, cache, and compare Codex GPT status data."""

    def __init__(self, plan: str | None = None):
        self.plan = self._normalize_plan(plan or "C")
        self._source_scanner: Optional[CodexStatusSourceScanner] = None
        self._last_realtime_fingerprint: Optional[Dict[str, Any]] = None
        self.last_probe_error: Optional[str] = None

    @staticmethod
    def _normalize_plan(plan: str) -> str:
        normalized = str(plan).strip().upper()
        aliases = {
            "DIRECT": "A",
            "REALTIME": "A",
            "REAL-TIME": "A",
            "CACHE": "B",
            "CACHED": "B",
            "BALANCED": "C",
        }
        return aliases.get(normalized, normalized if normalized in {"A", "B", "C"} else "C")

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            log_path = _log_file()
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass

    def _validate_status_data(self, data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Clamp impossible values so bad cache/session data cannot leak out."""
        if not data:
            return None

        try:
            validated = dict(data)

            context_window = _clamp_int(validated.get("context_window", DEFAULT_CONTEXT_WINDOW), 1, 10**9, DEFAULT_CONTEXT_WINDOW)
            context_used = _clamp_int(validated.get("context_used", 0), 0, context_window, 0)
            context_left_pct = round((1 - (context_used / context_window)) * 100)
            context_left_pct = _clamp_int(context_left_pct, 0, 100, 0)

            validated["context_window"] = context_window
            validated["context_used"] = context_used
            validated["context_left_pct"] = context_left_pct

            for used_key, left_key in (("used_5h_pct", "left_5h_pct"), ("used_7d_pct", "left_7d_pct")):
                used_value = _clamp_int(validated.get(used_key, 0), 0, 100, 0)
                validated[used_key] = used_value
                validated[left_key] = 100 - used_value

            validated["reset_5h"] = validated.get("reset_5h", "unknown") or "unknown"
            validated["reset_7d"] = self._ensure_7d_reset_has_date(validated)
            validated["plan_type"] = validated.get("plan_type", "unknown") or "unknown"
            return validated
        except Exception as exc:
            self._log(f"Validation error: {exc}")
            return None

    @staticmethod
    def _looks_date_time(value: Any) -> bool:
        return isinstance(value, str) and bool(re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+[AP]M$", value.strip()))

    def _reset_7d_from_source_event(self, data: Dict[str, Any]) -> Optional[str]:
        source_path = data.get("source_path")
        line_offset = data.get("line_offset")
        if not source_path:
            return None
        try:
            lines = Path(str(source_path)).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return None

        offsets: list[int] = []
        if isinstance(line_offset, int) and 0 <= line_offset < len(lines):
            offsets.append(line_offset)
        offsets.extend(range(len(lines) - 1, -1, -1))

        seen: set[int] = set()
        for idx in offsets:
            if idx in seen:
                continue
            seen.add(idx)
            try:
                event = json.loads(lines[idx])
            except (IndexError, json.JSONDecodeError):
                continue
            if event.get("type") != "event_msg":
                continue
            payload = event.get("payload", {}) or {}
            if payload.get("type") != "token_count":
                continue
            rate_limits = payload.get("rate_limits", {}) or {}
            secondary = rate_limits.get("secondary", {}) or rate_limits.get("7d", {}) or {}
            formatted = self._format_reset_time(secondary.get("resets_at"), include_date=True)
            if self._looks_date_time(formatted):
                return formatted
        return None

    def _ensure_7d_reset_has_date(self, data: Dict[str, Any]) -> str:
        reset_7d = data.get("reset_7d", "unknown") or "unknown"
        if self._looks_date_time(reset_7d) or reset_7d == "unknown":
            return str(reset_7d)
        from_source = self._reset_7d_from_source_event(data)
        return from_source or str(reset_7d)

    def _resolve_codex_command(self) -> list[str]:
        hermes_home = get_hermes_home()
        candidates = [
            hermes_home / "bin" / "codex",
            hermes_home / "node" / "bin" / "codex",
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return [str(candidate)]

        which = shutil.which("codex")
        if which:
            return [which]
        return ["codex"]

    def _transform_codex_api_format(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            rate_limits = data.get("rate_limits", {}) or {}
            primary = rate_limits.get("primary", {}) or rate_limits.get("5h", {}) or {}
            secondary = rate_limits.get("secondary", {}) or rate_limits.get("7d", {}) or {}

            info = data.get("info", {}) or {}
            token_usage = info.get("total_token_usage", {}) or {}
            context_window = info.get("model_context_window", DEFAULT_CONTEXT_WINDOW)
            context_used = token_usage.get("total_tokens", 0)

            payload = {
                "context_used": context_used,
                "context_window": context_window,
                "context_left_pct": round((1 - (_clamp_int(context_used, 0, 10**12, 0) / max(_clamp_int(context_window, 1, 10**12, DEFAULT_CONTEXT_WINDOW), 1))) * 100),
                "used_5h_pct": primary.get("used_percent", 0),
                "left_5h_pct": 100 - _clamp_int(primary.get("used_percent", 0), 0, 100, 0),
                "reset_5h": self._format_reset_time(primary.get("resets_at"), include_date=False),
                "used_7d_pct": secondary.get("used_percent", 0),
                "left_7d_pct": 100 - _clamp_int(secondary.get("used_percent", 0), 0, 100, 0),
                "reset_7d": self._format_reset_time(secondary.get("resets_at"), include_date=True),
                "plan_type": rate_limits.get("plan_type", "unknown"),
                "latency_ms": None,
            }
            return self._validate_status_data(payload)
        except Exception as exc:
            self._log(f"Transform error: {exc}")
            return None

    def _parse_text_output(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            result: Dict[str, Any] = {}
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue

                match = re.match(r"5h limit:\s*(\d+)%\s*used", line, re.IGNORECASE)
                if match:
                    result["used_5h_pct"] = int(match.group(1))
                    result["left_5h_pct"] = 100 - int(match.group(1))
                    continue

                match = re.match(r"7d limit:\s*(\d+)%\s*used", line, re.IGNORECASE)
                if match:
                    result["used_7d_pct"] = int(match.group(1))
                    result["left_7d_pct"] = 100 - int(match.group(1))
                    continue

                match = re.search(r"(\d+)\s*/\s*(\d+)\s*tokens", line)
                if match:
                    result["context_used"] = int(match.group(1).replace(",", ""))
                    result["context_window"] = int(match.group(2).replace(",", ""))
                    continue

                if "resets" in line.lower() and "5h" in line.lower():
                    result["reset_5h"] = line.split(":", 1)[-1].strip() if ":" in line else "unknown"
                if "resets" in line.lower() and "7d" in line.lower():
                    result["reset_7d"] = line.split(":", 1)[-1].strip() if ":" in line else "unknown"

            result.setdefault("context_window", DEFAULT_CONTEXT_WINDOW)
            result.setdefault("context_used", 0)
            result.setdefault("context_left_pct", 100)
            result.setdefault("used_5h_pct", 0)
            result.setdefault("left_5h_pct", 100)
            result.setdefault("used_7d_pct", 0)
            result.setdefault("left_7d_pct", 100)
            result.setdefault("reset_5h", "unknown")
            result.setdefault("reset_7d", "unknown")
            result.setdefault("plan_type", "unknown")
            return self._validate_status_data(result)
        except Exception as exc:
            self._log(f"Text parse error: {exc}")
            return None

    @staticmethod
    def _format_reset_time_static(epoch_ts: Any, *, include_date: bool = False) -> str:
        """Format reset time in Bangkok timezone.

        5h limit keeps time-only output (HH:MM AM/PM), while 7d shows date+time.
        """
        if not epoch_ts:
            return "unknown"
        try:
            from datetime import timedelta

            reset_dt = datetime.fromtimestamp(float(epoch_ts), tz=timezone.utc)
            local_tz = timezone(timedelta(hours=7))  # Bangkok UTC+7
            reset_local = reset_dt.astimezone(local_tz)

            if include_date:
                # e.g. "2026-04-26 05:01 AM"
                return reset_local.strftime("%Y-%m-%d %I:%M %p")

            # Keep 5h as time-only (AM/PM) per current format contract.
            return reset_local.strftime("%I:%M %p")
        except Exception:
            return "unknown"

    def _format_reset_time(self, epoch_ts: Any, *, include_date: bool = False) -> str:
        return self._format_reset_time_static(epoch_ts, include_date=include_date)

    def _get_status_from_session_files(self, session_id: str | None = None, min_mtime: float | None = None) -> Optional[Dict[str, Any]]:
        """Fetch realtime status from Codex session JSONL files across known roots."""
        try:
            scanner = self._source_scanner or CodexStatusSourceScanner()
            self._source_scanner = scanner
            try:
                data = scanner.find_latest_status(session_id=session_id, min_mtime=min_mtime)
            except TypeError:
                data = scanner.find_latest_status()
            validated = self._validate_status_data(data)
            if validated:
                validated["source"] = data.get("source", "session_files") if data else "session_files"
                checked = getattr(scanner, "checked_paths", [])
                if checked:
                    validated["checked_paths"] = checked
            return validated
        except Exception as exc:
            self._log(f"Session file scanner error: {exc}")
            return None

    def _mark_freshness(self, data: Optional[Dict[str, Any]], expect_advance: bool = False) -> Optional[Dict[str, Any]]:
        if not data:
            return None
        fingerprint = data.get("realtime_fingerprint")
        if expect_advance and fingerprint and fingerprint == self._last_realtime_fingerprint:
            data["freshness_warning"] = "Realtime source did not advance — data may be stale/wrong"
            data["is_stale"] = True
        elif fingerprint:
            data.pop("freshness_warning", None)
            data.setdefault("is_stale", False)
        if fingerprint:
            self._last_realtime_fingerprint = dict(fingerprint)
        return data

    def _read_cache_state(self) -> Optional[tuple[Dict[str, Any], Optional[float]]]:
        cache_path = _status_file()
        if not cache_path.exists():
            return None

        try:
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self._log(f"Cache read error: {exc}")
            return None

        if isinstance(raw, dict) and "data" in raw:
            data = raw.get("data")
            timestamp = raw.get("timestamp")
        else:
            data = raw
            timestamp = None

        if not isinstance(data, dict):
            return None

        validated = self._validate_status_data(data)
        if not validated:
            return None

        age_seconds: Optional[float] = None
        if timestamp is not None:
            try:
                age_seconds = max(0.0, time.time() - float(timestamp))
            except (TypeError, ValueError):
                age_seconds = None
        return validated, age_seconds

    def _write_cache_state(self, data: Dict[str, Any]) -> None:
        cache_path = _status_file()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": time.time(),
            "data": data,
        }
        cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _extract_session_id_from_exec_output(self, text: str) -> Optional[str]:
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                obj = None
            if isinstance(obj, dict):
                for key in ("session_id", "sessionId", "id"):
                    value = obj.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                payload = obj.get("payload")
                if isinstance(payload, dict):
                    value = payload.get("session_id") or payload.get("id")
                    if isinstance(value, str) and value.strip():
                        return value.strip()
            match = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", line, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def _get_status_via_exec_probe(self) -> Optional[Dict[str, Any]]:
        """Actively refresh Codex status by creating a minimal exec session."""
        self.last_probe_error = None
        started_at = time.time()
        cmd = self._resolve_codex_command() + ["exec", "--json", "--skip-git-repo-check", "--color=never", "Hello"]
        try:
            self._log(f"Running Codex exec probe: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="ignore",
                check=False,
            )
        except FileNotFoundError as exc:
            self.last_probe_error = f"codex exec unavailable: {exc}"
            self._log(self.last_probe_error)
            return None
        except subprocess.TimeoutExpired as exc:
            self.last_probe_error = f"codex exec probe timeout: {exc}"
            self._log(self.last_probe_error)
            return None
        except Exception as exc:
            self.last_probe_error = f"codex exec probe error: {exc}"
            self._log(self.last_probe_error)
            return None

        output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            self.last_probe_error = f"codex exec probe failed (rc={result.returncode}): {detail}"
            self._log(self.last_probe_error)
            return None

        session_id = self._extract_session_id_from_exec_output(output)
        if not session_id:
            self.last_probe_error = "codex exec probe did not report a session_id"
            self._log(self.last_probe_error)
            return None

        data = self._get_status_from_session_files(session_id=session_id, min_mtime=started_at - 5)
        if not data:
            data = self._get_status_from_session_files(session_id=session_id)
        if not data:
            self.last_probe_error = f"codex exec session {session_id} did not produce token_count data"
            self._log(self.last_probe_error)
            return None

        data["source"] = "codex_exec_probe"
        data["session_id"] = session_id
        data["probe_consumes_quota"] = True
        data["probe_command"] = "codex exec --json --skip-git-repo-check --color=never Hello"
        data["is_stale"] = False
        data.pop("freshness_warning", None)
        return self._validate_status_data(data)

    def _fetch_live_status(self) -> Optional[Dict[str, Any]]:
        """Fetch from live `codex status` only."""
        try:
            cmd = self._resolve_codex_command() + ["status"]
            self._log(f"Running live command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="ignore",
                check=False,
            )

            output = (result.stdout or "").strip()
            if not output:
                self._log(f"Direct codex status returned no output (rc={result.returncode})")
                return None

            try:
                parsed = json.loads(output)
            except json.JSONDecodeError:
                parsed = None

            if isinstance(parsed, dict):
                data = self._transform_codex_api_format(parsed)
            else:
                data = self._parse_text_output(output)

            if data:
                data["source"] = "direct_status"
                return data

            self._log(f"Direct codex status returned no usable data (rc={result.returncode})")
            return None
        except FileNotFoundError as exc:
            self._log(f"Direct codex status unavailable: {exc}")
            return None
        except subprocess.TimeoutExpired as exc:
            self._log(f"Direct codex status timeout: {exc}")
            return None
        except Exception as exc:
            self._log(f"Direct live fetch error: {exc}")
            return None

    def get_status(self, expect_advance: bool = False) -> Optional[Dict[str, Any]]:
        """Return Codex status according to the selected plan."""
        if self.plan == "A":
            self._log("Plan A - real-time session fetch")
            data = self._get_status_from_session_files()
            if data:
                data["plan"] = "A"
                return self._mark_freshness(self._validate_status_data(data), expect_advance=expect_advance)
            return None

        if self.plan == "B":
            cached = self._read_cache_state()
            if not cached:
                return None
            data, age_seconds = cached
            data["source"] = "cache"
            data["plan"] = "B"
            data["cache_age_seconds"] = round(age_seconds, 1) if age_seconds is not None else None
            return data

        # Plan C: active refresh via Codex exec probe. Passive local data is
        # useful for debugging only; stale local state is not a valid primary
        # answer for /gpts.
        probed = self._get_status_via_exec_probe()
        if probed:
            probed["plan"] = "C"
            probed["cache_saved"] = True
            try:
                self._write_cache_state(probed)
            except Exception as exc:
                self._log(f"Cache save error: {exc}")
                probed["cache_saved"] = False
            return self._mark_freshness(self._validate_status_data(probed), expect_advance=False)

        return None

    async def get_status_async(self) -> Optional[Dict[str, Any]]:
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_status)

    def compare_plans(self) -> Dict[str, Any]:
        """Compare Plan A vs Plan B and return a structured result dict."""

        def timed_get(plan: str) -> Dict[str, Any]:
            bridge = self.__class__(plan=plan)
            start = time.perf_counter()
            error: Optional[str] = None
            data: Optional[Dict[str, Any]] = None
            try:
                data = bridge.get_status()
            except Exception as exc:
                error = str(exc)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            success = data is not None and error is None
            if data is not None:
                data = dict(data)
                data["plan"] = plan
                data["latency_ms"] = latency_ms
            return {
                "plan": plan,
                "success": success,
                "latency_ms": latency_ms,
                "data": data,
                "error": error,
            }

        plan_a = timed_get("A")
        plan_b = timed_get("B")

        winner: str = "N/A"
        speedup: float | str = "N/A"
        if plan_a["success"] and plan_b["success"]:
            a_latency = max(float(plan_a["latency_ms"]), 0.001)
            b_latency = max(float(plan_b["latency_ms"]), 0.001)
            if a_latency <= b_latency:
                winner = "A"
                speedup = round(b_latency / a_latency, 2)
            else:
                winner = "B"
                speedup = round(a_latency / b_latency, 2)
        elif plan_a["success"]:
            winner = "A"
        elif plan_b["success"]:
            winner = "B"

        return {
            "plan_a": plan_a,
            "plan_b": plan_b,
            "winner": winner,
            "speedup": speedup,
            "cache_ttl_seconds": CACHE_TTL_SECONDS,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def compare_plans_async(self) -> Dict[str, Any]:
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.compare_plans)


def get_codex_status() -> Optional[Dict[str, Any]]:
    """Return current Codex status using the default plan (C)."""
    return CodexStatusBridge().get_status()


def compare_plans() -> Dict[str, Any]:
    """Compare Plan A vs Plan B."""
    return CodexStatusBridge().compare_plans()


__all__ = [
    "CodexStatusBridge",
    "CodexStatusSourceScanner",
    "CODEX_STATUS_FILE",
    "BRIDGE_LOG_FILE",
    "CACHE_TTL_SECONDS",
    "get_codex_status",
    "compare_plans",
]
