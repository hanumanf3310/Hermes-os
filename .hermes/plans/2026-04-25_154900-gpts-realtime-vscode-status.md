# /gpts Realtime Codex Status Bridge Plan

> **For Hermes OS:** Plan only. Do not implement until Boss explicitly approves.

**Goal:** Make `/gpts` show realtime Codex status/rate-limit data comparable to what Boss sees in VS Code `/status`, instead of returning `❌ No Codex Session data found` when the expected session JSONL path is missing or stale.

**Scope:** Only `/gpts` / Codex status bridge behavior. Do not modify unrelated `/model` work, do not push, and do not touch upstream remotes.

**Architecture:** Build a multi-source realtime status resolver with explicit source precedence and debug metadata. Prefer a live Codex probe/session path when possible, then VS Code / Codex session artifacts, then validated cache. Never silently show stale data as realtime.

---

## 1. Current Problem

Boss sees:

```text
❌ No Codex Session data found

Please check:
• Have you used Codex CLI today?
• Files at C:\Users\User\.codex\sessions

Use /gpts --compare to test both plans
```

But Boss wants `/gpts` to behave like VS Code `/status`, showing realtime data such as:
- current model/session status
- context usage
- rate limits
- reset times
- plan type
- source/debug information

Current bridge likely fails because it searches only limited session JSONL locations/dates and does not reliably read the same active source surface that VS Code/Codex is using.

---

## 2. Requirements

### Must-have
1. `/gpts` should return realtime status if any active Codex/VS Code status source exists.
2. `/gpts --debug` must show exact source used:
   - source kind
   - session file path or probe id
   - file mtime
   - event timestamp
   - originator if available
3. `/gpts --compare` must compare structured Plan A / Plan B / Plan C results.
4. Stale cache must be labeled stale, never presented as realtime.
5. If no data exists, error should say exactly which paths were checked.
6. Must work in WSL + Windows mixed environment.
7. **Realtime advancement invariant:** after confirmed new Codex/GPT activity creates a newer `token_count` event, `/gpts --debug` must not return the exact same realtime metadata/context snapshot as before. At minimum one of these must change:
   - `context_used`
   - `event_timestamp`
   - `source_mtime`
   - `source_path` when a new session file becomes active
   - token-count `line_offset` / event sequence metadata

If all of these remain identical after confirmed new activity, the result must be treated as stale/wrong, not realtime.

### Should-have
1. Include VS Code / Codex session locations beyond today's Linux path.
2. Prefer latest valid `token_count` event, not merely newest file.
3. Avoid synthetic Codex probe sessions accidentally hiding real VS Code sessions unless the probe is explicitly requested.
4. Support `codex exec` probe mode as fallback when no session exists.

---

## 3. Source Strategy

## Plan A — Realtime resolver
Use a chain of realtime-capable sources:

1. **Active/newest Codex session JSONL across multiple roots**
   - Linux WSL:
     - `~/.codex/sessions/**/**/*.jsonl`
   - Windows host:
     - `/mnt/c/Users/*/.codex/sessions/**/**/*.jsonl`
   - configured env roots if present:
     - `CODEX_HOME/sessions/**/**/*.jsonl`

2. **VS Code Codex extension artifacts**
   - Search candidate locations under:
     - `/mnt/c/Users/*/AppData/Roaming/Code/User/globalStorage/**`
     - `/mnt/c/Users/*/AppData/Roaming/Cursor/User/globalStorage/**`
     - `/mnt/c/Users/*/.codex/**`
   - Only read small JSON/JSONL files matching Codex-like patterns.
   - Do not crawl huge directories without filters.

3. **Optional live probe fallback**
   - Run a lightweight `codex exec` probe only when explicitly enabled by `/gpts --probe` or if Boss approves enabling probe fallback.
   - Parse returned thread/session id.
   - Read that exact session JSONL, not just newest file.

## Plan B — cache only
Use `~/.hermes/codex_ratelimit.json` only.

## Plan C — smart fallback
1. Try Plan A.
2. If Plan A works, update cache.
3. If Plan A fails, use fresh cache if within TTL.
4. If cache stale, return stale-labeled result or explicit no-data error depending command mode.

### Realtime freshness rule
Plan C must store and compare a small realtime fingerprint when possible:

```python
fingerprint = {
    "source_path": source_path,
    "source_mtime": source_mtime,
    "event_timestamp": event_timestamp,
    "context_used": context_used,
    "line_offset": line_offset,
}
```

If Boss asks for realtime status after new activity and the fingerprint is unchanged, render a warning such as:

```text
⚠️ Realtime source did not advance — data may be stale/wrong
```

This warning should appear in `/gpts --debug`; normal `/gpts` may show a compact stale-source warning.

---

## 4. Parser Rules

A valid realtime record is latest JSONL event where:

```python
event.get("type") == "event_msg"
payload = event.get("payload", {})
payload.get("type") == "token_count"
```

Extract:
- `rate_limits.primary.used_percent`
- `rate_limits.primary.resets_at`
- `rate_limits.secondary.used_percent`
- `rate_limits.secondary.resets_at`
- `rate_limits.plan_type`
- `info.total_token_usage.total_tokens`
- `info.model_context_window`

