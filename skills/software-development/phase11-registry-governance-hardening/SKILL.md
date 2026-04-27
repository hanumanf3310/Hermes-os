---
name: phase11-registry-governance-hardening
description: Reusable workflow for adding skill-registry governance features in Hermes-style fleets.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
      - registry
      - cli
      - audit
      - policy-packs
      - lifecycle
      - tests
      - compatibility
      - phase11
    related_skills:
      - phase10-knowledge-integration
      - skills-lifecycle-cli-ops
      - test-driven-development
      - systematic-debugging
---

# Phase 11 Registry Governance Hardening

Use this skill when extending a registry-backed skill system with:
- lifecycle CLI commands (`list`, `remove`, `deactivate`, `reactivate`)
- deterministic audit logging for registry actions
- service-specific policy metadata attached to context and adapter plans
- tests that must stay backward compatible with existing resolver and execution behavior

## When to Use
- The registry already loads manifests and resolves skills, but operators cannot manage lifecycle state cleanly.
- You need auditable registry actions without changing runtime routing semantics.
- You want richer service guardrails or policy metadata to flow through the knowledge package.
- Existing tests are flaky due to isolation issues, hidden state, or CLI subprocess boundaries.

## Core Approach
Prefer a narrow, compatibility-preserving sequence:

1. Inspect the implementation plan and current tests.
2. Write failing tests first.
3. Implement the smallest compatible change.
4. Add deterministic audit logging.
5. Propagate service policy packs through the knowledge layer.
6. Verify in layers: targeted tests, integration tests, full suite.
7. Update docs after verification.

## Registry Lifecycle Pattern

### Loading behavior
- Load manifests from the registry directory.
- Keep disabled manifests available for lifecycle operations.
- Keep disabled manifests non-selectable in resolver scoring.

### CLI commands to support
- `list-skills`
- `remove-skill --skill-id ...`
- `deactivate-skill --skill-id ...`
- `reactivate-skill --skill-id ...`

### Output conventions
- `list-skills` should return `status`, `count`, and `skills`.
- lifecycle commands should return `status`, the affected `skill` or `removed` manifest, and `NOT_FOUND` when appropriate.

## Audit Trail Pattern

### What to record
- `action`
- `skill_id`
- `status`
- `details` with deterministic structured fields

### Helpful actions
- `validate-skill`
- `register-skill`
- `deactivate-skill`
- `reactivate-skill`
- `remove-skill`

### Good practice
- Write audit entries from the registry layer, not only the CLI layer.
- Use a CLI flag to override the audit path so tests can isolate output.
- Provide a summary helper that can be asserted deterministically.

## Service Policy Pack Pattern

Use a shared policy pack helper when task context should carry service guardrails.

Recommended services:
- `calendar`
- `gmail`
- `drive`
- `docs`
- `sheets`
- `contacts`

Attach policy packs to:
- `ResolvedContext`
- service adapter plan payloads

Typical metadata:
- `service`
- `guardrails`
- service-specific read/write targets or mailbox/range/page_size
- token source or execution source hints

## TDD Workflow

### 1) Write the failing tests
Include coverage for:
- CLI lifecycle behavior
- audit log entries
- policy pack propagation
- resolver stability after lifecycle changes

### 2) Verify failure is real
Make sure failures come from missing behavior, not import-path mistakes or bad test setup.

### 3) Implement narrowly
- If a feature is purely metadata, avoid changing execution semantics.
- If a feature needs persistence, keep file writes small and deterministic.

### 4) Run targeted tests, then full suite
Use this order:
- new tests for the task
- affected phase 10/11 tests
- full suite

## Common Pitfalls
- Forgetting that disabled manifests should still be loadable for lifecycle operations.
- Changing resolver scoring when the task only needs CLI or metadata support.
- Omitting audit-path injection, which makes CLI tests write to shared state.
- Attaching policy packs only in the adapter or only in context, instead of both.
- Test imports failing because `integrations` is not on `sys.path` in standalone test files.
- Treating `list-skills` as a pure internal helper instead of a user-visible CLI surface.

## Verification Checklist
- [ ] Lifecycle CLI commands work
- [ ] Registry audit entries are deterministic
- [ ] Policy packs flow through context and adapters
- [ ] Resolver behavior remains backward compatible
- [ ] Targeted tests pass
- [ ] Full suite passes
- [ ] Roadmap/changelog match actual implementation

## Example Outcome
After applying this workflow, the registry can:
- list active skills
- deactivate and reactivate entries without losing manifests
- remove manifests cleanly
- record auditable lifecycle history
- carry service guardrails into the knowledge package

All without breaking the existing registry-first resolution flow.
