# Current State Evidence - 2026-05-03

This file records the working state that this Git checkpoint is meant to restore.

## Hermes OS

`hermes-os status` reported:

- Mode: Hermes OS
- Active: Yes
- Gateway: running
- RTK: Enabled
- Context Mode: Ready
- Context7: Ready (external docs evidence)
- Auto-run mode: pilot
- Kill switch: off
- Policy active ID: policy-0001

## Context7 MCP

`hermes mcp list` reported:

- `context7` at `https://mcp.context7.com/mcp`, enabled
- `context_mode`, enabled

`hermes mcp test context7` connected successfully and discovered:

- `resolve-library-id`
- `query-docs`

## Context7 Skills

`hermes skills list --enabled-only | grep -i context7` reported:

- `context7-docs-evidence...` under `hermes-os`, enabled
- `context7-skill-binding...` under `hermes-os`, enabled

## Telegram Gateway

`systemctl --user is-enabled hermes-gateway.service` returned `enabled`.

`systemctl --user is-active hermes-gateway.service` returned `active`.

## Dashboard

`python3 scripts/validate-dashboard-graph.py sources/hermes-workspace/memory-graph/dashboard.html --json` reported:

- nodes: 118
- links: 249
- duplicate nodes: none
- duplicate links: none
- missing link references: none
- connected components: 1
- isolated nodes: none
- ok: true

`curl http://localhost:3300/dashboard.html` returned:

```text
200 95388
```

## Repository Verification

Focused restore checkpoint checks passed:

- `git diff --check`
- `python3 -m json.tool restore/MANIFEST.json`
- `python -m py_compile` for changed Hermes Agent Python entry points and focused tests, using the live Hermes Agent venv
- `PYTHONPATH=. python -m pytest tests/hermes_cli/test_policy_gate_startup.py tests/tools/test_merged_policy_validator.py tests/hermes_cli/test_model_picker_parity_restore.py -q`

Pytest result:

```text
11 passed in 6.17s
```
