---
name: hermes-os-phase3-readiness-gate
description: Readiness-first workflow for Hermes OS Phase 3 Smart Router rollout, with compatibility checks, safe defaults, and analyzer/legacy-router alignment before code changes.
category: software-development
author: Hermes Assistant
guide_for: Hermes OS / enterprise-agent-fleet integration work
version: 1.3.2
---

# Hermes OS Phase 3 Readiness Gate

Use this when user asks to start Week2/Smart Router work (or similar auto-routing rollout) but implementation has not yet been wired end-to-end.

## Core principle

**Do not code-path hard switches before proving baseline behavior.**
Use a compatibility-first, analyze-only-first rollout:
1) discover the true execution path,
2) confirm current behavior,
3) identify gaps,
4) then implement with fallback-to-legacy.

---

## Prerequisites

- Environment sanity checks first:
  - Confirm runtime/test Python differs from system python.
  - In this environment, `/usr/bin/python3` lacks `pytest`; always run tests via `~/.hermes/hermes-agent/venv/bin/python3`.
- Import path sanity:
  - For running router/analyzer tests from skills root, set `PYTHONPATH` explicitly so `v3` imports resolve.
    - Recommended:
      `PYTHONPATH=$HOME/.hermes/skills/hermes-os:$HOME/.hermes/os`
- Runtime imports may still fail from repo root without `PYTHONPATH` when calling `from hermes_os import HermesOS`.

---

## Mandatory Readiness Checklist

### 1) Confirm active state and entrypoint

- `cat ~/.hermes/state/hermes-os.json`
- Read `~/.hermes/os/integrations/telegram_bridge.py` and locate:
  - mode check (`hermes_os`)
  - `process_message` behavior
- Read `~/.hermes/os/hermes_os.py` and locate:
  - `execute()` flow
  - router call site
  - fallback path when router unavailable

### 2) Map current routing layer

- Read routing and compatibility surfaces:
  - `~/.hermes/os/core/router/task_router.py` (if present)
  - `~/.hermes/skills/hermes-os/v3/router.py` (Phase 3 adapter)
- Confirm outputs/routes currently used (`hermes_direct`, `fleet_complex`) and that legacy route names still work as fallback.
- Verify alias mapping in analyzer/router docs/tests:
  - `direct` -> `hermes_direct`
  - `direct_with_suggestion` -> `hermes_direct`
  - `fleet` -> `fleet_complex`
- If Phase 3 analyzer exists (`skills/hermes-os/v3/analyzer.py`), verify it is actually wired in (adapter + HermesOS.execute callsite).

### 3) Confirm analyzer module quality

- Read analyzer tests and run from `~/.hermes/skills/hermes-os/v3`:
  - `cd ~/.hermes/skills/hermes-os/v3`
  - `PYTHONPATH=~/.hermes/skills/hermes-os:~/.hermes/os ~/.hermes/hermes-agent/venv/bin/python3 -m pytest test_analyzer.py -q`
- Optional but recommended: add smoke coverage for route contract and run together:
  - `PYTHONPATH=~/.hermes/skills/hermes-os:~/.hermes/os ~/.hermes/hermes-agent/venv/bin/python3 -m pytest test_analyzer.py test_router_smoke.py -q`
- Record pass rates explicitly (for evidence, e.g. `21 passed`, `25 passed`).

### 4) Smoke route behavior (before edits)

- Use a runtime probe script (with PYTHONPATH and venv python) to assert decision metadata and fallback behavior:

  - `PYTHONPATH=~/.hermes/skills/hermes-os:~/.hermes/os ~/.hermes/hermes-agent/venv/bin/python3 - <<'PY'
    from hermes_os import HermesOS
    os = HermesOS();
    # run 2-3 sample tasks for direct/fleet/analyze-only assertions
    PY`
- Confirm:
  - `analyze_only` keeps behavior stable and does not hard-switch
  - raw task override paths still route through existing runtime contracts
  - fallback route remains valid when analyzer decision is out-of-band

### 5) Integration surface scan

Use `search_files` for:
- `analyze_task\(|TaskAnalyzer|direct_with_suggestion|router|analyze_only|auto_route`.
- Detect config-only placeholders or stale references.

---

## Decision gates before Week2 code changes

Proceed only if:

- ✅ Analyzer tests pass.
- ✅ State and bridge are active/in-sync in hermes mode.
- ✅ Current path is understood and documented.
- ✅ Gaps are listed (e.g., analyzer not wired, missing flags, no integration tests).

If gaps exist, document them first in `LEARNING_DATABASE.md` and request approval before implementation.

---

## Implementation pattern for Phase 3 C (safe)

- Introduce new router/wrapper module that normalizes to current route enum to avoid breaking existing downstream contracts.
- Add config flags (feature-safe defaults):
  - `analyze_only` (default `True`)
  - `auto_route_enabled` (default `False` until proven)
  - `auto_route_threshold`
  - `manual_override`
- Keep fallback behavior: on analyzer/router error, use current `TaskRouter`/legacy direct path.
- Add route trace + decision metadata to the returned result.
- Add integration tests for flow:
  - telegram_bridge -> hermes_os -> router/task execution
  - fallback/exception path

---

## Commands that caused useful insights

- `read_file` for: `hermes_os.py`, `telegram_bridge.py`, `task_router.py`, `v3/analyzer.py`.
- `search_files` for integration term scan.
- `ls` in `skills/hermes-os/v3` to confirm artifact presence.
- `cat ~/.hermes/state/hermes-os.json` to verify active mode.

## Common pitfalls observed

1. Running `python3 - <<... import hermes_os` from wrong cwd without `PYTHONPATH`.
2. Assuming analyzer outputs can be consumed directly without adapter to existing route enum schema.
3. Treating global `python3` as pytest-enabled when it is not.
4. Making routing changes before confirming `TaskRouter` and `HermesOS.execute()` contract.
5. Importing skill modules with hyphen in package path via `from skills.xxx-yyy` (SyntaxError). Use explicit `importlib.machinery.SourceFileLoader` in verification scripts when module name contains non-identifier chars.

---

## Trial-and-error hardening notes (reusable)

When implementing smart-route work, use this fallback-first verification sequence:

