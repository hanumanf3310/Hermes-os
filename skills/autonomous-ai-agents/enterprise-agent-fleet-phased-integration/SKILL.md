---
name: enterprise-agent-fleet-phased-integration
description: Build and validate integration layer for a phased hierarchical agent fleet (registry, routing, orchestration, safety/QA gating) with compatibility checks.
---

# Enterprise Agent Fleet — Phased Integration

## When to use
Use when moving from "agents implemented" to "fleet operational" in a multi-phase architecture (e.g., Safety Core + Main Agents + Sub-Agents), especially before exposing a Boss-facing orchestrator.

## What this solves
- Connects 7 Main Agents + 21 Sub-Agents into one execution path
- Routes tasks deterministically
- Enforces safety intake + mandatory QA gate
- Prevents cross-phase interface mismatches (common failure point)

## Core workflow

1. **Create Agent Registry**
   - Centralize all Main Agent loaders/getters
   - Store `division -> chief` and `division -> [3 sub-agents]`
   - Expose topology (`total_main_agents`, `total_sub_agents`)

2. **Create Task Router**
   - First pass: explicit `task_type -> division` map
   - Second pass: keyword scoring
   - Fallback: route to operations triage when no strong match
   - Return route explanation (`reason`, `matched_keywords`, `confidence`)

3. **Create Fleet Orchestrator**
   - Intake task
   - Route to division
   - Run safety validation before execution
   - Support `dry_run=True` (planning only)
   - In live mode, enforce mandatory QA gate (DIV-05) before completion

4. **Fix interface compatibility immediately**
   - Verify method signatures between phases (especially escalation and validator interfaces)
   - If caller/callee mismatch exists, patch caller to match existing safety API contracts
   - During backend migrations, keep compatibility aliases (for example `execute_with_opencode` → `execute_with_backend`) until all callers move
   - Once the repo-wide caller search is clean, remove the legacy alias and rename tests/helpers to the new surface before promoting the change
   - After alias removal, run a repo-wide search for the legacy symbol and verify the result is zero before declaring the migration complete

5. **Centralize execution policy**
   - Put model/backend defaults in a single policy module rather than hardcoding them in agents/tests
   - Tests should import policy helpers instead of asserting literal model strings
   - Keep primary/secondary backend selection explicit so the fleet can switch between ThClaws/OMX without rewriting agent code

6. **Add phase integration tests**
   - Registry counts (7 main, 21 sub)
   - Router sanity cases (data -> DIV-03, engineering -> DIV-02, etc.)
   - Orchestrator dry-run success path
   - Safety-block path for fabrication prompts

## Critical compatibility lessons

### 1) Escalation signature mismatch
`main_agent_base` may call escalation with unsupported named args (`reason`, `agent_id`).

Expected pattern in this codebase:
- `escalate(level, context)`

Use context payload for extra details:
- `agent_id`, `task_id`, `issue`, `parent_agent`, `division`

### 2) Safety taxonomy mismatch
Safety Core can use legacy SA-* task taxonomy (e.g., `technical_writing`, `backend_code`) while router may output high-level task types (`communications`, `engineering`).

Add a normalization map in orchestrator:
- `DIV-01 -> web_search`
- `DIV-02 -> backend_code`
- `DIV-03 -> statistical_analysis`
- `DIV-04 -> technical_writing`
- `DIV-05 -> rule_compliance`
- `DIV-06 -> ui_design`
- `DIV-07 -> automation`

Without this, valid tasks can be incorrectly blocked by CRITICAL-02 specialty checks.

## Verification checklist
- [ ] Registry initializes with `ready=True`
- [ ] Topology reports `7 main / 21 sub`
- [ ] Router returns expected division for canonical prompts
- [ ] Dry-run returns `DRY_RUN_READY` for safe prompts
- [ ] Fabrication prompt returns `BLOCKED_BY_SAFETY`
- [ ] All integration tests pass

## Backend migration and fairness checks
When replacing a legacy execution backend with new candidates (for example ThClaws or OMX):