Also support schema variants:
- `payload.total_token_usage.total_tokens`
- missing `rate_limits` should not crash
- timestamps as epoch, ISO, or absent

Normalize output keys:
- `context_used`
- `context_window`
- `context_left_pct`
- `used_5h_pct`
- `left_5h_pct`
- `reset_5h`
- `used_7d_pct`
- `left_7d_pct`
- `reset_7d`
- `plan_type`
- `source`
- `source_path`
- `source_mtime`
- `event_timestamp`
- `originator`
- `is_realtime`
- `is_stale`
- `line_offset`
- `realtime_fingerprint`
- `freshness_warning`

Clamp:
- percentages `0..100`
- context used `0..context_window`
- context window `>0`

---

## 5. Proposed File Changes

### Primary files
- `gateway/codex_bridge.py`
  - Add `CodexStatusSourceScanner`
  - Add multi-root session discovery
  - Add debug metadata fields
  - Add optional probe strategy interface

- `gateway/codex_tracker.py`
  - Generalize path scanning if existing tracker is too limited
  - Support Windows glob roots
  - Return parse candidates with metadata, not only payload data

- `gateway/run.py`
  - Improve `/gpts` no-data message with checked paths
  - Add optional flags:
    - `/gpts --debug`
    - `/gpts --compare`
    - optional `/gpts --probe` only if approved

- `cli.py`
  - Keep CLI `/gpts` output aligned with gateway rendering

### Tests
- `tests/gateway/test_codex_status_regressions.py`
- `tests/gateway/test_gpts_pretty_card.py`
- New if needed: `tests/gateway/test_codex_status_source_scanner.py`

---

## 6. TDD Plan

### Task 1 — Multi-root scanner tests
**Test:** scanner checks Linux + Windows session roots and chooses latest valid token_count event.

Expected failing test before implementation:
```bash
pytest tests/gateway/test_codex_status_source_scanner.py::test_scanner_reads_windows_codex_sessions -q
```

### Task 2 — Latest event, not newest file only
**Test:** a newer file without `token_count` must not beat an older file with valid `token_count`.

### Task 3 — Debug metadata
**Test:** `/gpts --debug` includes path, mtime, event timestamp, and originator.

### Task 4 — No-data message lists checked paths
**Test:** when no valid source exists, output contains all roots checked and suggests using `/gpts --probe` or opening Codex/VS Code.

### Task 5 — Plan C stale cache labeling
**Test:** stale cache returns `is_stale=True` and renderer labels it clearly.

### Task 6 — Optional probe mode
**Test:** `codex exec` probe returns a thread/session id and parser reads that exact session file.

Important: Do not enable probe by default until Boss approves, because it creates a Codex session and may consume rate-limit.

### Task 7 — Context changes after new token_count activity
**Test:** create a fake session JSONL with a first `token_count`, call the bridge, append a second newer `token_count` with higher `context_used`, call bridge again, and assert:

- `context_used` changes
- `event_timestamp` or `line_offset` changes
- `realtime_fingerprint` changes
- no stale/freshness warning appears

Expected failing test before implementation:
```bash
pytest tests/gateway/test_codex_status_source_scanner.py::test_realtime_context_advances_after_new_token_count_event -q
```

### Task 8 — Unchanged realtime fingerprint is flagged
**Test:** call the bridge twice without adding a new `token_count` event while simulating that new activity was expected. The second result must be flagged as not advanced.

Expected assertions:
```python
assert result["freshness_warning"]
assert "did not advance" in result["freshness_warning"].lower()
```

Expected failing test before implementation:
```bash
pytest tests/gateway/test_codex_status_source_scanner.py::test_unchanged_realtime_fingerprint_warns_when_activity_expected -q
```

---

## 7. Verification Commands

Targeted:
```bash
cd /home/hanuman3310/.hermes/hermes-agent
source venv/bin/activate
pytest tests/gateway/test_codex_status_regressions.py tests/gateway/test_gpts_pretty_card.py -q
```

New scanner tests:
```bash
pytest tests/gateway/test_codex_status_source_scanner.py -q
```

Manual smoke:
```bash
/gpts --debug
/gpts --compare
```

If probe mode approved:
```bash
/gpts --probe --debug
```

---

## 8. Rollout / Safety

- No push without Boss approval.
- No automatic `codex exec` probe unless explicitly approved or behind explicit flag.
- Keep old cache fallback available but visibly labeled.
- Commit separately from `/model` commits.
- Suggested commit message:
  - `fix(gpts): discover realtime codex status across vscode/session roots`

---

## 9. Acceptance Criteria

Done only when:
1. `/gpts --debug` shows a realtime source if VS Code/Codex has status data.
2. If source missing, output lists checked paths instead of vague `C:\Users\User\.codex\sessions` only.
3. Tests prove Linux + Windows session discovery.
4. Tests prove stale cache is not mislabeled realtime.
5. Boss confirms the displayed data matches VS Code `/status` closely enough.
6. Tests prove realtime advancement: after a newer `token_count` event, `/gpts` returns changed context/fingerprint metadata.
7. Tests prove unchanged context/fingerprint after expected new activity is flagged as stale/wrong.