- **Context path hardening**: Ensure bridge/integration layers pass both `message` and `raw_task` into execution context.
- **Manual override robustness**: `_extract_manual_override` should accept fallback chain `(context['raw_task'] || context['message'] || task_description)` before parsing prefixes.
- **Adapter-safe route names**: Keep compatibility mapping to legacy names (`direct`, `direct_with_suggestion` -> `hermes_direct`, `fleet` -> `fleet_complex`) and never hard-switch behavior in the same patch.
- **Status truth source**: Validate `hermes-os` status output through the integration skill handler path, not only `status()` object fields.
- **Backup discipline**: Snapshot critical files before risky edits (e.g., `telegram_bridge.py`, `hermes_os.py`, integration skill).

Recommended order in this phase:

1. Verify readiness artifacts and route contract.
2. Implement context/manual override fixes only (no config hard-switch).
3. Add smoke assertions for the bridge → router path.
4. Update learning logs.
5. Re-run syntax + `pytest` gates before any rollout decision.


## Evidence logging

After readiness work, append concise notes to:
`~/.hermes/database/hermes-os-learning/LEARNING_DATABASE.md`

Include:
- what was observed,
- what passed,
- explicit gaps,
- approved rollout order,
- backup artifact paths,
- changed keys and validation commands/results.
### 2-3-1 Config-Change Execution Rule (preferred)

For runtime-affecting Phase-3 config updates, apply this loop for each candidate key:

1. **2 = 2 checkpoints before edit**
   - Snapshot targeted file (for risky files at minimum, and always include config/runtime-related files).
   - Record current effective values from source-of-truth before edit (config section + status output).
2. **3 = verify after edit**
   - Verify status paths that users actually consume (`HermesOS.status()`, integration status command), not only raw dict fields.
   - Run runtime sanity probes for expected contract behavior (including analyze-only/fallback routing expectations).
3. **1 = one change at a time**
   - Change exactly one config/behavior value per round.
   - Never combine with `analyze_only` or core safety flag flips unless explicitly approved as a separate rollout round.

Only proceed to next round after:
- explicit successful smoke test,
- log appended,
- user-confirmed continuation.

### Field-tested Rollout Pattern (used in this run)

- **Round 1:** `auto_route_threshold 0.8 → 0.9`
- **Round 2:** `auto_route_enabled false → true`
- **Round 3:** `auto_route_threshold 0.9 → 0.92`

All rounds passed:
- syntax/runtime smoke for `test_analyzer.py` + `test_router_smoke.py`.
- status checks via both `HermesOS.status()` and status card output.
- manual override invariants (`/fleet`) remained respected.

### Practical command patterns (from field experience)

- Python runtime checks in this environment should use venv python and explicit `PYTHONPATH`:
  - `PYTHONPATH=$HOME/.hermes/skills/hermes-os:$HOME/.hermes/os ~/.hermes/hermes-agent/venv/bin/python3 - <<'PY' ...`
- If module imports fail with hyphenated package names (`hermes-os`, etc.), use loader-based imports for diagnostics:
  - `SourceFileLoader('hermes_os_integration_skill', '/.../skills/hermes-os-integration/skill.py').load_module()`
- Keep backups for config changes in a versioned backup folder for each round.
- For any direct `import hermes_os` or skill module from script, verify current working dir and import path; when needed, load by absolute path to avoid package-name conflicts.

### Field-validated rollout check (safe auto-route enablement)

A reusable validation sequence used in Round 2 (safe-only):
- Baseline and post-change smoke: `test_analyzer.py` + `test_router_smoke.py` must pass.
- Change exactly one key: `auto_route_enabled` `false -> true` while keeping `analyze_only: true`.
- Validation expectations:
  - `HermesOS().status()['phase3']['auto_route_enabled']` reflects `True`.
  - Skill status output shows `Analyze-Only: 🟢` and `Auto-Route: ON`.
  - Manual override (`/fleet ...`) continues to force Fleet routing.
  - Non-overridden simple tasks remain `hermes_direct` unless analyzer confidence and policy allow auto-route.
- Keep `analyze_only: true` for the next round if zero confidence-change risk policy is required.

### Learning System Reality Check

Hermes OS currently has *memory + knowledge capture*, but not a fully closed-loop learning engine in core runtime:
- `HermesOS` memory is currently limited to `sessions` and `preferences`.
- `LEARNING_DATABASE.md` is the durable human-readable source of truth for lessons, rollout logs, config confirmations, and rollout holds.
- `hybrid_karpathy_memory.py` exists as a separate planner/worker/reviewer pipeline that can store SQLite memories.
- The core `HermesOS.execute()` path does **not** currently wire that script in as an autonomous learning loop.
- `config.yaml` does not yet expose a learning policy control that lets the runtime self-tune routing from feedback.

Therefore, treat learning as *advisory and human-curated* until telemetry, feedback, and policy-versioning are added.

### Learning Gap-to-Roadmap Order

When the user asks for the next learning step, use this order:
1. Add structured routing telemetry for every execution decision.
2. Add explicit feedback capture from Boss/user outcomes.
3. Add a versioned learning policy store separate from runtime config.
4. Add offline replay/evaluation against historical tasks before policy changes.
5. Add auto-tuning only after rollback guards and drift thresholds exist.

### Observation Window Rule

After a safe config change, hold the last known-good threshold (e.g. `0.92`) long enough to collect production-like signals before the next rollout:
- route distribution (`hermes_direct` vs `fleet_complex`)
- manual override frequency (`/fleet`, `/hermes-os fleet`)
- fallback / analyze-only behavior
- routing metadata fields and exceptions

If false-positive routing or operational risk appears, rollback the most recent config key first.

### Phase A (Telemetry Foundation) Field-Tested Template

When starting Phase A, follow this order before any threshold or routing-policy changes:

- **1) Runtime safety baseline** (no code change): confirm `analyze_only=true`, `auto_route_enabled` + current threshold are known from live status/runtime sources.
- **2) Add telemetry sink + memory window** in `hermes_os.py`:
  - append-only JSONL: `~/.hermes/state/hermes_os_route_telemetry.jsonl`
  - in-memory window (e.g., `routing_telemetry`) and count fields for quick status visibility
  - expose route-path metadata on status output (path + cached count)
- **3) Capture decision trace in execution path**:
  - add `resolution_reason`/route metadata in `_resolve_execution_route`
  - time route + execution + total latency (`perf_counter`)
  - append events with `event_id`, `task_id`, `route`, `confidence`, `decision`, `manual_override`, runtime flags, and outcome/error outcome
- **4) Keep hard-switching untouched in Phase A**:
  - retain `analyze_only=true` and existing safety gates
  - do not change config policy during telemetry hardening
- **5) Add/extend tests first for Phase A signals**:
  - create `test_telemetry_foundation.py`
  - cover: execution emits event, manual `/fleet` override is preserved, required schema fields exist
