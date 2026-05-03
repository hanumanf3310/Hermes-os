# Hermes OS Restore Bootstrap

Generated: 2026-05-03

## Restore Source

Use checkpoint branch:

```bash
hermes-os-checkpoint-20260503-context7-restore
```

Remote:

```bash
https://github.com/hanumanf3310/Hermes-os.git
```

## First File To Read

Use `restore/RESTORE_GUIDE.md`. It contains the full restore order, Context7 MCP config snippet, smoke tests, and rollback commands.

## Critical Groups Captured

```text
sources/hermes-agent/
sources/hermes-os-runtime/
sources/hermes-workspace/
skills/hermes-os/
bin/
scripts/validate-dashboard-graph.py
restore/MANIFEST.json
restore/RESTORE_GUIDE.md
restore/CURRENT_STATE_20260503.md
```

## Caveat

Secrets are intentionally excluded. The live `skills/hermes-os/` namespace is captured, but cache folders are removed. Keep or recreate `~/.hermes/.env`, bot tokens, provider keys, and machine-local config values outside this repository.
