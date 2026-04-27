---
name: enterprise-agent-fleet-rtk-integration
description: Integrate RTK wrapping into Enterprise Agent Fleet subprocess paths with a shared runtime helper, env-gated wrapping, and regression tests.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [rtk, enterprise-agent-fleet, subprocess, wrapping, tests]
---

# Enterprise Agent Fleet RTK Integration

Use this skill when the user wants the Enterprise Agent Fleet to use RTK for terminal/subprocess execution paths.

## Goal
Wrap subprocess-based execution with `rtk run` when `HERMES_RTK_WRAP=1`, while avoiding double-wrapping and keeping existing behavior unchanged when RTK is disabled.

## Recommended approach
1. Create a shared helper module, e.g. `integrations/rtk_runtime.py`.
2. Centralize all RTK decisions there:
   - `rtk_enabled()` reads `HERMES_RTK_WRAP`
   - `build_rtk_command(cmd)` returns either the original argv or `[rtk, run, ...cmd]`
   - `run_command(cmd, **kwargs)` delegates to `subprocess.run()` with the wrapped argv
3. Import the helper from the real execution points only:
   - Main-agent OpenCode execution
   - Sub-agent OpenCode execution
   - Service executor subprocess paths
4. Keep RTK as a thin transport wrapper only. Do not mix it with routing, knowledge, or safety logic.
5. Add tests that assert:
   - RTK disabled leaves commands unchanged
   - RTK enabled prepends `rtk run`
   - already-wrapped commands are not double-wrapped
   - main-agent, sub-agent, and service executor paths all use the shared helper
6. Run the full test suite after the change.

## Important implementation notes
- Prefer `rtk run "<shell command>"` for shell-style invocation only when the calling API expects a shell string.
- For Python subprocess argv calls, prefer raw argv wrapping: `["rtk", "run", *cmd]`.
- Do not use `rtk '<command>'`; that can be interpreted as a literal command name and fail.
- If RTK is enabled but the binary is missing, fail fast with a clear error.
- Preserve existing CLI/service output formats; RTK should only affect execution transport.

## Pitfalls
- Double wrapping a command that already starts with `rtk`.
- Patching only one execution path and leaving other subprocess paths unwrapped.
- Wrapping test subprocesses by accident instead of only production execution paths.
- Using shell quoting when the code already has argv arrays.
- Assuming `HERMES_RTK_WRAP` is always set; default behavior should remain unchanged when it is not.

## Verification checklist
- [ ] `rtk_runtime.py` added and imported by execution paths
- [ ] `HERMES_RTK_WRAP=1` activates wrapping
- [ ] `HERMES_RTK_WRAP` unset leaves behavior unchanged
- [ ] No double wrapping
- [ ] Dedicated RTK integration tests pass
- [ ] Existing Phase 10/11 tests still pass
- [ ] Full suite passes

## Example pattern
```python
from integrations.rtk_runtime import run_command

result = run_command([
    "opencode",
    "run",
    "--model",
    "opencode/big-pickle",
    "--acp",
    "--stdin",
], input=prompt, capture_output=True, text=True, timeout=300)
```

This pattern keeps RTK as a reusable transport layer instead of scattering wrapper logic across agents and executors.