- **6) Verify and log**:
  - `python3 -m py_compile ~/.hermes/os/hermes_os.py`
  - `cd ~/.hermes/skills/hermes-os/v3 && PYTHONPATH=/home/hanuman3310/.hermes/skills/hermes-os:/home/hanuman3310/.hermes/os /home/hanuman3310/.hermes/hermes-agent/venv/bin/python3 -m pytest test_analyzer.py test_router_smoke.py test_telemetry_foundation.py -q` (expected **29 passed** in this branch)
  - runtime command check: confirm `HermesOS.status()['telemetry']` and one execute writes one JSONL event
  - update `~/.hermes/database/hermes-os-learning/LEARNING_DATABASE.md` immediately with results
- **7) Backup discipline**: snapshot risky files before edits in versioned backup folder.

### Additional environment observation

- In this workspace, `git status` can fail with `fatal: not a git repository` if run from non-repo paths (`~/.hermes`); run from the correct git root when change-tracking is required.

### Phase B Feedback Capture (Closed-loop Foundation)

Use this after Phase A telemetry is stable and before any policy auto-tuning.

## Phase B objective
Capture human feedback on routing outcomes without changing routing behavior yet, and produce deterministic metrics baseline for future tuning.

---

## Phase C Policy Store & Controlled Rollout (Field-tested this run)

This run moved to a **proposal + readiness + apply** model before any behavior change.

### Recommended order (no hard-switch in this phase)

1. **Foundation implementation first (no runtime behavior flip):**
   - Add versioned policy store (JSONL ledger + active policy index/state file) in `~/.hermes/state/`.
   - Keep `analyze_only=true` regardless of proposal state.
   - Keep route names mapped to legacy contracts.
2. **Propose-only workflow:**
   - Implement `propose_learning_policy(...)` to validate candidate payload and append a `proposed` record.
   - Include candidate fields like `candidate_id`, `auto_route_threshold`, `auto_route_enabled`, `created_by`, `reason`.
   - Do not apply candidate immediately.
3. **Readiness-only evaluation:**
   - Add `evaluate_learning_policy_readiness(candidate, metrics)` using existing feedback telemetry.
   - Evaluate directional false-positive risk (`should_direct`, `should_fleet`) before changing thresholds.
4. **Apply step:**
   - Only when readiness passes and approved, run `apply_learning_policy(candidate_id)`.
   - After apply, verify output contract now references the active policy id/values.
5. **Visibility + guardrails:**
   - Expose status/metrics/readiness in both bridge and skill command surfaces.
   - Maintain explicit `policy_id`, `policy_status`, and `auto_route_threshold` in contract.
   - Keep manual override (`fleet` path) unchanged.

### Validation commands used in this phase

- `PYTHONPATH=$HOME/.hermes/skills/hermes-os:$HOME/.hermes/os ~/.hermes/hermes-agent/venv/bin/python3 -m pytest skills/hermes-os/v3/test_analyzer.py test_router_smoke.py test_telemetry_foundation.py test_feedback_capture.py test_learning_policy_store.py -q`
- Runtime smoke with explicit runtime path:
  - `PYTHONPATH=$HOME/.hermes/skills/hermes-os:$HOME/.hermes/os ~/.hermes/hermes-agent/venv/bin/python3 - <<'PY'
from hermes_os import HermesOS
os = HermesOS()
print(os.get_active_learning_policy())
print(os.get_policy_status())
print(os.evaluate_learning_policy_readiness('policy-0001-candidate-0005', min_feedback_events=1))
PY`
- For route-contract smoke: assert `direct`, `direct_with_suggestion`, `fleet` values remain mapped to `hermes_direct`/`fleet_complex` while in analyze-only mode.
### Field-tested evidence snapshot (this branch)

- full relevant suite: `41 passed` (`test_analyzer`, `test_router_smoke`, `test_telemetry_foundation`, `test_feedback_capture`, `test_learning_policy_store`) in this branch
- syntax compile checks: `py_compile` on changed files passed
- no hard-route switch performed (`analyze_only=True`, no direct hard route mutation)
- proposal/apply split worked in incremental loop (`propose` creates candidate only, `apply` flips active policy)
- explicit backup discipline used before risky edits
- readiness gate now includes guardrails for minimum sample floor, false-positive ceilings, threshold drift, and offline-replay route-stability checks

### Compatibility gotchas observed in the field

- `import hermes_os` from script may fail without explicit `PYTHONPATH` in this workspace (`No module named 'os.integrations'` / `No module named 'hermes_os'` depending cwd).
- `evaluate()` method confusion in runtime script: use `execute()` for current API.
- Keep commands mentioned in user-facing copy as `hermes-os`, `fleet`, `skill` (without leading `/`) when that is the project's UX rule.
- Readiness in this branch remains `analyze_only`-gated and offline replay-dependent: even strong metrics can still keep candidate `ready=False` until replay verification is added.
---

## Recommended sequence

1. **Prepare runtime safety context first**
   - Confirm `analyze_only=true` and existing `auto_route_enabled`/`auto_route_threshold` are known and accepted for safety-first rollout.
   - Keep compatibility-first defaults until evidence supports change.

2. **Add canonical feedback label contract in runtime core**
   - In `hermes_os.py`, define canonical label set, e.g.:
     - `correct`
     - `incorrect`
     - `should_direct`
     - `should_fleet`
   - Reject unknown labels early with deterministic error text.

3. **Add feedback capture API (no hard-switch)**
   - Add `HermesOS.capture_routing_feedback(task_id, label, note=None, source="user")`.
   - Resolve latest routing decision for `task_id` and store a `routing_feedback` JSONL event with:
     - `event_version`, `event_at`, `task_id`, `label`, `note`, `source`
     - `expected_route`
     - snapshot metadata (`route`, `confidence`, `manual_override`, `decision_source`, `analysis_output`)
   - Keep write path safe on malformed telemetry lines.

4. **Add robust lookup + writer helpers**
   - `_find_latest_routing_decision(task_id)` must tolerate missing/invalid JSON records and partial schema.
   - `_append_feedback_event(event)` writes to existing telemetry sink.

5. **Add route-contract-safe aggregation metrics API**
   - Add `get_routing_feedback_metrics(limit: Optional[int] = None)` returning at minimum:
     - `routing_total`, `feedback_total`, `route_mix`
     - `manual_override_count`, `manual_override_rate`
     - `feedback.labels.*`
     - false-positive hints for `should_direct` and `should_fleet`
   - Normalise route alias names to current routing contracts before counting.

