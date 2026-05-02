# Plan Review: Fail-Safe Hermes OS State Sync

## Goal
Review and correct the proposed plan before any implementation so Hermes OS remains safe, predictable, and aligned with the post-router-retirement contract.

## Verified Current Context

Evidence checked read-only:

- PATH launcher:
  - `command -v hermes-os` → `/home/hanuman3310/.local/bin/hermes-os`
  - `readlink -f` → `/home/hanuman3310/.hermes/skills/hermes-os/bin/hermes-os`
- Global state file: `~/.hermes/state/hermes-os.json`
  - `mode: hermes_os`
  - `rtk_enabled: true`
  - no `active` field currently present
- Chat binding file: `~/.hermes/gateway_hermes_os_mode.json`
  - `7826599585: on`
- Gateway runtime:
  - bare `/hermes_os` uses `subcmd = "on"`
  - `/hermes_os` calls `['hermes-os', 'on']`
  - `_inject_hermes_os_mode_if_needed()` currently gates only on per-chat binding, not global state
- Existing tests verify:
  - bare `/hermes_os` activates chat binding
  - `/hermes_os status` does not activate binding
  - `/hermes_os off` clears the chat binding
  - persisted binding survives reload
  - normal messages remain direct and receive context injection once

## Important Correction to Earlier Plan

The earlier plan over-assumed an `active: true|false` field as an existing reliable source of truth.

Actual evidence shows `active` is absent in the current state file. Therefore the safer plan is:

- Treat `mode` as the current global source-of-truth candidate.
- Add `active` only if we intentionally migrate the state schema and update all readers/writers.
- Do not depend on `active` until migration + tests prove it exists and is maintained.

## Recommended Safe Architecture

Use one Hermes OS control layer, with two state scopes:

1. Global control state
   - File: `~/.hermes/state/hermes-os.json`
   - Safe source of truth for whether Hermes OS control layer is globally allowed.
   - Current reliable field: `mode` (`hermes_os` or `hermes_off`).

2. Per-chat context binding
   - File: `~/.hermes/gateway_hermes_os_mode.json`
   - Decides whether a specific Telegram chat is opted into Hermes OS context injection.
   - Must never override a global OFF.

Safety rule:

```python
if global_mode != "hermes_os":
    return False  # fail closed; never inject even if chat binding says on
if chat_binding != "on":
    return False
inject_context_once()
```

## Revised Behavior Contract

### `/hermes_os` or `/hermes-os` with no args in Telegram
- Must remain activation command.
- Must call `hermes-os on`.
- Must set this chat binding to `on` only if launcher succeeds.
- Should ensure global mode is `hermes_os` through the launcher result / state writer.

### `/hermes_os status`
- Must not enable context by accident.
- Should show both:
  - Global: ON/OFF from `~/.hermes/state/hermes-os.json`
  - This chat: ON/OFF from `~/.hermes/gateway_hermes_os_mode.json`
- Should clearly say if global OFF blocks chat ON.

### `/hermes_os off` in Telegram
Safer default: chat-scoped off only.

- Sets this chat binding to `off`.
- Does not necessarily shut down global Hermes OS for all chats.
- Message wording must say “disabled for this chat”.

### CLI `hermes-os off`
Safer as system-level control.

- Sets global `mode: hermes_off`.
- Should not silently delete chat bindings unless Boss explicitly chooses “emergency global off clears all chat bindings”.
- Injection gate still blocks all chats while global mode is off, so clearing bindings is optional.

## Files Likely to Change

1. `gateway/run.py`
   - Add a read-only helper for global Hermes OS mode, e.g. `_hermes_os_global_enabled()`.
   - Use it inside `_inject_hermes_os_mode_if_needed()` before checking chat binding.
   - Optionally use it in `/hermes_os status` response.

2. `hermes_cli/hermes_os_format.py`
   - Add a compact formatter for combined global + chat status.
   - Keep Telegram-safe wording and emoji.

3. `tests/gateway/test_hermes_os_session_binding.py`
   - Add tests for fail-closed behavior:
     - global `hermes_off` + chat `on` → no injection
     - missing global state → no injection or documented safe fallback
     - global `hermes_os` + chat `on` → injection allowed
     - global `hermes_os` + chat `off` → no injection
     - `/hermes_os status` reports both global and chat status without enabling

4. Possibly `~/.hermes/skills/hermes-os/bin/hermes-os` or `~/.hermes/os/hermes_os.py`
   - Only if audit proves the launcher/core fails to persist `mode` consistently.
   - Do not patch until verified.

## Tests / Validation

Preferred wrapper:

```bash
scripts/run_tests.sh tests/gateway/test_hermes_os_session_binding.py -q
```

Known caveat: if wrapper hits live venv missing `pip`, fallback may be needed and must be reported:

```bash
venv/bin/python -m pytest tests/gateway/test_hermes_os_session_binding.py -q -n 4
```

Manual evidence checks:

```bash
command -v hermes-os
readlink -f $(command -v hermes-os)
hermes-os status
hermes os status
python3 ~/.hermes/os/cli.py status
```

Runtime checks:

- Confirm gateway process/service evidence separately from pretty status output.
- Confirm `/hermes_os` root returns activation card, not status card.
- Confirm normal follow-up remains direct and does not auto-route.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Accidentally disabling other chats | Keep Telegram `/hermes_os off` chat-scoped by default |
| Global OFF + chat ON ghost context | Add global fail-closed gate before injection |
| Depending on missing `active` field | Use `mode` first; only add `active` through explicit schema migration |
| Launcher/core mismatch | Verify PATH-resolved launcher and core path before success claim |
| Router-era regression | Keep wording: context binding, not routing; direct execution remains default |

## Recommendation

Implement the minimal safe fix first:

1. Add global mode read helper in gateway.
2. Gate context injection on `global mode == hermes_os` AND chat binding `on`.
3. Add combined status wording.
4. Add regression tests.
5. Verify launcher/core/status parity.

Do not clear all chat bindings on global off in the first pass unless Boss explicitly requests emergency-stop semantics.