- Treat hardcoded model/runtime references as migration targets, not permanent contracts.
- Extract the execution backend behind a neutral interface before changing fleet policy.
- Keep the same prompt, the same requested model flag, and the same acceptance criteria across backends when comparing them.
- Use smoke tests that prove the real runtime path, not just config loading.
- If the new backend becomes the intended primary path, update the fleet tests to assert the new contract explicitly.
- If a test still encodes legacy behavior (for example hardcoded `opencode/big-pickle`), rewrite the test together with the code so the suite reflects the desired operating model.
- When cleaning up a compatibility alias such as `execute_with_opencode`, migrate callers in batches by domain, then re-run the phase tests that cover those divisions before removing the alias from the base class.
- Use a final search pass for the legacy symbol after each batch; only remove the alias once no production callers remain and the focused pytest slice still passes.
- For these migrations, run both `python -m py_compile` on all touched modules and the smallest meaningful pytest slice that spans the moved callers, not just the unit test for the base class.
- When cleaning up a compatibility alias such as `execute_with_opencode`, migrate callers in batches by domain, then re-run the phase tests that cover those divisions before removing the alias from the base class.
- Use a final search pass for the legacy symbol after each batch; only remove the alias once no production callers remain and the focused pytest slice still passes.
- For these migrations, run both `python -m py_compile` on all touched modules and the smallest meaningful pytest slice that spans the moved callers, not just the unit test for the base class.

## Hermes terminal usage note
When RTK policy is active, run shell via:
- `rtk run "<command>"`

Avoid:
- `rtk '<command>'`  (can fail with "No such file or directory")

## Phase 5 extension (Boss-facing Orchestrator)
After Phase 4 is stable, add `integrations/hermes_orchestrator.py` as the single entrypoint from Boss to Fleet:

- `submit_task(task_description, task_type, command, boss_id, dry_run, context)`
- `get_task_status(task_id)`
- `list_recent_tasks(limit)`
- `fleet_status()`

Implementation notes:
- Persist task/event logs under `logs/orchestrator/` as JSONL
- Keep in-memory history for fast status lookups in-session
- Always store the raw fleet result in task record for auditability

Recommended tests (`tests/test_phase5_hermes_orchestrator.py`):
- fleet ready + topology counts
- submit `plan` returns `DRY_RUN_READY`
- fabrication prompt is blocked by safety
- task lookup + recent listing

## Phase 6 extension (CLI Interface)
Add `integrations/hermes_cli.py` for operator/dev usage:

Commands:
- `status`
- `plan --type <task_type> "<task>"`
- `run --type <task_type> "<task>"`
- `task <task_id>`
- `recent --limit N`

Output rules:
- Default pretty JSON
- `--compact` for one-line JSON (automation-friendly)

Recommended tests (`tests/test_phase6_cli.py`):
- status output shape + readiness
- plan path returns `DRY_RUN_READY`
- recent returns list
- non-existent task returns `NOT_FOUND`

## Regression gate after each phase
When adding a new phase, always re-run previous phase tests to catch cross-phase breakage:
- After Phase 5: rerun Phase 4 tests
- After Phase 6: rerun Phase 5 tests
- After Phase 7: rerun Phase 6 tests

## Phase 7 extension (Monitoring & Logging)
Add `monitoring/monitoring_core.py` and wire it into `hermes_orchestrator.py`.

Core additions:
- Runtime counters (e.g., `tasks_total`, `status_*`, `blocked_by_safety`, `qa_passed`)
- Daily JSONL metric/event files under `logs/monitoring/`
- Health snapshot attached to `fleet_status()`
- Daily summary API via `monitoring_summary()`

Integration points in `HermesOrchestrator`:
1. Initialize `self.monitoring = MonitoringCore(root_dir)`
2. On startup, emit `ORCHESTRATOR_INITIALIZED`
3. On each submitted task, call `record_task_result(record.to_dict())`
4. Also emit mirrored `TASK_SUBMITTED` monitoring events
5. In `fleet_status()`, include `health` snapshot

CLI extension:
- Add `monitor` command in `integrations/hermes_cli.py`
- `monitor` should return `{ status: "OK", summary: ... }`

Recommended tests (`tests/test_phase7_monitoring.py`):
- `fleet_status()` includes `health` with `main_agents=7` and `sub_agents=21`
- After submitting at least one safe + one blocked task, summary shows:
  - `tasks_total >= 2`
  - `blocked_by_safety >= 1`
- CLI `monitor` command returns valid JSON summary

## Minimal test runner pattern
Create phase-specific test files with direct callable tests + pytest-compatible asserts. Include a `__main__` block to run quickly without extra tooling.