# Hermes-os Backup Restore Guide

This repository is a consolidated backup snapshot for Hermes-os-related sources,
selected skills, command wrappers, and thclaws restore material.

## What is included
- `sources/hermes-agent/`
- `sources/hermes-workspace/`
- `skills/`
- `bin/`
- `thclaws/`
- `restore/MANIFEST.json`

## What is intentionally excluded
- secrets and tokens
- logs and session data
- caches, build output, and compiled artifacts
- package managers' dependency caches

## Restore flow
1. Clone this repository.
2. Review `restore/MANIFEST.json` for the exact scope.
3. Copy the wrapper scripts in `bin/` into `~/.local/bin/` if needed.
4. Rebuild thclaws from `thclaws/releases/thclaws-c69986b-20260426/` if the binary is missing.
5. Load Hermes skills from the `skills/` tree into your local Hermes skill store.
6. Keep your personal `Repo.env` outside the repository.

## GitHub note
The actual `Repo.env` used for upload lives outside the repo and is not committed.
