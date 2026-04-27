---
name: phase10-knowledge-integration
description: Reusable workflow for implementing a knowledge / skill / fact / memory integration layer with service adapters, executor wiring, and TDD verification.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [integration, architecture, tdd, service-adapters, orchestration, google-me, boss-calendar]
    related_skills: [test-driven-development, systematic-debugging, writing-plans, enterprise-testing-framework]
---

# Phase 10 Knowledge / Skill / Fact / Memory Integration

Use this skill when adding a reusable integration layer that connects intent routing, skill resolution, context/fact/memory resolution, service adapters, and a real executor path.

## When to Use
- A system already has skills/facts/memory or similar knowledge sources, but they are not wired into runtime execution.
- You need a clean bridge from natural-language intent to concrete service commands.
- Service-specific behavior must remain modular and testable.
- Calendar/Gmail/Drive/Docs/Sheets-style integrations need per-service adapters.

## Core Architecture
Prefer this chain:

1. **Intent Router**
   - Classify task text into a normalized intent category.
## Core Architecture
Prefer this chain:

1. **Intent Router**
   - Classify task text into a normalized intent category.
2. **Skill Registry**
   - Load skill manifests from a registry directory as the source of truth.
3. **Skill Collision / Validation Gate**
   - Validate manifest schema before registration and detect duplicate/near-duplicate skills before accepting them.
4. **Skill Resolver**
   - Map intent → best matching skill profile from the registry, with legacy fallback when needed.
5. **Context Resolver**
   - Collect and normalize facts, memory, constraints, and observations.
6. **Service Adapter Resolver**
   - Map service → adapter that creates a service plan.
7. **Execution Bridge / Executor**
   - Run the service plan through a real executor or fallback path.
8. **QA / Completeness Gate**
   - Preserve safety and completeness checks before delivery.

## Registry Workflow
When adding a new skill in Phase 10, use this order:

1. Create or update the skill manifest.
2. Run schema validation (`validate-skill`).
3. Run collision detection against existing skills.
4. Register/persist only if the manifest is valid and non-conflicting.
5. Let `SkillResolver` discover the skill at runtime.

This pattern keeps new skills discoverable without hardcoding them into the resolver and prevents collisions from silently changing routing behavior.

## Skill Discovery Pattern

When adding new skills, prefer registry-driven discovery over hardcoded `if category == ...` branches.

### Recommended manifest fields
- `skill_id`
- `name`
- `service`
- `command`
- `intent_categories`
- `triggers`
- `guardrails`
- `read_targets`
- `write_targets`
- `enabled`
- `priority`

### Resolver behavior
- First, let the intent router classify the request.
- Then query the skill registry for candidates.
- Rank candidates by exact intent match, keyword overlap, service match, and priority.
- Return a concrete `SkillProfile` when confident.
- If no candidate matches, apply **narrow compatibility fallback** only where explicitly allowed.
- If the registry already supports a category/service, **do not** bypass it with legacy fallback.
- If a category is unknown or unsupported, fall back to the existing generic routing path rather than inventing a skill.

### Phase 11 hardening rule (registry-first fallback narrowing)
Use this when migrating from hardcoded routing to manifest-driven skill resolution:

1. Add a registry capability check (e.g., `supports_category(category)`).
2. Keep a small compatibility allowlist for legacy fallback only (example set used in implementation: `calendar`, `gmail`, `drive`, `docs`, `sheets`, `contacts`).
3. Resolver order should be:
   - registry best match first,
   - if no match and category is on compatibility allowlist **and** registry does not support that category, then legacy fallback,
   - otherwise generic fallback.
4. Add tests that explicitly cover:
   - registry precedence over legacy,
   - compatibility fallback allowed only in allowed categories,
   - no fallback for unknown/non-compat categories.

### Design rule
A new skill should become usable by adding metadata/manifest, not by editing multiple routing branches.

## Recommended File Split
- `knowledge_models.py`
  - Shared dataclasses for intent, skill, resolved context, and execution plan.
- `knowledge_router.py`
  - Intent classification.
- `skill_resolver.py`
  - Intent → skill mapping.