6. **Expose through integration/skill boundaries**
   - Add bridge methods and skill command dispatch:
     - `hermes-os feedback <task_id> <label> [note]`
     - `hermes-os metrics [N]`
   - Update help text in command handler.

7. **Add focused tests before broader test runs**
   - Create/update `test_feedback_capture.py` with:
     - happy path write
     - malformed telemetry JSON fallback
     - invalid task id / invalid label
     - metrics route mix + false-positive checks
     - integration command path checks

8. **Verify + evidence logging (mandatory)**
   - Runtime compile check:
     - `python3 -m py_compile os/hermes_os.py os/integrations/telegram_bridge.py skills/hermes-os-integration/skill.py`
   - Test command pattern used successfully in-field:
     - `PYTHONPATH=/home/hanuman3310/.hermes/os:/home/hanuman3310/.hermes/skills/hermes-os /home/hanuman3310/.hermes/hermes-agent/venv/bin/python3 -m pytest test_analyzer.py test_router_smoke.py test_telemetry_foundation.py test_feedback_capture.py -q`
   - Update `LEARNING_DATABASE.md` in same round with:
     - contract changes
     - passed counts
     - baseline snapshot

## Field-tested checkpoint from this run

- `test_feedback_capture.py` added and all related tests pass with aggregate suite:
  - **34 passed**
- Initial runtime metrics snapshot after Phase B capture:
  - `routing_total=19`, `feedback_total=2`
  - `route_mix={'direct':8,'fleet':10,'direct_with_suggestion':1,'unknown':0}`
  - `manual_override_rate=0.2631578947368421`
  - `feedback.labels.correct=2`, `incorrect=0`, `should_direct=0`, `should_fleet=0`
  - `false_positive` counts both 0
- Field-tested checkpoint (Phase C+):
  - Added offline replay pre-flight to readiness evaluation (`_evaluate_candidate_offline_replay` + `_simulate_execution_route_for_policy`).
  - Added route canonicalization (`direct`, `direct_with_suggestion`, `fleet`) and stability guards.
  - Added recent-window drift guard for replay to catch trend risk even when overall flip-rate is still acceptable:
    - `READINESS_RECENT_REPLAY_WINDOW=5`
    - `READINESS_MAX_RECENT_ROUTE_FLIP_RATE=0.55`
    - readiness reason code: `offline_replay_recent_drift_risk`
  - Added confidence-bound guard for sparse replay samples using Wilson upper bound:
    - `READINESS_MIN_CONFIDENCE_REPLAY_EVENTS=8`
    - `READINESS_CONFIDENCE_Z=1.96`
    - readiness reason code: `offline_replay_confidence_low`
    - trigger intent: block candidates when sample is still small, there is at least one mismatch, and the confidence upper bound still exceeds the operational flip-rate ceiling.
  - Added seasonal and sparsity replay guards:
    - `READINESS_MAX_SEASONAL_FLIP_DELTA=0.3` with reason code `offline_replay_seasonal_shift_risk`
    - `READINESS_MIN_ROUTE_SUPPORT=2` with reason code `offline_replay_route_sparsity_risk`
    - trigger intent: detect half-window regime shift and route-bucket under-sampling risk even when aggregate flip-rate still looks acceptable.
  - Added readiness `policy_report` payload for audit-style approvals before apply:
    - `acceptance_passed`, `failed_signals`, per-signal blockers, replay metrics snapshot
    - emitted in both readiness pass/fail responses to keep contract stable for command/status rendering.
  - Expanded readiness tests for route-flip and replay stability/drift/confidence/seasonal/sparsity/reporting (`test_readiness_offline_replay_stability_pass`, `test_readiness_offline_replay_route_flip_guard`, `test_readiness_offline_replay_recent_window_drift_guard`, `test_readiness_offline_replay_confidence_bound_guard`, `test_readiness_offline_replay_seasonal_shift_guard`, `test_readiness_offline_replay_route_sparsity_guard`).
  - End-to-end evidence run in this branch now includes
    - `test_learning_policy_store.py`: 11 passed
    - full v3 suite (`test_analyzer`, `test_router_smoke`, `test_telemetry_foundation`, `test_feedback_capture`, `test_learning_policy_store`): **45 passed**
  - Added route-sparsity guard for under-sampled mismatch buckets:
    - `READINESS_MIN_ROUTE_SUPPORT=2`
    - readiness reason code: `offline_replay_route_sparsity_risk`
    - trigger intent: block candidates when mismatches happen on routes with too little baseline support for trustworthy inference.
  - Expanded readiness tests for route-flip and replay stability/drift/confidence/sparsity/seasonal (`test_readiness_offline_replay_stability_pass`, `test_readiness_offline_replay_route_flip_guard`, `test_readiness_offline_replay_recent_window_drift_guard`, `test_readiness_offline_replay_confidence_bound_guard`, `test_readiness_offline_replay_seasonal_shift_guard`, `test_readiness_offline_replay_route_sparsity_guard`).
  - End-to-end evidence run in this branch now includes
    - `test_learning_policy_store.py`: 11 passed
    - full v3 suite (`test_analyzer`, `test_router_smoke`, `test_telemetry_foundation`, `test_feedback_capture`, `test_learning_policy_store`): **45 passed**
- Risk handling and hygiene:
  - Guardrails in readiness now include minimum threshold floor, threshold-delta, false-positive caps, and replay route-change-rate ceilings.
  - Readiness remains analyze-only-first; no hard-switch route auto-apply.
  - Candidate readiness can return `ready=False` with reason codes even under sufficient feedback count.
- Evidence updates in LEARNING DB + fact_store entries were part of completion in each round.

### Phase C+ Operator-Facing Readiness Card pattern (integration-level)

For readable operator review without changing behavior, keep `readiness`/`status` UX in integration layer (`skills/hermes-os-integration/skill.py`) and keep runtime core logic unchanged unless explicitly approved.

#### Recommended implementation sequence

1. **Add dedicated readiness formatter before changing payloads**
   - Implement a helper such as `_format_readiness_report(policy_id, readiness)`.
   - Emit stable sections: acceptance, signals, metrics, reason/failed signals, and review guidance.
   - Include `policy_report` always in readiness responses (pass/fail/insufficient-data) so downstream renderers stay stable.
2. **Normalize commands to project UX style**
   - Ensure user-facing usage/help examples use `hermes-os`, `fleet`, `skill` without leading slash when policy requires.
