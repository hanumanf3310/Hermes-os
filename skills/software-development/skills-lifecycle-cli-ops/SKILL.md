---
name: skills-lifecycle-cli-ops
description: Implement or extend Hermes skills lifecycle CLI operations by wiring /skills subcommands through the registry, chat handler, and tests while preserving existing runtime behavior.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, cli, lifecycle, registry, commands, tests, compatibility]
    related_skills: [qualified-skill-fallback-hardening, systematic-debugging, test-driven-development]
---

# Skills Lifecycle CLI Operations

Use this when adding or fixing Hermes skill lifecycle commands such as:
- `/skills search`
- `/skills browse`
- `/skills inspect`
- `/skills install`
- `/skills list`
- `/skills check`
- `/skills update`
- `/skills audit`
- `/skills uninstall`
- `/skills reset`
- `/skills publish`
- `/skills snapshot`
- `/skills tap`

This pattern was validated while making sure the CLI command registry reflected the actual lifecycle actions already implemented in `hermes_cli.skills_hub`.

## Goal

Keep the lifecycle surface consistent across:
1. the runtime handlers in `hermes_cli/skills_hub.py`
2. the command registry in `hermes_cli/commands.py`
3. the interactive slash-command parser in `cli.py`
4. targeted tests and docs

The key idea is to avoid changing runtime behavior unless it is truly missing; often the bug is only that the CLI metadata or subcommand extraction does not expose the already-supported actions.

## When to Use

Use this skill when:
- a new `/skills` subcommand exists in the handler but is not visible in command help/completion
- the CLI registry and chat slash-command parser disagree about supported lifecycle actions
- a test expects lifecycle commands to be discoverable but the registry only exposes a partial list
- you need to make a skills command feel complete without breaking backward compatibility

## Workflow

### 1) Inspect the real handler surface first
Check `hermes_cli/skills_hub.py` and confirm which lifecycle actions already exist.

Also inspect the registry implementation for lifecycle side effects:
- whether disabled manifests are still loaded but filtered from default listing
- whether `remove`, `deactivate`, and `reactivate` must persist to disk
- whether audit logging needs a configurable path for tests and deployments

Look for:
- `do_install`
- `do_list`
- `do_uninstall`
- `do_update`
- `do_check`
- `do_audit`
- `do_reset`
- `do_publish`
- `do_snapshot`
- `do_tap`
- `handle_skills_slash`

If the handler already supports the action, prefer wiring metadata/tests instead of adding duplicate logic.

### 2) Update the command registry declaratively
In `hermes_cli/commands.py`, make sure the `CommandDef("skills", ...)` entry exposes the full lifecycle subcommand set.

Typical subcommands to include:
- `search`
- `browse`
- `inspect`
- `install`
- `list`
- `check`
- `update`
- `audit`
- `uninstall`
- `reset`
- `publish`
- `snapshot`
- `tap`

Keep the list aligned with the actual handler surface and with any help/completion logic that reads `SUBCOMMANDS`.

### 3) Keep slash-command handling thin
In `cli.py`, `_handle_skills_command()` should continue to delegate to `hermes_cli.skills_hub.handle_skills_slash()`.

Do not duplicate lifecycle business logic in the CLI layer. The parser should only:
- split the action
- forward arguments
- preserve user-facing status text if needed

### 3) Add lifecycle state transitions carefully
When implementing `deactivate-skill` / `reactivate-skill` / `remove-skill`:
- keep the default resolver path backward compatible
- allow disabled manifests to remain in the registry store, but exclude them from normal candidate selection
- make `list-skills` support an explicit `--all`/include-disabled mode so operators can inspect inactive entries
- persist state changes back to the manifest file when the registry is file-backed
- return `NOT_FOUND` for missing skill IDs rather than failing with an unhandled exception

### 4) Add deterministic audit logging if requested by the phase
If the phase calls for auditability, prefer a simple JSONL audit trail:
- one entry per action
- stable fields such as `action`, `skill_id`, `status`, and a small `details` object
- CLI flag like `--audit-path` to redirect the log during tests
- summary helpers should be deterministic so tests can assert on counts and action/status buckets

### 4.5) Preserve disabled-skill visibility without changing resolver behavior
When adding `deactivate/reactivate` lifecycle operations to a manifest registry:

- Keep disabled manifests loadable/listable for operations tooling (`list --all`, `reactivate`, `remove`).
- Keep resolver selection unchanged by filtering disabled entries at scoring/match time (not by deleting them from registry state).
- Add a listing mode split, e.g.:
  - default list: enabled only (backward-compatible operational behavior)
  - explicit list-all: include disabled (governance/audit workflows)
- Persist enabled-state changes back to the manifest file.
- Resolve manifest path by `skill_id` content, not filename convention alone, so lifecycle commands keep working even if filenames differ from IDs.

### 5) Add or update tests together with code
Add targeted tests for both registry exposure and runtime handling.

Good test targets:
- `tests/hermes_cli/test_commands.py`
- `tests/hermes_cli/test_skills_hub.py`
- any command-completion or help tests that use `SUBCOMMANDS`

Recommended assertions:
- the `/skills` registry includes all intended lifecycle subcommands
- handler-level tests still pass for install/list/update/uninstall flows
- help or completion output does not regress

### 6) Keep docs in sync
If the work is part of a phased roadmap, update the relevant status report or changelog.

Document:
- what changed
- whether runtime behavior changed or only metadata exposure changed
- what was verified

## Common Pitfalls

- **Registry drift**: the handler supports a subcommand, but `CommandDef("skills")` does not expose it.
- **Duplicated behavior**: re-implementing handler logic in `cli.py` instead of delegating.
- **Partial test coverage**: only checking one subcommand like `install` while the rest of the lifecycle set is still incomplete.
- **Mismatch between help and runtime**: completion shows commands that the parser cannot execute, or vice versa.
- **Unnecessary runtime changes**: if the issue is only discoverability, avoid altering working lifecycle logic.

## Verification Checklist

- [ ] `hermes_cli/skills_hub.py` still owns the lifecycle behavior
- [ ] `hermes_cli/commands.py` exposes the full `/skills` subcommand set
- [ ] `cli.py` delegates skills command handling cleanly
- [ ] Tests cover the registry surface and key lifecycle handlers
- [ ] Help/completion output matches the supported actions
- [ ] Docs or status report updated when the change is part of a phase

## Example Outcome

After the fix, the user-visible `/skills` command should advertise and route all supported lifecycle actions, not just the discovery actions like `search`, `browse`, `inspect`, and `install`.

That keeps the system honest:
- runtime features remain in `hermes_cli.skills_hub`
- CLI metadata remains in `hermes_cli.commands`
- chat parsing remains in `cli.py`
- tests prove the layers agree
