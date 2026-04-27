---
name: codex-status-bridge-realtime
description: Implement /gpts-style Codex status by reading the latest Codex session JSONL token_count events when non-interactive status commands are unavailable.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [codex, status, realtime, session-jsonl, bridge, regression-tests]
    related_skills: [systematic-debugging, test-driven-development, subagent-driven-development]
---

# Codex Status Bridge (Realtime)

Use this skill when a project needs a live Codex status display but the Codex CLI build does **not** expose a reliable non-interactive `codex status` command.

## Key Lesson
In this environment, `codex status` was not a valid non-interactive command. The working real-time source of truth was the latest Codex session JSONL log under `~/.codex/sessions`, specifically the newest `event_msg` whose payload type is `token_count`.

## Recommended Approach
1. **Confirm the CLI contract first**
   - Run `codex --help`.
   - Verify whether `codex status` exists.
   - If it requires a TTY or does not exist, do not build Plan A around it.

2. **Use session JSONL as the realtime source**
   - Search the latest `~/.codex/sessions/YYYY/MM/DD/*.jsonl` files.
   - Scan from newest to oldest lines.
   - Find the latest `event_msg` where `payload.type == "token_count"`.
   - Extract:
     - `rate_limits.primary.used_percent`
     - `rate_limits.primary.resets_at`
     - `rate_limits.secondary.used_percent`
     - `rate_limits.secondary.resets_at`
     - `info.total_token_usage.total_tokens`
     - `info.model_context_window`
     - `rate_limits.plan_type`

3. **Clamp and validate output**
   - Clamp percentages to `0..100`.
   - Clamp `context_used` to `0..context_window`.
   - Recompute derived percentages from the clamped values.
   - Never trust cache or session data blindly.

4. **Keep plans separate**
   - Plan A: realtime session parsing only.
   - Plan B: cache-only.
   - Plan C: cache-first, refresh from session JSONL, stale fallback if needed.

5. **Make compare mode structured**
   - Return a dict with `plan_a`, `plan_b`, `winner`, `speedup`, and timestamps.
   - Ensure callers like CLI/gateway can render it without special cases.

6. **Test the real behavior**
   - Add tests that prove:
     - Plan A ignores stale cache.
     - Plan A uses the session-file path.
     - Plan C refreshes from session files when cache is stale.
     - `compare_plans()` returns a structured dict.
   - Mock the session parser, not the whole world.
   - When the implementation resolves session files via `DEFAULT_CODEX_SESSIONS_DIR` directly, patch that constant in tests instead of `get_today_session_dir()`.
   - Add a regression test that simulates a fresh `codex_exec` probe session and a newer real session; Plan A should prefer the real session, not the probe.
   - For `--debug`, verify the rendered output includes the session file path, file modified time, event timestamp, and originator.

## Common Pitfalls
- Building Plan A around a `codex status` command that does not exist.
- Assuming `--format json` is available for a status subcommand.
- Falling back to session files only as a last resort instead of making them the primary realtime source.
- Forgetting to validate impossible percentages.
- If `HERMES_RTK_WRAP` is enabled in the environment, treat RTK as a terminal wrapper concern, not as part of the hermes-os mode semantics.
- For `/gpts`, verify both the CLI and Gateway renderers, not just the bridge helper.
- Treat pretty-card output as a presentation-layer test: assert the rendered headings/labels, not only the underlying dict fields.
- A non-interactive `codex status` attempt may fail with `Error: stdin is not a terminal`; when that happens, switch Plan A to session JSONL parsing instead of trying to force TTY behavior.
- `compare_plans()` should remain a structured dict with `plan_a`, `plan_b`, `winner`, `speedup`, `generated_at`, and `cache_ttl_seconds` so CLI/Gateway rendering stays simple.
- `get_realtime_codex_status()` reads `DEFAULT_CODEX_SESSIONS_DIR` directly; isolated tests should patch `DEFAULT_CODEX_SESSIONS_DIR`, not `get_today_session_dir()`.
- `get_codex_status_via_exec()` should use `codex exec` as a probe, parse `thread_id` from stdout, then read the matching JSONL session file for that probe session (not an unrelated newest file).
- If freshness looks wrong, check whether the implementation is accidentally selecting a different session by mtime instead of the probe session by `thread_id`.
- `--debug` output is useful for confirming which JSONL file was read, the originator (for example `codex_exec`), file modification time, event timestamp, source age, and token-count line offset.
- When unit-testing `get_realtime_codex_status()`, patch `DEFAULT_CODEX_SESSIONS_DIR` (not `get_today_session_dir`) because the implementation resolves the latest file via the module-level directory constant directly.
- If the session schema varies, accept both `payload.info.total_token_usage.total_tokens` and `payload.total_token_usage.total_tokens` so tests and live data do not regress on a single shape.
- For `/gpts`, use the live probe session path and surface an explicit failure instead of silently falling back to stale cache/session data; stale output is worse than an error for a status command.
- In WSL + VS Code/Codex setups, do not scan only `~/.codex/sessions` or only today’s path. Add multi-root discovery for `CODEX_HOME/sessions`, WSL `~/.codex/sessions`, Windows `/mnt/c/Users/*/.codex/sessions`, and filtered VS Code/Cursor globalStorage roots.
- A newer JSONL file without a `token_count` event must not hide an older file with a valid `token_count`; choose the latest valid token_count candidate, not simply the newest file.
- Realtime must advance after confirmed Codex/GPT activity. Track a fingerprint such as `{source_path, source_mtime, event_timestamp, context_used, line_offset}`; if `/gpts --debug` returns the exact same fingerprint after expected new activity, warn that the realtime source did not advance and mark the result stale/wrong.
- Do not run `codex exec` automatically for ordinary `/gpts`; it can create a session and consume rate-limit. Keep probe mode explicit (for example `/gpts --probe`) and only enable it when the operator approves.

## Realtime Advancement Invariant

When `/gpts` or an equivalent status command claims to be realtime, it must prove the source advanced after new Codex/GPT activity. Repeated identical values are suspicious if the user has interacted with the active model/session between checks.

Track a compact realtime fingerprint from the selected `token_count` event:

```python
fingerprint = {
    "source_path": source_path,
    "source_mtime": source_mtime,
    "event_timestamp": event_timestamp,
    "context_used": context_used,
    "line_offset": line_offset,
}
```

After a newer `token_count` event is appended, at least one of these should change:
- `context_used`
- `event_timestamp`
- `source_mtime`
- `source_path` (if a new session file becomes active)
- token-count `line_offset` / event sequence metadata

If all remain identical after confirmed new activity, flag the result as stale/wrong rather than presenting it as realtime. In debug output, include a warning such as:

```text
⚠️ Realtime source did not advance — data may be stale/wrong
```

Regression tests should cover both paths:
1. Append a newer `token_count` with higher `context_used`; assert context/fingerprint changes and no freshness warning appears.
2. Simulate expected new activity without a newer event; assert `freshness_warning` is set.

## Verification Checklist
- [ ] `codex --help` checked first
- [ ] `codex status` contract verified or rejected
- [ ] Latest session JSONL token_count parsing implemented
- [ ] Percentages and token counts clamped
- [ ] Plan A / B / C behavior separated
- [ ] `compare_plans()` returns structured data
- [ ] Realtime advancement invariant tested (new activity changes context/fingerprint)
- [ ] Unchanged fingerprint after expected activity is flagged stale/wrong
- [ ] Targeted regression tests pass

## Example Usage
- `/gpts` in CLI or gateway should use the realtime bridge skill when direct status is unavailable.
- If the live command fails, prefer session JSONL parsing before any stale-cache fallback.