3. **Bind through status/readiness handler only**
   - Route command handler: `subcmd in {ready/readiness}` should call the same formatter and not alter execution routes.
   - Keep route contract and compatibility invariants in core (`direct`, `direct_with_suggestion`, `fleet`) unchanged.
4. **Add concise audit copy updates**
   - Show active policy lineage in status (`active_id`, `active_sequence`, state and artifact paths).
   - Ensure acceptance output is review-friendly with explicit thresholds and failure reasons.
5. **Verification pattern (mandatory)**
   - `py_compile` for changed files.
   - Targeted tests for changed area + existing v3 suite.
   - runtime smoke with explicit `PYTHONPATH` and venv python:
     - call `status` and `readiness <policy_id> <min_feedback_events>` and validate card shape.
   - confirm `acceptance_passed` remains false if not ready (analyze-only posture still active).
6. **Reason-explainability hardening**
   - Keep core readiness payload contract in `hermes_os.py` untouched where possible; map human-facing explanation at integration formatter level.
   - Add/maintain `reason_explanations` dictionary in `_format_readiness_report(...)` so unknown reason codes fall through as `รหัส: รหัส` (no crash) and known codes have action-oriented Thai copy.
   - Add a dedicated checklist item: verify `Reason insights:` appears in readiness card for rejected candidates in runtime smoke.
7. **Failure recovery discipline**
   - If a broad edit causes syntax/runtime failure, immediately restore from backup and rerun compile before continuing.

**Field evidence (this run):**
- `45 passed` in core v3 subset (`test_analyzer`, `test_router_smoke`, `test_telemetry_foundation`, `test_feedback_capture`, `test_learning_policy_store`) before formatter-only Option 2 expansion.
- Readiness smoke: `hermes-os readiness policy-0001 20` returned review card with `Acceptance: ⚠️ REVIEW_REQUIRED`, failed signal `policy_state`, and `policy_not_ready_for_readiness` reason code while still not applying route changes.
- Backups captured for risky edits in `~/.hermes/backups/hermes-os-phase3-policy-report-card/`.

### Phase C+ Option 2 Contract-First Pattern (Formatter-only, no route change)

- Add integration contract tests for readability/auditability first (RED→GREEN):
  - test `HermesOS.evaluate_learning_policy_readiness(...)` payload coverage of `policy_report.signals`
  - test `_format_readiness_report(...)` renders every signal key into deterministic card sections
  - test unknown `reason_code` shows Thai fallback copy (no crash, still readable)
- Keep runtime logic untouched until formatter contract proves stable; this avoids behavior-risk while improving operator observability.
- Use explicit module loading in tests (`importlib.util.spec_from_file_location`) to avoid hyphenated package import quirks in `hermes-os` module path.
- Evidence in this run:
  - Added `skills/hermes-os/v3/test_readiness_formatter_contract.py`
  - `47 passed` including formatter contract tests
  - smoke check: readiness card includes `**Reason insights:**` and `policy_not_ready_for_readiness` explainability line
  - Fact log: `fact_store` entry added (`fact_id: 144`) documenting this milestone

### Phase C+ Option 3 Command-Path Contract Pattern (Integration Command Coverage)

- Add explicit integration contract tests for command handlers before operator-facing formatter changes are considered done:
  - `handle_command('hermes-os', 'readiness <policy_id> [min_samples]')` happy path
  - invalid args path (`min_samples` parse failure)
  - bridge failure path (`ok=False`)
- Assert that bridge delegation is called with canonical payload `(policy_id, min_feedback_events)` and that standardized usage/error strings stay stable.
- Use a lightweight bridge mock to avoid integration flake and to prove command routing contract independent of runtime state.
- Evidence in this run:
  - Added `skills/hermes-os/v3/test_readiness_command_path_contract.py`
  - `50 passed` in v3 subset after adding command-path contract tests
  - runtime smoke confirmed `calls=[('policy-0001', 20)]`

### Phase C+ Option 4 Golden-Text Snapshot Pattern (Formatting Drift Guard)

- For critical human-visible cards, follow a stricter contract step after command-path tests:
  - add full-string golden snapshot assertions for output formatting
  - include section headers, ordered signal lines, replay metrics text, reason explanations, notes, and recommendation footer
- Keep snapshot focused and stable by pinning the same test fixture (policy_id, observed/required counts, signals, replay fields, reason codes, notes).
- This catches accidental wording/layout regressions even when behavior remains unchanged.
- Evidence in this run:
  - expanded `test_readiness_command_path_contract.py` with
    `test_hermes_os_readiness_command_success_golden_contract_snapshot`
  - `51 passed` across 7 v3 suites (`test_readiness_command_path_contract.py` included)

### Phase C+ Option 5 Command-Path Metrics Contract Pattern (Routing Metrics Operator Surface)

- After formatter contracts, add integration command-path coverage for `hermes-os metrics` in the same style to lock runtime-facing operator contract before touching policy logic.
- Implement contract tests that assert delegation and output behavior for:
  - success path: `handle_command('hermes-os', 'metrics')` passes normalized payload to bridge and renders expected card fields (`routing_total`, `feedback_total`, `manual_override_rate`, `route_mix`, `feedback.labels`, `false_positive`)
  - invalid args: parse errors should return the same usage/help string as runtime contract
  - bridge failure path: when bridge returns `ok=False`, return standard error message and no brittle formatting assumptions
- Use a lightweight in-test bridge mock for stable routing assertions and avoid flake from live state.
- Keep a concise fixture (policy-like payload with minimal keys) and assert only contract-critical text.
- Important schema lesson from this rollout: expected metric shape must match runtime payload exactly (for example, `false_positive['total']` is an `int`, not a nested object), and test fixtures should be adjusted to prevent false regressions.
- Evidence in this run:
-  - added `test_hermes_os_metrics_command_path_contract.py` (3 tests)
  - `3 passed` for file-level metric-path contract
  - `54 passed` for full v3 suite after integrating metrics command-path tests
  - LEARNING_DATABASE updated with Option 5 milestone and evidence block

### Phase C+ Option 6 Status + Apply Guard Contract Pattern (Integration-First)

- After metrics contract hardening, bind `policy-report` to the operator-visible `status/readiness` card path in the same command surface and keep runtime behavior unchanged unless `apply` explicitly approved.
- Add integration command-path coverage for:
  - `handle_command('hermes-os', 'status')` showing latest candidate + policy report summary + readiness state
  - `handle_command('hermes-os', 'status readiness')` where available, with explicit card rendering for policy_report and readiness signal notes
  - `handle_command('hermes-os', 'apply <candidate_id> <auto_token>')` hard-guards on readiness before applying
  - no-argument/error paths with stable usage copy and no brittle route-specific dependencies
