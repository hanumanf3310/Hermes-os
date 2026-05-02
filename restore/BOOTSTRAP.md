# Hermes OS Restore Bootstrap

Generated: 2026-05-02T19:58:50.706445+07:00

## Restore source
Use the verified checkpoint branch reported with this snapshot.

## Restore order
1. Clone `https://github.com/hanumanf3310/Hermes-os.git` at the checkpoint branch.
2. Copy `sources/hermes-agent/` into the Hermes Agent restore location after reviewing local secrets/config.
3. Copy `sources/hermes-workspace/` into `~/hermes-workspace/` if restoring dashboard/workspace state.
4. Install wrappers from `bin/` as needed.
5. Restore skills from `skills/` as needed.
6. Do not restore secrets from this repo; recreate `.env`, tokens, and `Repo.env` locally.
7. Verify Gateway with service + process + journal + Telegram/API evidence; service-active alone is insufficient.

## Critical files captured
```text
sources/hermes-agent/hermes_cli/commands.py
sources/hermes-agent/cli.py
sources/hermes-agent/gateway/run.py
sources/hermes-agent/gateway/platforms/base.py
sources/hermes-agent/hermes_cli/hermes_os_format.py
sources/hermes-agent/website/docs/reference/merged-hard-gate-policy.yaml
sources/hermes-agent/website/docs/reference/merged-hard-gate-policy.schema.json
sources/hermes-agent/tools/merged_policy_validator.py
sources/hermes-workspace/memory-graph/dashboard.html
```

## Caveat
Full pytest is not part of this checkpoint by Boss request; this backup is a rollback/restore safety point before touching risky test/venv work.
