---
name: codex-gpt-status-bridge
title: Codex GPT Status Bridge
description: Handle /gpts command to display Codex GPT status with real-time data from session JSONL files instead of unreliable codex status CLI call
version: 1.0.1
tags: [codex, gpt, status, bridge, cli, gateway]
---

## Problem
- `codex status` CLI command fails in non-interactive environments with "stdin is not a terminal"
- Stale cache data was being displayed as current status
- `/gpts` command needed to show real-time, accurate data

## Solution

### Plan C: Active Probe + Matching Session Scanner (current preferred default)
Boss prioritizes correct/current data over a tiny quota cost. For the default `/gpts` path, actively refresh Codex status by running a minimal probe:

```bash
codex exec --json --skip-git-repo-check --color=never Hello
```

Then extract the newly created `session_id` and read the matching fresh session JSONL `token_count` event. Label the source as `codex_exec_probe` and clearly state that it may consume a small amount of quota.

If the active probe fails, return an explicit refresh failure and debug paths/errors; do **not** silently present stale passive session data as the primary `/gpts` answer.

### Passive Session Scanner (debug/fallback only)
Read Codex session JSONL files from multiple roots, including WSL `~/.codex/sessions`, Windows-mounted `/mnt/c/Users/*/.codex/sessions`, `CODEX_HOME/sessions`, and VS Code/Cursor storage roots when available.
- Do not limit discovery to today's files; select the latest valid `token_count` event.
- Do not let a newer file without `token_count` override an older file that has valid usage data.
- Extract source metadata: `source_path`, `source_mtime`, `source_age_seconds`, `event_timestamp`, `originator`, `line_offset`, and `realtime_fingerprint`.
- Mark old/unchanged sources as stale instead of presenting stale cache/session data as realtime.
- Do not rely on `codex status`; it is not a stable non-interactive API.

### Plan B: Cache
Read from `~/.hermes/codex_ratelimit.json` only as a fallback.
- Used when realtime session data is unavailable.
- Must be labeled fresh/stale according to TTL.

### Verification Link
The `/gpts` pretty card should include the official Codex usage analytics link so Boss can manually verify displayed data:
`https://chatgpt.com/codex/cloud/settings/analytics#usage`

### Reset Time Display
Codex rate-limit reset fields (`rate_limits.primary.resets_at`, `rate_limits.secondary.resets_at`) are real epoch timestamps from Codex session `token_count` events.

For Boss-facing `/gpts` output:
- Convert epoch UTC to Bangkok time (UTC+7).
- `5h Limit` reset should remain **time-only** in 12-hour AM/PM format (e.g. `11:37 PM`).
- `7d Limit` reset should be **date + time** in 12-hour AM/PM format: `YYYY-MM-DD hh:mm AM/PM` (e.g. `2026-04-26 11:59 PM`).

Implementation note:
- Keep a helper that can optionally include date (defaulting to time-only for backward compatibility), and call it with explicit `include_date` behavior by limit type. Avoid hardcoding reset values.

### Plan C: Fallback
If active probe/session matching and acceptable cache data fail, return an error message with the checked paths instead of stale data.

## Key Files
- `gateway/codex_bridge.py` - Core bridge logic
- `gateway/codex_tracker.py` - Cache management
- `hermes_cli/commands.py` - central command registry; must contain `CommandDef("gpts", ...)`
- `cli.py` - CLI command surface; must dispatch `canonical == "gpts"` and define `HermesCLI._handle_gpts_command`
- `gateway/run.py` - gateway command surface; must dispatch `canonical == "gpts"` and define `GatewayRunner._handle_gpts_command`
- `tests/gateway/test_codex_status_regressions.py` - Regression tests
- `tests/gateway/test_codex_status_source_scanner.py` - Session source scanner tests
- `tests/gateway/test_gpts_pretty_card.py` - Pretty card output tests

## Upstream update / restore audit checklist
When `/gpts` breaks after an upstream update, do not copy the whole old `gateway/run.py`. Rebuild the command surface against the new upstream file:
1. Compare Fact Store + this skill + backup `RESTORE_GUIDE.md` before editing.
2. Verify the bridge modules exist: `gateway/codex_bridge.py`, `gateway/codex_tracker.py`.
3. Verify central command registration: `CommandDef("gpts", ...)` in `hermes_cli/commands.py`.
4. Verify CLI surface: `cli.py` dispatches `canonical == "gpts"` and has `HermesCLI._handle_gpts_command`.
5. Verify gateway surface: `gateway/run.py` dispatches `canonical == "gpts"` and has `GatewayRunner._handle_gpts_command`.
6. Add/keep a command-surface sentinel in `tests/gateway/test_gpts_pretty_card.py` that verifies:
   - `CommandDef("gpts", ...)` exists in `COMMAND_REGISTRY`
   - `resolve_command("/gpts")` resolves to `gpts`
   - `GatewayRunner._handle_gpts_command` exists
   - `HermesCLI._handle_gpts_command` exists
7. Run `python -m pytest -q tests/gateway/test_gpts_pretty_card.py tests/gateway/test_codex_status_regressions.py tests/gateway/test_codex_status_source_scanner.py` before claiming `/gpts` is restored.

Symptom mapping:
- `AttributeError: 'GatewayRunner' object has no attribute '_handle_gpts_command'` means the bridge may exist but gateway surface is missing.
- `AttributeError: 'HermesCLI' object has no attribute '_handle_gpts_command'` means CLI surface is missing.
- Passing bridge regression tests but failing pretty-card tests usually means command integration is missing, not parser logic.

## Test Results
- `pytest tests/gateway/test_gpts_pretty_card.py tests/gateway/test_codex_status_regressions.py -q` → 9 passed

### Implementation Details
1. Default `/gpts` should use active `codex exec --json --skip-git-repo-check --color=never Hello` probe, then parse the matching fresh session JSONL `token_count` event.
2. Passive session scanning remains useful for `/gpts --debug`, `/gpts --compare`, and fallback diagnostics, but stale passive data must be labeled and must not silently replace a failed active refresh.
3. Reset displays are derived from real `resets_at` epoch timestamps; format in Bangkok time with 12-hour AM/PM, using time-only for 5h and date+time for 7d limits.
4. Keep `_format_reset_time*` helpers backward-compatible: add `include_date` parameter with default behavior equivalent to current time-only output.
5. Verify both /gpts call-sites (`reset_5h`, `reset_7d`) after formatting refactors with `search_files(..., pattern="reset_5h|reset_7d" , path="gateway")` and patch only call-sites, not broad rewrites.
6. Clear stale cache when data is stale: `rm ~/.hermes/codex_ratelimit.json`.

### Practical verification notes
- When editing `/gpts` formatting, add/refresh tests in both:
  - `tests/gateway/test_gpts_pretty_card.py` (time string fixture/assertions)
  - `tests/gateway/test_codex_status_regressions.py` (stable regression)
- Run focused regression commands that match the code touched:
  - `python -m pytest -q tests/gateway/test_gpts_pretty_card.py tests/gateway/test_codex_status_regressions.py`
  - For combined `/model` parity work, run `python -m pytest -q tests/hermes_cli/test_model_picker_parity_restore.py tests/hermes_cli/test_codex_models.py`

## Usage
```bash
/gpts           # Show current status (pretty card)
/gpts --compare # Compare Plan A vs Plan B
```