- In apply path, enforce: readiness evaluation always runs and failure returns standardized **Apply approval checklist** block instead of blind apply.
- Add deterministic candidate lookup helper for the latest candidate id to avoid flaky selection in status/card rendering.
- Keep all checks on the command surface (integration layer) so runtime policy core remains stable unless explicit apply pass.
- Evidence in this run:
  - Added/updated `skills/hermes-os/v3/test_status_readiness_policy_apply_contract.py` (4 tests)
  - Updated `test_readiness_command_path_contract.py` to include readiness/checklist golden expectation alignment
  - `4 passed` for Option 6 new file + `58 passed` for full v3 suite
  - `policy_report` now included in status card output and apply guard messaging with checklist
  - LEARNING_DATABASE `Next Action` and Option 6 milestone updated

### Trial-and-error hardening lessons captured

- A test-path typo (`test_analyzer.py` absent from wrong cwd) caused a false-negative test failure; fixed by running suite with explicit `skills/hermes-os/v3/...` paths from project root and with `PYTHONPATH`.
- Adding assertions for `policy_report` first (RED) exposed a real contract gap (`KeyError: policy_report`) even though readiness logic passed; fix was to emit `policy_report` on every readiness path (not-found, insufficient samples, reasoned-fail, and pass) for stable downstream rendering.
- Keep module path discipline (`PYTHONPATH=$HOME/.hermes/skills/hermes-os:$HOME/.hermes/os`) as a hard requirement for runtime smoke and pytest in this environment.
- A broad automated text replacement intended to rewrite slash-commands accidentally introduced `IndentationError` in integration skill; immediate rollback to backup and `py_compile` verification is mandatory before continuing after any broad text edits.
- `LEARNING_DATABASE.md` block updates can fail with brittle exact-string replacement when duplicated sections/line endings differ; safer pattern is marker-based replacement around headings (for example replace between `### Runtime Verification` and `### Next Action`) to avoid partial mismatch.

### Phase D+D? Offline Replay + Phase E Guarded Auto-Tune Contract Pattern

- After Option 6 (status/apply guard), complete remaining rollout safely in two command-first phases:
  1. **Phase D (Offline Replay):** add replay-evaluation flow that simulates historical route decisions before policy acceptance.
  2. **Phase E (Guarded Auto-Tune):** add proposed auto-tune path that is *readiness-only* until operator approval is explicit.

#### Phase D execution recipe (reusable)

- Implement replay helper pipeline in runtime (`hermes_os.py`) with deterministic fallback behavior:
  - `evaluate_learning_policy_candidates(...)` should score candidates and return candidate-level mismatches with route alias normalization.
  - `_iter_telemetry_events` / history reader must tolerate malformed JSON lines and missing keys.
  - `_simulate_execution_route_for_policy(...)` should preserve existing route contract names and metadata shape.
- Add readiness reason gates that block unsafe proposals even with high total sample volume:
  - recent window drift (`offline_replay_recent_drift_risk`)
  - confidence bounds (`offline_replay_confidence_low`)
  - seasonal flip deltas (`offline_replay_seasonal_shift_risk`)
  - per-route sparsity (`offline_replay_route_sparsity_risk`)
- Emit replay summary into `policy_report` every path so downstream card renderers remain stable on pass/fail/insufficient cases.
- Add dedicated contract tests for each guard reason and a passing-replay scenario.

#### Phase E execution recipe (reusable)

- Add `propose_guarded_auto_tune(...)` entrypoint and command path binding in integration layer:
  - `handle_command("hermes-os", "tune")`
  - `handle_command("hermes-os", "replay <task_count>")`
  - `handle_command("hermes-os", "health")`
- Keep all auto-tune in *proposal mode* unless approval is present (`/apply` with auto token) and readiness gate still passes at apply time.
- Extend status/readiness cards to surface:
  - `health` metrics
  - `acceptance_passed` / `failed_signals`
  - reason codes above when blocked
- Add command-path tests in `test_status_readiness_policy_apply_contract.py` and `test_readiness_command_path_contract.py` before touching core behavior.

#### Verification pattern that reduced regressions in this rollout

1. Run `py_compile` on changed files immediately after edits.
2. Run focused contract suites first (v3 command-path + phase-specific), then larger smoke bundles.
3. Record exact command + pass count in LEARNING_DATABASE right away (not just in chat).
4. Add fact_store evidence for milestones with immutable IDs to preserve continuity.
5. Keep safety contracts unchanged unless a specific Option explicitly authorizes behavior changes.

#### One hard-won lesson from this round

- LEARNING_DATABASE/markdown evidence is part of required contract, not a cleanup item: always update it in the same iteration as feature + test evidence, and verify the written block exists before handoff.
- Keep module path discipline (`PYTHONPATH=$HOME/.hermes/skills/hermes-os:$HOME/.hermes/os`) as a hard requirement for runtime smoke and pytest in this environment.

### Option 7 (Pilot-safe Control Plane Loop + Auto-Run Readiness)

This project has now reached a pilot-safe control-plane state (manual-assisted):

- Added `hermes-os auto-run` command surface with:
  - `status`
  - `set`
  - `run`
  - `loop [limit] [min_samples] [force]`
- Added core loop method + gating in `hermes_os.py`:
  - evaluates `auto_run_mode`, `kill_switch`, and `cooldown`
  - supports operator override via `force` in manual-trigger path
  - returns idempotency/cycle metadata (`cycle_id`, `last_cycle_at`, decision/trigger summary)
- Added integration path via Telegram bridge proxy so command handling remains `handle_command("hermes-os", "...")`-first.
- Added contract tests for both success and blocked loop execution in:
  - `test_status_readiness_policy_apply_contract.py`

Current guard status (evidence-backed):

- `~/.hermes/skills/hermes-os/v3` full suite: **66 passed** under `PYTHONPATH=/home/hanuman3310/.hermes/skills/hermes-os:/home/hanuman3310/.hermes/os` + venv python.
- `~/.hermes/database/hermes-os-learning/LEARNING_DATABASE.md` Runtime Verification updated to include Option 7 loop path + Next Action.
- fact trail appended (fact ids) for Option 7 path and loop gating evidence.

### Option 7 practical rollout checklist (from this implementation)

Recommended next step before true scheduler rollout:

