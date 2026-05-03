# Hermes-os Backup

This repository contains a consolidated backup of Hermes-related source, selected skills, wrappers, and restore notes.

## Layout
- `sources/hermes-agent/`
- `sources/hermes-os-runtime/`
- `sources/hermes-workspace/`
- `skills/hermes-os/`
- `bin/`
- `scripts/`
- `thclaws/`
- `restore/`

## Restore notes
- Secrets are intentionally excluded.
- Runtime caches, logs, sessions, and build artifacts are excluded.
- The live Hermes OS skill namespace is captured, with cache folders removed.
- Use `restore/RESTORE_GUIDE.md` first. It documents the restore order, Context7 MCP config, smoke tests, and rollback safety steps for the current restore-ready checkpoint.
