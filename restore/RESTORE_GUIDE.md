# Hermes OS Restore Guide - 2026-05-03 Context7 Checkpoint

This checkpoint is intended to restore Hermes OS to the working state where:

- Hermes OS status reports Gateway running, RTK enabled, and Context7 ready.
- Telegram gateway autostart is enabled and active.
- Dashboard graph validates with 118 nodes, 249 links, and one connected component.
- Context7 MCP is installed for current external documentation evidence.
- Context7 skill bindings are enabled for Hermes OS workflows.

## Restore Source

Remote:

```bash
https://github.com/hanumanf3310/Hermes-os.git
```

Checkpoint branch:

```bash
hermes-os-checkpoint-20260503-context7-restore
```

## Canonical Restore Source

The verified Git checkpoint branch is the source of truth for Hermes OS restore after:

- the branch exists on GitHub,
- a fresh shallow clone succeeds,
- `restore/MANIFEST.json` parses,
- restore-critical files exist,
- dashboard validation passes,
- and manifest hashes match.

Local `~/hermes-agent-backups` bundles are temporary fallbacks only while push or clone verification is blocked. After Git verification passes, clean local bundles or keep at most one newest emergency bundle with a written reason. Use `python3 scripts/prune-hermes-agent-bundles.py --after-verified-git-checkpoint --keep-latest 0` after successful push plus fresh-clone manifest/hash verification; use `--keep-latest 1` only for a documented offline emergency fallback.

Clone:

```bash
git clone --branch hermes-os-checkpoint-20260503-context7-restore https://github.com/hanumanf3310/Hermes-os.git ~/Hermes-os-restore
```

## What This Snapshot Captures

- `sources/hermes-agent/` - Hermes Agent core plus Hermes OS integrations in CLI, gateway, model picker, policy gate, and tests.
- `sources/hermes-os-runtime/` - live `~/.hermes/os` nerve/control runtime code, excluding caches and fleet task runtime data.
- `sources/hermes-workspace/` - dashboard/workspace files, including the refreshed memory graph.
- `skills/hermes-os/` - live Hermes OS skill namespace, including Context7 docs evidence, Context7 binding manifest, Obsidian integration notes, memory/context skills, policy skills, launcher helper, and v3 readiness tests; caches are removed.
- `bin/` - local wrapper commands such as `hermes-os`, `hermes-workspace`, and related helpers.
- `scripts/validate-dashboard-graph.py` - dashboard integrity validator used by restore smoke tests.
- `restore/MANIFEST.json` - generated file inventory and hashes.

## What Is Not Captured

Secrets and machine-local runtime state are intentionally excluded:

- `~/.hermes/.env`
- API keys, bot tokens, GitHub tokens, passwords, and `Repo.env`
- logs, sessions, broad skill caches, `__pycache__`, `node_modules`, venvs, and build artifacts
- fleet runtime task data

Keep the existing local secret files or recreate them after restore. Do not copy secrets into this repository.

## Restore Order

Stop the gateway first:

```bash
systemctl --user stop hermes-gateway.service
```

Create a dated quarantine folder for the broken state:

```bash
stamp=$(date +%Y%m%d-%H%M%S)
mkdir -p ~/.hermes/restore-quarantine/$stamp
```

Move the broken runtime out of the way while preserving it for inspection:

```bash
mv ~/.hermes/hermes-agent ~/.hermes/restore-quarantine/$stamp/hermes-agent.broken
mv ~/.hermes/os ~/.hermes/restore-quarantine/$stamp/os.broken
```

Restore Hermes Agent source:

```bash
mkdir -p ~/.hermes/hermes-agent
rsync -a ~/Hermes-os-restore/sources/hermes-agent/ ~/.hermes/hermes-agent/
```

If the old virtualenv was healthy, restore it from quarantine:

```bash
if [ -d ~/.hermes/restore-quarantine/$stamp/hermes-agent.broken/venv ]; then
  rsync -a ~/.hermes/restore-quarantine/$stamp/hermes-agent.broken/venv/ ~/.hermes/hermes-agent/venv/
fi
```

Restore Hermes OS runtime nerve code:

```bash
mkdir -p ~/.hermes/os
rsync -a ~/Hermes-os-restore/sources/hermes-os-runtime/ ~/.hermes/os/
```

Restore Hermes OS skills:

```bash
mkdir -p ~/.hermes/skills
rsync -a ~/Hermes-os-restore/skills/ ~/.hermes/skills/
```

Restore workspace dashboard files:

```bash
mkdir -p ~/hermes-workspace
rsync -a ~/Hermes-os-restore/sources/hermes-workspace/ ~/hermes-workspace/
```

Restore helper scripts and wrappers:

```bash
mkdir -p ~/.hermes/scripts ~/.local/bin
rsync -a ~/Hermes-os-restore/scripts/ ~/.hermes/scripts/
install -m 755 ~/Hermes-os-restore/bin/* ~/.local/bin/
```

Ensure Context7 MCP exists in `~/.hermes/config.yaml` under `mcp_servers`:

```yaml
mcp_servers:
  context7:
    connect_timeout: 30
    enabled: true
    timeout: 120
    url: https://mcp.context7.com/mcp
```

Restart the gateway:

```bash
systemctl --user daemon-reload
systemctl --user restart hermes-gateway.service
```

## Smoke Tests

Run these before trusting the restore:

```bash
hermes mcp test context7
hermes skills list --enabled-only | grep -i context7
hermes-os status
systemctl --user is-enabled hermes-gateway.service
systemctl --user is-active hermes-gateway.service
python3 ~/.hermes/scripts/validate-dashboard-graph.py ~/hermes-workspace/memory-graph/dashboard.html --json
curl -s -o /tmp/hermes-dashboard-check.html -w '%{http_code} %{size_download}\n' http://localhost:3300/dashboard.html
```

Expected high-signal results:

- Context7 connects and discovers `resolve-library-id` and `query-docs`.
- Context7 docs evidence and binding skills are enabled.
- `hermes-os status` shows `Gateway: running`, `RTK: Enabled`, and `Context7: Ready (external docs evidence)`.
- Gateway service is `enabled` and `active`.
- Dashboard validator reports `nodes=118`, `links=249`, `connected_components=1`, and `ok=true`.
- Dashboard HTTP check returns `200 95388` for this snapshot.

## Rollback Safety

If restore fails, stop the gateway and move the quarantined folders back:

```bash
systemctl --user stop hermes-gateway.service
rm -rf ~/.hermes/hermes-agent ~/.hermes/os
mv ~/.hermes/restore-quarantine/$stamp/hermes-agent.broken ~/.hermes/hermes-agent
mv ~/.hermes/restore-quarantine/$stamp/os.broken ~/.hermes/os
systemctl --user restart hermes-gateway.service
```

Only use the rollback commands with the same `stamp` created during that restore run.
