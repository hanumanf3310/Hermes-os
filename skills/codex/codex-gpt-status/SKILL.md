---
name: codex-gpt-status
description: Query Codex GPT status including token usage and rate limits from cli
service: codex
intent_categories: ["codex", "cli", "status", "monitoring"]
triggers: ["/gpts", "codex status", "gpt status", "token usage", "rate limit"]
---

# Codex GPT Status (/gpts)

Query Codex CLI status including token usage, context window, and rate limits.

## Usage

| Command | Description |
|---------|-------------|
| `/gpts` | Show status using cache if fresh (<5 min) |
| `/gpts --plan A` | Force real-time session-file read (latest `token_count` event) |
| `/gpts --plan B` | Force cache read |
| `/gpts --compare` | Compare Plan A vs Plan B latency |
| `/gpts --debug` | Show debug info (source, latency_ms) |

## How It Works

```
/gpts
  ↓
Check cache (~/.hermes/codex_ratelimit.json)
  ↓
├─ Cache fresh (<5 min) → Return immediately (~0.05ms)
├─ Cache stale (≥5 min) → Read latest Codex session JSONL → Update cache → Return
├─ Session read fails → Fallback to stale cache or None
└─ No cache → Read Linux sessions → Validate → Use
```

## Important reality check

- The shipped Codex CLI in this environment does **not** expose a non-interactive `codex status` subcommand.
- Real-time / Plan A should read the latest session JSONL from `~/.codex/sessions/**/**/*.jsonl` and extract the most recent `event_msg` with `payload.type == "token_count"`.
- If you need machine-readable execution output, `codex exec --json` is available; it is **not** a status API.
- The status bridge should validate/clamp impossible values before displaying them.
- When the live path silently falls back, verify the bridge against a targeted regression test that proves Plan A reads session JSONL and that compare mode returns the structured `{plan_a, plan_b, winner, speedup}` shape.

## Files

| File | Purpose |
|------|---------|
| `~/.hermes/codex_ratelimit.json` | Cache file (5 min TTL) |
| `~/.hermes/codex_bridge.log` | Debug log |
| `~/.codex/sessions/*/*/*/*.jsonl` | Linux session data (preferred source for live status) |
| `/mnt/c/Users/User/.codex/sessions/*/*/*/*.jsonl` | Windows session data (fallback) |

## Troubleshooting

### Context shows impossible percentages or token counts
**Cause:** Session data may be stale or malformed.
**Fix:** Validate/clamp values; prefer the latest `token_count` event from Linux sessions.

### Real-time Plan A does not work with `codex status`
**Cause:** `codex status` is not a supported non-interactive subcommand in this CLI build.
**Fix:** Use session JSONL parsing instead of calling `codex status`.

### Data doesn't match Codex TUI
**Cause:** WSL and Windows Codex use separate session directories.
**Check:** Compare `~/.codex/sessions/` vs `C:\Users\User\.codex\sessions\`
**Fix:** Read both, preferring Linux (WSL) sessions.

### Stale cache
**Fix:**
```bash
rm ~/.hermes/codex_ratelimit.json
/gpts
```

### 7d reset shows only time, not date
**Cause:** Fresh cache or older formatter may contain `reset_7d` as time-only (for example `02:31 AM`) even though the weekly reset needs a date. Plan B is cache-only and can preserve the old time-only value.

**Fix / verification:** Force a live session read or cache refresh, then inspect `reset_7d`:
```bash
cd ~/.hermes/hermes-agent
python3 - <<'PY'
from gateway.codex_bridge import CodexStatusBridge
for plan in ['A','C']:
    d = CodexStatusBridge(plan=plan).get_status()
    print(plan, d.get('source'), d.get('reset_7d'), d.get('used_7d_pct'))
PY
```
Expected weekly format includes the date, e.g. `YYYY-MM-DD 02:31 AM`. If Plan C uses `codex_exec_probe`, tell Boss it may consume a small amount of quota. The 5h reset may remain time-only because it resets within the same day.

## Implementation

Source: `~/.hermes/hermes-agent/gateway/codex_bridge.py`

Key class: `CodexStatusBridge`
- Plan A: real-time session-file fetch
- Plan B: cached file only
- Plan C: cache-first with refresh-from-session-files and stale fallback
- Validates/clamps token counts and percentage fields
- Caches results for 5 minutes

## Testing

```python
from gateway.codex_bridge import CodexStatusBridge, compare_plans

bridge = CodexStatusBridge(plan="A")
data = bridge.get_status()

assert data is not None
assert 0 <= data['context_left_pct'] <= 100
print(f"Context: {data['context_left_pct']}%")
print(f"5h limit: {data['used_5h_pct']}% used")
print(f"Source: {data.get('source')}")

comparison = compare_plans()
assert set(comparison) >= {"plan_a", "plan_b", "winner", "speedup"}
```
