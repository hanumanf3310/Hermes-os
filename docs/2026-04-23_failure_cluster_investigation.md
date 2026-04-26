# Failure Cluster Investigation Report

**Date:** 2026-04-23

## Goal
Investigate the two failure clusters seen in the latest full-suite run:
1. Environment / subprocess cleanup warnings from `tools/environments/base.py`
2. Discord gateway test failures caused by shared mock contamination

## 1) Environment / subprocess cleanup cluster

### Root cause
`BaseEnvironment._wait_for_process()` assumed `proc.stdout` always exposed a real `fileno()`.

That assumption is false in several tests that use lightweight doubles:
- `tests/tools/test_base_environment.py` uses `iter([])`
- `tests/tools/test_ssh_environment.py` uses iterator-based stdout/stderr doubles
- `tests/tools/test_local_env_blocklist.py` uses a mock stdout whose `fileno()` does not return an integer

### Fix
Updated `tools/environments/base.py` so `_drain()`:
- checks whether `stdout.fileno()` exists and returns a real integer
- falls back to iterable consumption when the stdout object is a test double / non-pipe stream
- skips `select()` / `os.read()` when there is no real file descriptor

### Verification
Targeted tests passed:
- `tests/tools/test_base_environment.py::TestInitSessionFailure::test_login_flag_when_snapshot_not_ready`
- `tests/tools/test_ssh_environment.py`
- `tests/tools/test_local_env_blocklist.py`

## 2) Discord gateway cluster

### Root cause
The Discord tests were relying on a `discord.AllowedMentions` object, but in combined runs the imported `discord` module was often a `MagicMock`-based stub from other test setup paths. In that state, `discord.AllowedMentions(...)` returned a mock object instead of a deterministic boolean-bearing value object, which caused assertions like `am.everyone is False` to fail.

The failure only showed up in combined runs because test collection/import order changed which mock module ended up in place.

### Fix
Updated `gateway/platforms/discord.py`:
- `_build_allowed_mentions()` now prefers the real `discord.AllowedMentions` class when present
- otherwise it falls back to a small local value object with stable boolean attributes

This makes the production code resilient to test stubs and avoids cross-test contamination.

### Verification
Targeted Discord tests passed together with the e2e discord fixture path:
- `tests/e2e`
- `tests/gateway/test_discord_allowed_mentions.py`
- `tests/gateway/test_discord_connect.py`

## Combined verification
Also ran the environment and Discord slices together:
- all passed

## Full-suite status
- Full suite rerun after the two fixes: **42 failed, 13,537 passed, 37 skipped**
- The two previously investigated clusters no longer appear in the failing list.
- Remaining failures are in other areas (Discord reply/send/slash, Telegram approval, modal sandbox, voice mode, provider parity, and a few tool tests).
