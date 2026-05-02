# Hermes OS Global Mode + Chat Binding Fix Plan

## Goal
แก้ปัญหา Hermes OS state ไม่ชัดเจน/ไม่ sync ระหว่าง global state และ Telegram chat binding โดยให้ปลอดภัยที่สุดกับ Hermes OS contract:

- Hermes OS เป็น control/nervous layer เดียว
- Direct execution remains default
- Chat binding = context/policy binding เท่านั้น ไม่ใช่ router
- Fleet/thClaws/OMX ใช้เฉพาะ explicit command หรือ policy-approved path
- Fail closed เมื่อ global state ไม่อนุญาต

## Current Verified Evidence

จากการตรวจ read-only ก่อนหน้า:

- PATH-resolved launcher:
  - `command -v hermes-os` → `/home/hanuman3310/.local/bin/hermes-os`
  - real path → `/home/hanuman3310/.hermes/skills/hermes-os/bin/hermes-os`
- Global state:
  - File: `~/.hermes/state/hermes-os.json`
  - Current fields: `mode`, `timestamp`, `rtk_enabled`
  - Current reliable source: `mode`
  - `active` field is currently absent, so do not depend on it yet
- Telegram chat binding:
  - File: `~/.hermes/gateway_hermes_os_mode.json`
  - Current chat binding example: `{ "7826599585": "on" }`
- Gateway runtime:
  - `/hermes_os` bare command already defaults to `on`
  - handler calls `['hermes-os', 'on']`
  - current injection checks only chat binding, not global mode

## Safe Target Contract

Hermes OS has one control layer, but two state scopes:

1. Global mode
   - Source: `~/.hermes/state/hermes-os.json`
   - Field: `mode`
   - Allowed ON value: `hermes_os`
   - OFF value: `hermes_off`

2. Per-chat binding
   - Source: `~/.hermes/gateway_hermes_os_mode.json`
   - Value per chat: `on` or `off`

Fail-safe rule:

```python
if global_mode != "hermes_os":
    return False  # global OFF blocks every chat, even if chat binding says on
if chat_binding != "on":
    return False
inject_context_once()
```

## Recommended Implementation Scope: Minimal Safe Fix

Do not redesign the whole Hermes OS state schema in the first pass.
Do not require the missing `active` field yet.
Do not clear all chat bindings by default.

Implement only:

1. Read global mode safely from `~/.hermes/state/hermes-os.json`.
2. Gate Telegram context injection on both global mode and chat binding.
3. Improve status message to show both global mode and this chat binding.
4. Add regression tests for fail-closed behavior.

## Detailed Steps

### Phase 1 — Add global mode helper in Gateway

File:

- `/home/hanuman3310/.hermes/hermes-agent/gateway/run.py`
- Mirror to dev checkout if needed: `/home/hanuman3310/hermes-agent/gateway/run.py`

Add helper methods near existing Hermes OS mode helpers:

```python
def _load_hermes_os_global_mode(self) -> str:
    """Return global Hermes OS mode. Fail closed on missing/invalid state."""
    try:
        path = Path.home() / ".hermes" / "state" / "hermes-os.json"
        data = json.loads(path.read_text())
        return str(data.get("mode") or "hermes_off")
    except Exception:
        return "hermes_off"


def _hermes_os_global_enabled(self) -> bool:
    return self._load_hermes_os_global_mode() == "hermes_os"
```

Important:

- Fail closed on missing file, malformed JSON, missing mode.
- Do not use `active` yet.

### Phase 2 — Gate context injection

Modify `_inject_hermes_os_mode_if_needed()`:

Current logic:

```python
if not chat_id or self._hermes_os_mode_for_chat(chat_id) != "on":
    return False
```

Target logic:

```python
if not chat_id:
    return False
if not self._hermes_os_global_enabled():
    return False
if self._hermes_os_mode_for_chat(chat_id) != "on":
    return False
```

Effect:

- Global OFF + chat ON no longer injects Hermes OS context.
- Global ON + chat ON still injects.
- Global ON + chat OFF remains direct without injection.

### Phase 3 — Improve `/hermes_os status` wording

Files:

- `gateway/run.py`
- `hermes_cli/hermes_os_format.py`

Add a combined status formatter, e.g.:

```text
🛰️ Hermes OS Context Binding
━━━━━━━━━━━━━━━━━━━━━
🌐 Global mode: ON/OFF
💬 This chat: ON/OFF
🛡️ Effective context: ACTIVE/BLOCKED
⚡ Execution: Direct path remains default
🚀 Fleet: explicit commands only
```

Rules:

- `/hermes_os status` must not activate binding.
- If global OFF but chat ON, show:
  - `Effective context: BLOCKED by global mode`
  - This makes ghost state visible without silently changing files.

### Phase 4 — Regression tests

File:

- `tests/gateway/test_hermes_os_session_binding.py`

Add tests:

1. `test_global_off_blocks_chat_on_injection`
   - state file mode = `hermes_off`
   - chat binding = `on`
   - expected: `_inject_hermes_os_mode_if_needed()` returns `False`

2. `test_missing_global_state_fails_closed`
   - no state file
   - chat binding = `on`
   - expected: no injection

3. `test_global_on_and_chat_on_injects`
   - state mode = `hermes_os`
   - chat binding = `on`
   - expected: injection happens once

4. `test_global_on_chat_off_does_not_inject`
   - state mode = `hermes_os`
   - chat binding = `off`
   - expected: no injection

5. `test_status_reports_global_and_chat_without_enabling`
   - call `/hermes_os status`
   - verify no chat binding is created if not already present
   - verify response mentions global and chat state

### Phase 5 — Verification commands

Use test wrapper first:

```bash
scripts/run_tests.sh tests/gateway/test_hermes_os_session_binding.py -q
```

Known caveat: if wrapper fails because live venv lacks pip, report caveat and use fallback:

```bash
venv/bin/python -m pytest tests/gateway/test_hermes_os_session_binding.py -q -n 4
```

Smoke checks:

```bash
command -v hermes-os
readlink -f $(command -v hermes-os)
hermes-os status
hermes os status
python3 ~/.hermes/os/cli.py status
```

Runtime evidence after code change:

- `py_compile` for modified files
- Targeted pytest result
- `hermes gateway restart`
- `hermes gateway status` or process evidence
- Telegram smoke:
  1. `/hermes_os` returns activation card
  2. normal follow-up remains direct but receives context if global ON + chat ON
  3. set global OFF and confirm chat ON no longer injects

## Non-Goals for First Pass

Do not do these yet:

- Do not migrate schema to require `active`.
- Do not clear all chat bindings on global OFF.
- Do not make normal messages auto-route to Fleet/thClaws/OMX.
- Do not change direct execution default.
- Do not reintroduce router-era behavior.

## Risks

| Risk | Mitigation |
|---|---|
| Missing global state blocks injection unexpectedly | This is intentional fail-closed; status should explain it |
| Existing chat binding appears on but no context injects | Status must show `blocked by global mode` |
| Multi-chat disruption | Keep `/hermes_os off` chat-scoped; do not clear all chats |
| Launcher/core mismatch | Always verify PATH-resolved launcher and core path |
| Test wrapper broken | Report wrapper caveat and use documented fallback |

## Final Recommendation

Proceed with the minimal safe fix:

1. Add global `mode` fail-closed helper.
2. Gate injection by `global mode == hermes_os` AND `chat binding == on`.
3. Add combined status output.
4. Add regression tests.
5. Verify and restart gateway only after tests pass.

This keeps Hermes OS safe and predictable without over-changing architecture.
