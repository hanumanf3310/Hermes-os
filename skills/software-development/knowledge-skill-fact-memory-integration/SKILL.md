---
name: knowledge-skill-fact-memory-integration
description: Pattern for adding a reusable Phase 10-style integration layer that maps intent to skills, resolves facts/memory context, adapts data formats, and wires the result into an existing orchestrator without breaking the legacy routing path.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [integration, orchestration, skills, memory, fact_store, adapters, routing, qa]
---

# Knowledge / Skill / Fact / Memory Integration Layer

Use this when a system already has:
- a working orchestrator or router,
- reusable skills/tools,
- facts/memory/context stores,
- and you need to connect them into the execution flow.

This skill captures the Phase 10 pattern used in Enterprise Agent Fleet.

## Goal

Convert a natural-language task into a reusable execution package:
1. classify intent,
2. resolve the right skill,
3. merge facts + memory + task context,
4. adapt output/input formats,
5. produce an execution plan,
6. preserve compatibility with the legacy routing path,
7. keep QA/completeness gates in the flow.

## Boss shorthand and fact tiers

When Boss uses these labels, preserve them exactly in downstream routing and summaries:

- `Fact` = durable fact / reference / preference / rule to store and retrieve.
- `Fact +` = `Fact + Learning` — a fact that should also feed the learning loop, feedback, or policy update path.
- `Fact*` = high-impact fact that must be verified before use.
- `Fact+*` = both `Fact +` and `Fact*` at once; it should both feed learning and remain gated by verification before operational use.

Treat a change as `Fact*` if it can affect Hermes OS behavior directly or indirectly, including:
- core Hermes OS routing or runtime behavior,
- update/rollback safety,
- upstream Hermes Agent changes,
- external tool changes that Hermes OS depends on,
- any change that would require rework to restore prior working behavior.

If a task mixes durability and governance, store the fact and also tag the routing context so the learning/policy layer can distinguish `Fact`, `Fact +`, and `Fact*`.

## Recommended module split

Create small, testable modules instead of one large controller:
- `knowledge_models.py` — dataclasses for intent, skill, resolved context, execution plan
- `knowledge_router.py` — deterministic intent classification
- `skill_resolver.py` — intent → skill profile mapping
- `context_resolver.py` — normalize facts, memory, skills, constraints, observations
- `knowledge_data_adapter.py` — output formatting / service-specific transformation
- `knowledge_execution_bridge.py` — build the final plan for skill-first or fallback execution
- `knowledge_integration_layer.py` — top-level façade

## Implementation steps

### 1) Write tests first
Add tests for:
- intent classification,
- skill mapping,
- context merging,
- adapter formatting,
- orchestration integration,
- fallback behavior.

Verify the tests fail before writing code.

### 2) Define deterministic intent routing
Prefer explicit keyword + task_type routing over LLM inference.

Typical categories:
- calendar
- gmail
- drive
- docs
- sheets
- contacts
- general/fallback

### 3) Resolve skills from intent
Map each intent to a concrete skill profile:
- skill name
- service command
- read targets
- write targets
- guardrails

Keep this mapping declarative.

### 4) Resolve context from facts + memory
Normalize input context into a structured object.
Include:
- facts
- memory
- skill references
- constraints
- observations

Always dedupe and keep the result serializable.

### 5) Add a data adapter for output shape
Use adapters when a domain requires a specific format.
Examples:
- calendar display format with date grouping and source tags
- Gmail summary normalization
- Drive/Docs metadata extraction

Adapters should be deterministic and testable.

### 6) Build the execution bridge
Create a single execution plan object with:
- mode (`skill` or `fleet`)
- target
- command
- payload
- notes

If a skill is resolved, prefer skill-first execution.
If not, fall back to the legacy fleet/router path.

### 7) Wire into the orchestrator carefully
Inject the knowledge package into the existing context, not as a replacement.
Preserve old routing so unrelated tasks still work.

Good pattern:
- HermesOrchestrator prepares knowledge package
- FleetOrchestrator receives merged context
- task result includes knowledge details for transparency

### 8) Keep QA/completeness in the loop
For deliverables, ensure QA still sees:
- the knowledge package,
- the original route,
- the final output,
- any local completeness or placeholder audit results.

## Calendar-specific rules to preserve

If the task is calendar-related and the boss rules apply:
- read all required calendars,
- write/edit/delete only to the allowed work calendar,
- preserve source transparency in output,
- sort chronologically,
- respect all-day event conventions.

## Common pitfalls

- **Knowledge layer gets bypassed by legacy fallback**
  - Fix: add an explicit skill-first branch before generic routing/safety fallback.

- **Context is passed but not persisted in results**
  - Fix: include the knowledge package in returned task details.

- **Adapters become business logic**
  - Fix: keep adapters purely transformational.

- **Intent routing is too vague**
  - Fix: use deterministic keyword/task_type mapping first.

- **Calendar write rules are violated**
  - Fix: enforce read-targets vs write-targets in the skill resolver.

- **QA cannot see what the knowledge layer decided**
  - Fix: pass the resolved intent, skill, and context through the result payload.

- **Fact Store runtime supports schema fields in docs but not in the backend**
  - Fix: add explicit DB migration, normalize serialized list fields on read/write, and ensure tool APIs accept/return `fact_type`, `fact_star`, `fact_plus`, `verify_before_use`, `importance_level`, `star_reason`, `learning_policy_id`, and `verification_status`.

- **Fact* data renders like ordinary memory in dashboards**
  - Fix: add a dedicated `fact_star` node type/color, include the star fields in export payloads, and show a separate sidebar section for `Fact*` metadata.

- **Binary/JSON-like fields leak into UI serialization**
  - Fix: strip internal columns such as raw vector blobs before returning rows to the UI/API layer.

## Verification checklist

- [ ] New module imports succeed
- [ ] Intent routing returns stable categories
- [ ] Skill resolver returns the correct skill profile
- [ ] Context resolver dedupes and serializes data
- [ ] Adapter output matches the expected domain format
- [ ] Orchestrator includes knowledge in the returned task result
- [ ] Skill-first tasks do not fall through to incorrect generic routes
- [ ] Full test suite passes

## Example

A calendar query like:

`ดูตารางงานเดือนหน้ามีอะไรบ้าง`

should become:
- intent: `calendar`
- skill: `boss-calendar`
- context: merged facts + memory + constraints
- execution: `skill` mode
- adapter: boss-style calendar formatter
- output: source-aware, chronologically grouped

## When to update this skill

Update this skill if you discover a better pattern for:
- intent classification,
- context resolution,
- skill-first execution,
- adapter design,
- or preserving legacy compatibility while adding a new knowledge layer.