- `context_resolver.py`
  - Normalize facts, memory, and constraints.
- `service_adapters.py`
  - Service-specific plans for calendar, gmail, drive, docs, sheets, contacts.
- `service_executor.py`
  - Real execution path for service plans.
- `knowledge_integration_layer.py`
  - Top-level orchestration API that assembles the package.

## TDD Workflow
Always add tests before code.

### 1) Write tests for the desired behavior
Cover:
- intent classification
- skill resolution
- context resolution
- service adapter output
- executor wiring
- Hermes/Fleet propagation of knowledge context

### 2) Run tests and confirm they fail
Ensure the failure is due to missing behavior, not import errors from a bad test setup.

### 3) Implement the smallest code to pass
Keep each module focused.

### 4) Run the specific tests, then the full suite
Verify:
- the new tests pass
- no regression in existing phases

## Practical Patterns That Worked Well

### Separate service plan from execution plan
Do not reuse the generic execution plan as the service plan.
A service adapter should emit the real service command payload, and the executor should run that payload.

### Carry knowledge through Hermes, not just Fleet
If the knowledge layer is only called inside Fleet, the flow can still fall back to generic routing.
Build the knowledge package in Hermes, then pass it through to Fleet.

### Keep dry-run and live execution separate
- **dry-run**: return the knowledge/service plan only
- **live**: call the executor and attach the service execution result

### Preserve safety fallbacks
If a task is not skill-matched or the executor is unavailable, fall back to the existing orchestrator path rather than inventing a result.

## Operational Findings From Implementation

### Real Google ME command mapping
The local executor path uses `~/.hermes/google_me/google_me.py` with known commands:
- `gmail-summary`
- `gmail-today`
- `calendar-today`

For Google Workspace services that are not exposed in `google_me.py`, use direct API-backed execution in the executor layer.

### Service adapters should be per-service, not shared
Docs, Sheets, and Contacts needed separate adapters because a generic workspace adapter hid service-specific payload differences:
- Docs: `document_id` / `doc_id`
- Sheets: `spreadsheet_id` / `sheet_id` + `range`
- Contacts: `page_size`

### Service policy packs should travel through both context and adapter layers
When a service has explicit guardrails, attach a deterministic `policy_pack` to both:
- `ResolvedContext` so the orchestration layer can reason about guardrails
- the service adapter plan so execution has the same policy metadata

Keep these packs small, service-specific, and derived from a shared map rather than copied into multiple modules.

### Registry lifecycle changes should be auditable
For skill lifecycle operations, use a JSONL audit trail with deterministic entries for:
- `validate-skill`
- `register-skill`
- `deactivate-skill`
- `reactivate-skill`
- `remove-skill`

Expose an overrideable audit path in the CLI so tests can isolate logs without changing production defaults.

### Benchmark harnesses should be fixture-backed and deterministic
### Service adapters should be per-service, not shared
Docs, Sheets, and Contacts needed separate adapters because a generic workspace adapter hid service-specific payload differences:
- Docs: `document_id` / `doc_id`
- Sheets: `spreadsheet_id` / `sheet_id` + `range`
- Contacts: `page_size`

### Service policy packs should flow through both context and adapter layers
When a service needs guardrails, attach a shared policy pack in two places:
- the resolved context (`ResolvedContext.policy_pack`)
- the service adapter plan (`policy_pack` on the adapter output)

This keeps the policy visible to routing/execution code and to downstream service-specific behavior. Use a small shared map keyed by service name, then enrich it with task context (for example `document_id`, `sheet_id`, `range`, or `page_size`) inside the adapter or context resolver.

### Router keyword collisions matter
Broad keywords such as `document`, `docs`, or `ตาราง` can collide with Drive/Sheets/Calendar routing.
Tighten keywords when a more specific service starts getting misclassified.

### Skill registry should validate before registration
Use a registry-backed resolver when skill counts grow, but validate every new manifest first.
Minimum checks:
- required fields present (`skill_id`, `name`, `service`, `command`)
- `intent_categories` and `triggers` are non-empty lists
- `priority` is a non-negative integer
- `enabled` is boolean

