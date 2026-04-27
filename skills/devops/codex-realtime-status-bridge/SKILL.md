---
name: codex-realtime-status-bridge
description: Recover real-time Codex rate-limit/status data by parsing session JSONL logs instead of calling a missing non-interactive `codex status` command.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [codex, realtime, status, jsonl, session-logs, bridge]
    related_skills: [systematic-debugging, test-driven-development, subagent-driven-development]
---

# Codex Realtime Status Bridge

Use this skill when a project needs a real-time Codex status or rate-limit view but the CLI does not expose a usable headless `codex status` command.

## Key Finding
In this environment, `codex status` is **not** a reliable non-interactive API. Attempts may fail with messages like:
- `Error: stdin is not a terminal`
- `unexpected argument '--format' found`

If you need live status data, use the **Codex session JSONL files** instead.

## Source of Truth
For passive/debug parsing, scan session JSONL roots across WSL and Windows, not only today's WSL path:
- `~/.codex/sessions/**/*.jsonl`
- `/mnt/c/Users/*/.codex/sessions/**/*.jsonl`
- `$CODEX_HOME/sessions/**/*.jsonl`
- VS Code/Cursor globalStorage roots when investigating extension-specific state

Look backward for the latest event with:
- `type == "event_msg"`
- `payload.type == "token_count"`

That payload usually contains:
- `rate_limits.primary.used_percent`
- `rate_limits.primary.resets_at`
- `rate_limits.secondary.used_percent`
- `rate_limits.secondary.resets_at`
- `info.total_token_usage.total_tokens`
- `info.model_context_window`
- `rate_limits.plan_type`

Also parse session metadata when present:
- `session_meta.payload.id` as `session_id`
- `session_meta.payload.originator` / `source`

## Implementation Pattern
Prefer a small bridge with these steps:
1. Find the latest session JSONL file.
2. Read lines from bottom to top.
3. Find the latest `token_count` payload.
4. Transform it into a normalized dict.
5. Clamp impossible values before returning them.
6. Attach `source: session_files` or similar to make the origin obvious.

## Recommended Fallback Order
For `/gpts` in this Hermes environment, Boss prefers correctness over strict read-only behavior:
1. **Active Codex exec probe** for the default `/gpts` path: run a minimal `codex exec --json --skip-git-repo-check --color=never 'Hello'` probe.
2. Extract `session_id` from stdout/stderr, then read the new matching session JSONL token_count event.
3. Label the source as `codex_exec_probe` and make it clear that the command may consume a small amount of quota.
4. If the probe fails, return an explicit refresh failure; do not silently present stale passive session data as the primary `/gpts` answer.
5. Passive session JSONL parsing remains useful for debug/compare flows and tests.

## Non-interactive Codex Commands
If you need machine-readable Codex execution, prefer:
- `codex exec --json --skip-git-repo-check --color=never 'Hello'` for active `/gpts` refresh probes
- or the Codex app-server protocol

Do **not** rely on `codex status` unless the specific environment has verified support.

## Testing Strategy
Use strict TDD for behavior changes. Add targeted tests for:
- default `/gpts` Plan C calls `codex exec --json --skip-git-repo-check --color=never Hello`
- extracting `session_id` from JSONL/stdout/stderr formats
- reading only the matching freshly-created probe session token_count event
- probe failure returns an explicit refresh failure and does not silently show stale passive data
- parsing WSL and Windows-mounted session roots
- selecting latest valid token_count rather than newest file without token_count
- realtime fingerprint/metadata advancement (`source_path`, `source_mtime`, `event_timestamp`, `context_used`, `line_offset`)
- clamping impossible percentages
- structured compare/status output
- stale cache/session labeling in debug flows

## Pitfalls
- Treating `codex status` as a stable API when it is not
- Optimizing for zero token usage when the user needs correct actionable data; a tiny probe cost is better than stale/wrong status causing bad decisions
- Letting passive local session data become the primary answer after it is proven stale compared with Codex Cloud Analytics
- Parsing the wrong event type from session logs
- Returning stale cached data without labeling it
- Forgetting to clamp impossible percentages
- Assuming TTY-based commands can run in a non-interactive subprocess
- Forgetting to tell the user that active probe mode may consume a small amount of quota

## Example Outcome
A working `/gpts` bridge should actively refresh by creating a minimal Codex exec session, then show rate limits from the new matching JSONL token_count event. In the verified workflow, `/gpts` returned `source: codex_exec_probe`, a fresh session id/path, and 5h/7d percentages close to Codex Cloud Analytics; stale passive data was not used as the primary answer.