1. Add/verify operator-auth / role gating for control commands (especially `auto-run` state changes).
2. Add scheduler/daemon trigger for `hermes-os auto-run loop` with `mode=pilot` first, then explicit `auto` approval.
3. Add replay/health/tune loop cadence policy (`canary`, `cooldown`, `max_daily_change`, rollback trigger).
4. Add idempotency/ledger checks for repeated cycles and emergency stop-path behavior (`kill_switch`, `revert`), plus rollback evidence entries in LEARNING DB/fact_store.
5. Add contract tests for scheduled invocation and blocked reason surfacing (`mode_off`, `killswitch`, `cooldown`, `insufficient-data`).
6. Keep `apply` as manual approval while pilot is active; promote only after repeated dry-runs pass safety checks and policy drift/rollout metrics remain bounded.

#### Command/verification pattern used for this round

- Keep loop development integration-first: bridge/skill command contract first, then core loop logic.
- Use marker-based markdown updates in `LEARNING_DATABASE.md` (`### Runtime Verification` → `### Next Action`) to avoid brittle exact-line replacements.
- Always run:
  - `py_compile` on changed files
  - targeted/then full v3 contract pytest
  - evidence updates before any scheduler enablement.

#### Option 7 pilot scheduler activation runbook (field-tested)

When user says “continue now” and approval is implicit, use this deterministic sequence:

1. **Create trigger script first**
   - Add `~/.hermes/scripts/hermes_os_auto_run_loop.py` with:
     - explicit import path bootstrap (`~/.hermes/skills/hermes-os` + `~/.hermes/os`)
     - mode gate via `HERMES_OS_EXPECTED_MODE` against `~/.hermes/state/hermes-os.json`
     - JSON stdout result for scheduler/audit tooling
2. **Run blocked-path smoke before mode switch**
   - Execute script once while mode still `off` and confirm blocked reason `mode_off` (expected-safe behavior).
3. **Set auto-run mode to `pilot`**
   - Use bridge/core API (`set_auto_run_mode`) and verify status payload fields update.
4. **Run success-path smoke**
   - Execute script again and confirm `ok=true` with loop decision payload (typically `pilot_recommend`).
5. **Create cron only after smoke passes**
   - Create local-delivery cron with conservative cadence (e.g. `*/15 * * * *`) and self-contained prompt.
   - Immediately `list` to confirm `job_id`, `enabled=true`, `state=scheduled`.
6. **Re-verify full contract suite and evidence**
   - run full v3 pytest, then update LEARNING + fact trail in same round.

Observed pitfall and fix from this run:
- `gate_state.cooldown_minutes` was incorrectly populated using seconds helper. Rename to `cooldown_seconds` (or compute true minutes) to avoid operator/audit confusion.
#### Failure-handling notes discovered in this rollout

- Some `patch` operations failed with context mismatch (`hunk ... not found` / identical strings). In those cases, use deterministic scripted text rewrite with boundary-anchored replacements, then immediately rerun compile/test.
- Do not run git commands from non-repo directories; use `git -C <repo>` once repo root is confirmed.
- Cron monitor jobs created with `deliver=local` may not produce an output file immediately when manually triggered. Validate with `cronjob list` (`last_run_at`/`last_status`) and re-check `~/.hermes/cron/output/<job_id>/` after scheduler tick instead of assuming failure.

#### Option 7 pilot scheduler + monitor evidence protocol (reusable)

When Boss says “continue” after Option 7 control-plane is live, use this exact sequence:

1. **Baseline state check first**
   - read `~/.hermes/state/hermes_os_auto_run_state.json`
   - read `~/.hermes/state/hermes_os_auto_run_ledger.jsonl`
   - verify `mode`, `kill_switch`, `last_cycle_*`
2. **Prove gate behavior before promotion**
   - verify at least one blocked scheduler cycle with `reason=cooldown_not_elapsed` from cron output for loop job
   - blocked-by-cooldown in pilot mode is positive safety evidence, not a failure
3. **Add monitor script + monitor cron**
   - script should emit JSON snapshot (mode, kill_switch, cooldown remaining, next_cycle_at, decision/risk mix)
   - keep monitor read-only (never mutate mode or kill-switch)
4. **Contract revalidation after scheduling changes**
   - run `py_compile` on changed runtime/integration/script files
   - run full v3 contracts (`pytest -q ~/.hermes/skills/hermes-os/v3`) and require pass before status claims
5. **Readiness decision rule for daemon promotion**
   - if evidence window is still small (few recent cycles), keep recommendation at pilot and log `HOLD`
   - promote to full-auto daemon only after repeated scheduler cycles show stable gate decisions and no unsafe trigger patterns
6. **Evidence hygiene**
   - append LEARNING_DATABASE with latest pilot snapshot and explicit Go/Hold recommendation
   - add fact_store entry for each milestone (scheduler added, monitor added, latest promote snapshot)

#### Option 7 Scheduler + Monitor operational notes (new)

- Use two separate cron jobs for safer rollout:
  1) loop trigger job (`*/15 * * * *`, local delivery) that runs `hermes_os_auto_run_loop.py`
  2) monitor job (`5 * * * *`, local delivery) that reads state+ledger and emits JSON health snapshot
- Keep loop script mode-safe:
  - gate on `HERMES_OS_EXPECTED_MODE=hermes_os`
  - return `ok=false, blocked=true` (not crash) when mode mismatches or Hermes OS is off.
- Before enabling scheduled loop, run one manual smoke in `pilot` mode and confirm expected blocked/allowed transitions:
  - blocked reason example: `mode_off` or `cooldown_not_elapsed`
  - allowed example returns `decision=pilot_recommend` with `action=loop`.
- Normalize gating payload keys carefully: cooldown returned from helper is in seconds, so use `cooldown_seconds` (not `cooldown_minutes`) in gate-state payload to avoid audit confusion.
- Cron evidence retrieval tip: verify run output under `~/.hermes/cron/output/<job_id>/...`; a newly created job may show `last_status=ok` before output file appears due to asynchronous write timing.

#### Option 7 Promote-Gate automation pattern (new)

When Boss asks to "continue" beyond pilot, add a deterministic promote decision layer before any daemon/full-auto promotion:

1. Create `hermes_os_auto_run_promote_gate.py` that computes **GO/HOLD** from explicit criteria, not free-text judgment.
2. Recommended criteria set:
   - `mode_is_pilot`
   - `kill_switch_off`
   - `sufficient_recent_runs` (e.g., `min_runs=6`)
   - `no_unsafe_reasons`
   - `no_run_errors`
   - `has_successful_scheduled_cycle` (`ok_count >= 1`)