### Collision detection should run before acceptance
Before adding a new manifest, compare it with existing skills for:
- exact `skill_id`, `name`, or `command` match
- same service + overlapping intent categories
- trigger overlap that could shadow an older skill

Recommended outcomes:
- `OK` → safe to register
- `WARNING` → review scope/priority
- `CONFLICT` → reject and rename or split scope

### Registry lifecycle should persist and audit changes deterministically
For lifecycle commands (`list`, `deactivate`, `reactivate`, `remove`), keep the registry as the source of truth and write changes back to the manifest file when possible.
A reusable pattern is:
- `list-skills` returns enabled skills by default, with an opt-in flag for disabled ones
- `set_enabled(skill_id, enabled)` toggles state and reloads the registry
- `remove_manifest(skill_id)` deletes the manifest file and prunes in-memory state
- every lifecycle action writes a JSONL audit entry with `action`, `skill_id`, `status`, and structured details

### CLI registration path
A small CLI command is useful for the registry workflow:
- `validate-skill` to load manifest JSON and validate schema only
- `register-skill` to validate, run collision checks, then persist
- keep registration and validation on the same registry-backed source of truth
- future lifecycle commands (`list`, `update`, `deactivate`, `remove`) should use the same registry and must not bypass validation/collision gates

### Routing hardening lesson
When the resolver gets a broad synonym wrong, tighten the keyword set before widening fallback behavior.

A real example from implementation: a calendar keyword that was too broad (`ตาราง`) caused misrouting with sheet/table-related prompts and surfaced as an unrelated adapter failure. The fix was to remove the ambiguous keyword, add/adjust synonyms more carefully, and validate the change with cross-service ambiguity tests.

### Deterministic benchmark harness pattern
When adding routing/skill-selection benchmarks, use a fixed JSON fixture and a pure Python runner that returns a stable report object.
Good benchmark outputs include:
- routing accuracy
- skill selection accuracy
- fallback rate
- total case count

Keep the benchmark deterministic:
- no random sampling
- no live external service calls
- same fixture in, same report out

### Executor payload should carry the service plan
Do not pass the generic knowledge execution object to the executor if the real executor expects service-specific fields.
Pass the adapter-produced service plan instead.

### Useful verification command set
Run specific tests first, then the full suite:
- `pytest tests/test_phase10_*.py -q --tb=short`
- `pytest tests/ -q --tb=short`

## Service-Specific Notes

### Calendar
Use a dedicated calendar adapter when the intent is schedule/timeline related.
For Boss-style calendar behavior, keep these rules:
- read all 3 calendars
- write/edit/delete only in `ปฏิทินงาน Line`
- preserve source transparency in output
- format chronologically

### Google ME / Gmail
Use the unified Google ME path when the service is Gmail or general Google Workspace.
Prefer known commands like:
- `gmail-summary`
- `gmail-today`
- `calendar-today`

### Drive
If a direct command is not exposed, a direct API-backed executor may be needed.
Keep the executor implementation isolated so other services do not depend on it.

## Common Pitfalls
- Routing skill-first tasks into generic fallback safety blocks.
- Treating service adapter output and execution result as the same thing.
- Forgetting to pass knowledge context through the orchestrator boundary.
- Returning fabricated data instead of a real executor result.
- Making one giant adapter instead of per-service adapters.
- Forgetting QA/completeness gates after integration.

## Verification Checklist
- [ ] Intent routing tests pass
- [ ] Skill resolver tests pass
- [ ] Service adapter tests pass
- [ ] Executor tests pass
- [ ] Hermes/Fleet integration tests pass
- [ ] Full suite passes
- [ ] No fabricated output is introduced

## Example Task Flow
1. User says: “ดูตารางงานเดือนหน้า”
2. Intent router classifies as calendar
3. Skill resolver selects `boss-calendar`
4. Context resolver injects facts/memory and calendar rules
5. Calendar adapter emits a Boss calendar plan
6. Executor runs the plan or returns a dry-run preview
7. Hermes/Fleet returns a structured result with the service execution attached

## Notes
This skill is meant to be reused whenever runtime knowledge integration needs to be added in a modular, testable way.
