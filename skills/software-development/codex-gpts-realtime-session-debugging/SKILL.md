---
name: codex-gpts-realtime-session-debugging
description: Debug and validate /gpts Codex status changes using session JSONL files, cache fallback, and pretty-card regression tests.
---

# Codex /gpts real-time session debugging

Use this skill when /gpts, Codex status bridge, or rate-limit output looks stale, impossible, or inconsistent between CLI and gateway.

## When to use
- `codex status` fails in non-interactive shells (e.g. `stdin is not a terminal`)
- /gpts shows stale, negative, or impossible percentages
- CLI and gateway outputs diverge
- Plan A / B / C behavior needs confirmation
- You need to verify pretty-card output end-to-end

## Workflow
1. **Check the live environment first**
   - Use `date` to confirm the current day/time.
   - Inspect `~/.codex/sessions` for fresh session JSONL files.
   - Prefer the newest session file for *today only* (`YYYY/MM/DD/*.jsonl`).
   - Do not treat yesterday's session as real-time if no fresh session exists today.

2. **Validate the real-time source**
   - Parse the latest `token_count` event from the newest session JSONL.
   - Extract:
     - `rate_limits.primary.used_percent` and `resets_at`
     - `rate_limits.secondary.used_percent` and `resets_at`
     - `info.total_token_usage.total_tokens`
     - `info.model_context_window`
   - Clamp impossible values:
     - context used must not exceed context window
     - percentages must stay within `0..100`

3. **Map plans clearly**
   - Plan A: session JSONL real-time source
   - Plan B: cached-file source
   - Plan C: cache-first with refresh from session files and stale fallback
   - If live CLI calls are impossible, do not force `codex status`; use session files instead.

4. **Test the bridge narrowly first**
   - Run targeted regression tests for the bridge logic.
   - Confirm `compare_plans()` returns structured keys:
     - `plan_a`, `plan_b`, `winner`, `speedup`, `generated_at`, `cache_ttl_seconds`

5. **Test output formatting end-to-end**
   - Verify both CLI and gateway render the pretty card.
   - Check normal mode and `--compare` mode.
   - Confirm the output text that users actually see, not only internal dicts.

6. **Treat stale cache as a bug, not a success**
   - If the cache contains old values, confirm whether the session source is fresher.
   - If the newest session file is from a prior day, report that clearly instead of inventing current data.
   - When no session exists for today, returning `None`/"no Codex Session" is better than reusing stale cache data.

## Common pitfalls
- `codex status` may work interactively but fail in non-interactive automation.
- Old cache files can look plausible while still being stale.
- Session date may not match the current date; verify before claiming real-time freshness.
- Pretty-card tests can fail because of rich markup differences vs plain text output.

## Verification checklist
- `codex status` failure path is understood and handled
- latest session JSONL was inspected
- impossible values are clamped or rejected
- CLI and gateway outputs match expectations
- regression tests pass for both normal and compare modes
- when there is no fresh session for today, the bridge returns `None` rather than stale cache data

## Suggested test commands
- `pytest tests/gateway/test_codex_status_regressions.py -q`
- `pytest tests/gateway/test_gpts_pretty_card.py -q`
- Combine them when validating a full /gpts change