3. Parse loop-cron evidence from `~/.hermes/cron/output/<loop_job_id>/*.md` and runtime state from `~/.hermes/state/hermes_os_auto_run_state.json`.
4. Add robust markdown parsing fallbacks:
   - status may appear as inline bold (`**Status:** blocked`) OR table (`| **Status** | BLOCKED |`)
   - reason extraction should prefer known tokens (`cooldown_not_elapsed`, `mode_off`, `mode_mismatch`, `kill_switch`) to avoid false positives from generic wording.
5. Add a dedicated promote-gate cron (local delivery), e.g. hourly, separate from loop and monitor jobs.
6. Promotion rule from this rollout:
   - if cycles are safe but sample count below threshold -> **HOLD** (do not promote)
   - if recent runs are all `blocked` (for example `cooldown_not_elapsed`) and `ok_count=0` -> **HOLD** (avoid false GO)
   - only emit **GO** when all criteria pass for the configured evidence window, including at least one successful scheduled cycle.

### Promote-gate triage lesson from this session

A common failure mode is **passing the new `has_successful_scheduled_cycle` gate while still holding because of an unsafe reason**.
In this session:
- early promote-gate runs were held because `recent_run_count` was below threshold or `ok_count=0`
- later, after `ok_count >= 1`, the gate still returned **HOLD** because `unsafe_reasons` contained `kill_switch`

So the troubleshooting order should be:
1. Verify the most recent promote-gate decision card.
2. Check whether `has_successful_scheduled_cycle` is the blocker or already satisfied.
3. Inspect `unsafe_reasons` separately from sample-count criteria.
4. If `kill_switch` appears, do not treat the result as a sample-size problem.
5. Cross-check the latest loop-cron evidence in `~/.hermes/cron/output/<job_id>/` to confirm whether the successful cycle was actually present or whether the block came from cooldown-only runs.

This reduces subjective promotion decisions and makes pilot→daemon transition auditable/replayable.

### Practical hardening add-on (applicable for Option/Phase rollover)


When finishing a rollout chunk (e.g., end of Option/Phase), always run this deterministic closure sequence before waiting for next instruction:

1. **Contract-first revalidation scope:**
   - Run the *focused* contract suites first (newly touched command-path / readiness / apply tests).
   - Then run the full v3 suite with the required runtime env to confirm no collateral regressions.
   - Example:
     - `cd ~/.hermes/skills/hermes-os/v3 && PYTHONPATH=$HOME/.hermes/skills/hermes-os:$HOME/.hermes/os ~/.hermes/hermes-agent/venv/bin/python3 -m pytest -q`
2. **Evidence first, code second:**
   - Update `LEARNING_DATABASE.md` immediately after tests, including exact command + pass count and changed runtime outputs.
   - Include runtime smoke checkpoints that were executed (e.g., `capture_routing_feedback`, command-path smoke for `metrics`/`replay`/`health`/`tune`).
3. **Durable fact trail:**
   - Add/update `fact_store` entries for milestone, test counts, and audit-log updates so continuity survives context reset.
4. **Recovery-safe markdown edits:**
   - For brittle LEARNING blocks, use marker-based replacement (`### Runtime Verification` to `### Next Action`) instead of exact one-line replacement.
5. **Repo context discipline:**
   - If `git` commands fail with `fatal: not a git repository`, discover actual repo roots first (e.g., `search_files` for `.git`) and run status/commit from the correct root only.

This pattern reduced context-related ambiguity and prevented release-readiness gaps after D/E closure.
### Mapping and command-hygiene lessons for Phase B

- Keep user-facing runtime command names aligned with project guidance (no leading slash in internal command intent when required).
- Preserve path compatibility for ambiguous route names:
  - user contract route labels expected: `direct`, `direct_with_suggestion`, `fleet`
  - existing legacy execution route names still map via adapter (`hermes_direct`, `fleet_complex`).
- For `expected_route`, ensure canonical mapping for feedback suggestions is explicit (`should_direct` -> `hermes_direct`, `should_fleet` -> `fleet_complex`) so false-positive metrics are truthful.

### Backup and change control additions for feedback work

- Backup risky files before edits in a versioned folder (e.g. `~/.hermes/backups/hermes-os-phase3-feedback/`).
- Change routing/telemetry runtime logic in small increments per candidate field/value.
- If an edit fails or creates uncertain behavior, stop immediately, revert to safe state, and request approval before proceeding.

### Manual-learning mode switch (disable autonomous learning loops)

When Boss requires **operator-triggered learning only** (no autonomous loop), apply this exact compatibility-safe sequence:

1. **Add a dedicated manual command path** in integration skill:
   - command: `hermes-learning`
   - subcommands:
     - `hermes-learning status`
     - `hermes-learning run [limit] [min_samples]`
   - manual run should pass explicit provenance metadata (for audit), e.g. `actor="operator"`, `source="hermes-learning-command"`.
2. **Deprecate, do not hard-delete**, old auto-run command entrypoints:
   - keep legacy `hermes-os auto-run run` callable but return deprecation guidance to `hermes-learning run`.
   - block autonomous loop triggers (`loop`, `set auto/pilot`) if policy requires manual-only behavior.
3. **Scheduler enforcement (critical):**
   - pause existing Hermes OS auto-run cron jobs (`loop`, `monitor`, `promote-gate`) so behavior matches policy immediately.
   - verify by `cronjob list`: jobs must be `state=paused`, `enabled=false`.
4. **Regression safety checks:**
   - run focused command-path/contract tests for changed integration surfaces.
   - if full suite cannot run due to environment import-path constraints, report that gap explicitly and avoid claiming full regression completion.
5. **Known pitfall from field evidence:**
   - promote-gate parsers that scan entire markdown for reason tokens can raise false `unsafe_reasons` (e.g. `kill_switch`) from informational tables.
   - parse structured status/reason fields first (status line/table extraction) before token fallback, or gate token matching to reason-specific sections.

This pattern allows immediate policy compliance (manual-only learning) without destabilizing runtime contracts.

6. **Operator UX truth-check after cutover:**
   - verify `hermes-learning` (no args) returns the manual usage card and does not execute a cycle.
   - verify `hermes-learning status` reflects control-plane state and explicitly shows operator-triggered control.
   - if status still reports `Auto mode: pilot` after policy switch, set `hermes-os auto-run set off` to avoid operator confusion between control-plane mode text and manual-only command policy.
