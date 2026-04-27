---
name: fact-store-factstar-governance
description: Design, classify, and migrate Fact Store records for Hermes OS with explicit Fact / Fact+ / Fact* semantics, JSON Schema fields, verification gates, and safe backfill/migration planning.
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [fact-store, factstar, fact-plus, verification, schema, migration, hermes-os, governance]
---

# Fact Store Fact* Governance

Use this skill when Boss asks to:
- define or refine Fact / Fact+ / Fact* / Fact+* semantics,
- add schema fields to Fact Store,
- classify existing facts,
- design a migration/backfill plan,
- or wire Fact* / Fact+* into dashboard, memory, or learning flows.

## Core rule

- **Fact** = information to remember.
- **Fact+** = Fact + Learning.
- **Fact*** = information or a change that can affect Hermes OS directly or indirectly and must be verified before use.
- **Fact+*** = Fact+ and Fact* at the same time; it must both feed learning and pass verification before operational use.

Treat as `Fact*` anything that can alter:
- Hermes OS core behavior
- routing / orchestration
- safety / approvals
- rollback cost
- tool dependencies relied on by Hermes OS
- upstream core changes that may break prior working behavior

Treat as `Fact+*` when the item is both learning-relevant and operationally risky.

## Recommended fields

Use explicit fields instead of inferring importance from text alone.

Minimum useful schema:

```json
{
  "fact_type": "fact | fact_plus | fact_star | fact_plus_star",
  "fact_star": false,
  "fact_plus": false,
  "verify_before_use": false,
  "importance_level": "normal | important | critical",
  "star_reason": null
}
```

Recommended fuller schema:

```json
{
  "fact_id": 1,
  "content": "...",
  "category": "user_pref | policy | technical | project | learning | tool",
  "tags": ["..."],
  "source": "manual | system | imported | learned | inferred | unknown",
  "fact_type": "fact | fact_plus | fact_star",
  "fact_star": false,
  "fact_plus": false,
  "verify_before_use": false,
  "importance_level": "normal | important | critical",
  "star_reason": null,
  "learning_policy_id": null,
  "verified_by": null,
  "last_verified_at": null,
  "verification_status": "unverified | verified | needs_review | rejected",
  "trust_score": 0.5,
  "confidence_score": 0.5,
  "impact_scope": ["none"],
  "rollback_required": false,
  "related_entities": [],
  "created_at": "...",
  "updated_at": "...",
  "created_by": null,
  "updated_by": null,
  "notes": null
}
```

## Classification mapping

### Fact
Use when the item is only meant to be remembered.

Typical field set:
- `fact_type = "fact"`
- `fact_star = false`
- `fact_plus = false`
- `verify_before_use = false`
- `importance_level = "normal"`

### Fact+
Use when the item should also drive learning, trust updates, or policy adaptation.

Typical field set:
- `fact_type = "fact_plus"`
- `fact_plus = true`
- `fact_star = false`
- `learning_policy_id` set
- `importance_level = "important"` or `"critical"`

### Fact*
Use when the item can affect Hermes OS directly or indirectly and must be checked before use.

Typical field set:
- `fact_type = "fact_star"`
- `fact_star = true`
- `verify_before_use = true`
- `importance_level = "critical"`
- `star_reason` set
- `verification_status = "verified"` before promotion/use
- `rollback_required = true` when the change can break current behavior

### Fact+*
Use when both rules apply at once.

Typical field set:
- `fact_type = "fact_plus_star"`
- `fact_plus = true`
- `fact_star = true`
- `verify_before_use = true`
- `importance_level = "critical"`
- `star_reason` set
- `learning_policy_id` set
- `verification_status = "verified"` before promotion/use
- `rollback_required = true` when the change can break current behavior

## Decision rules

### Mark as Fact*
Mark as Fact* if the item could affect any of these:
- Hermes OS core
- routing or orchestration
- safety/approval boundaries
- rollback or recovery cost
- dashboard/workflow correctness
- tools Hermes OS depends on
- upstream Hermes Agent changes that may alter current behavior

### Mark as Fact+
Mark as Fact+ if the item is valuable to memory but should also update learning/trust/policy.

### Keep as Fact
Keep as Fact if it is primarily a remembered preference, note, or stable information item with no learning or safety implications.

## Schema migration workflow

### Phase 0: Inventory
- List existing records.
- Identify candidates for `fact_plus` or `fact_star`.
- Review content, tags, category, and trust.

### Phase 1: Backward-compatible schema expansion
- Add new fields as optional first.
- Ensure old records still load.
- Keep old read paths working.

### Phase 2: Backfill
- Classify existing records.
- Use conservative defaults if uncertain.
- Mark ambiguous records `needs_review`.

### Phase 3: Write-path enforcement
- New records must populate `fact_type` and the matching booleans.
- `Fact*` records must require `star_reason` and `verify_before_use = true`.
- `Fact+` records should link a `learning_policy_id` when relevant.

### Phase 4: Read/filter support
Support queries for:
- all facts
- only Fact+
- only Fact*
- facts requiring verification
- verified-only facts

### Phase 5: Dashboard/learning integration
- Expose Fact* clearly in dashboards.
- Let learning systems consume Fact+ and Fact* explicitly.
- Keep Fact* visible as a governance item.

## Validation rules

- `fact_type = "fact"` must not claim `fact_star = true` or `fact_plus = true`.
- `fact_type = "fact_plus_star"` requires both `learning_policy_id` and `star_reason`.
- `fact_type = "fact_star"` must include `verify_before_use = true`.
- `fact_type = "fact_plus_star"` must include `verify_before_use = true` and the record must be verified before operational use.
- `importance_level = "critical"` is expected for Fact*.
- `verification_status = "verified"` is required before operational use when the fact affects Hermes OS.

## Example mappings

### Fact
```json
{
  "fact_type": "fact",
  "fact_star": false,
  "fact_plus": false,
  "verify_before_use": false,
  "importance_level": "normal"
}
```

### Fact+
```json
{
  "fact_type": "fact_plus",
  "fact_star": false,
  "fact_plus": true,
  "learning_policy_id": "policy-0001",
  "importance_level": "important"
}
```

### Fact*
```json
{
  "fact_type": "fact_star",
  "fact_star": true,
  "verify_before_use": true,
  "importance_level": "critical",
  "star_reason": "Affects Hermes OS routing and rollback safety",
  "verification_status": "verified",
  "rollback_required": true
}
```

## Common pitfalls

- **Encoding importance only in text**
  - Fix: store `fact_star` as a real field.
- **Promoting Fact* without verification**
  - Fix: require `verification_status = verified`.
- **Mixing Fact+ and Fact* without clear semantics**
  - Fix: use `fact_type` to make intent explicit.
- **Breaking old records during migration**
  - Fix: add fields backward-compatibly first.
- **Letting dashboard and store diverge**
  - Fix: update both schema and visualization labels.

## Verification checklist

- [ ] Schema fields are explicit, not inferred from content alone
- [ ] Fact / Fact+ / Fact* mapping is deterministic
- [ ] Backward compatibility is preserved
- [ ] Migration backfill is conservative and reviewable
- [ ] Fact* requires verification before use
- [ ] Dashboard or reports can filter Fact*
- [ ] Learning integration only consumes the intended classes

## When to use this skill

Use it whenever Boss asks about:
- Fact Store structure
- Fact* governance
- schema design
- migration/backfill planning
- learning integration for facts
- dashboard labels for critical facts

## Runtime validator integration (proven workflow)

When you move this policy into code, the reusable pattern is:

1. Add a standalone Python validator module near the schema so it can be reused by CLI, backend, and tests.
2. Make the validator dependency-free if possible, so it can run in the same environments as the store.
3. Normalize the candidate record before validation:
   - fill implicit defaults,
   - coerce booleans,
   - parse JSON-string arrays for fields like `tags`, `impact_scope`, and `related_entities`,
   - strip internal DB-only columns before schema validation.
4. Validate at write time in both `add_fact` and `update_fact` paths, not only on read.
5. For star records, auto-fill `last_verified_at` when `verification_status=verified` and the caller did not provide a timestamp.
6. Keep legacy compatibility when the existing store uses categories like `general`; add them explicitly if they are still used by the live path.
7. Reject invalid `Fact+*` combinations with clear error messages before the DB commit.
8. Keep tests for:
   - valid Fact / Fact+ / Fact* / Fact+* records,
   - invalid composite combinations,
   - add path,
   - update promotion path,
   - provider/tool wrapper path.

### Pitfalls discovered

- Validation can fail if DB row objects include internal columns such as `helpful_count` or `retrieval_count`; remove those before schema validation.
- Validation can fail if update-path snapshots omit `created_at`; read the full row for promotion/update validation.
- Validation can fail if SQLite timestamps are stored as `YYYY-MM-DD HH:MM:SS`; accept both SQLite-style and RFC3339/ISO-8601 timestamps.
- `tags` may be stored as a JSON string in older paths; convert it to a list before validation.
- Candidate records should be validated after normalization but before SQL commit so bad `Fact+*` values never enter the DB.

## Proven implementation pattern (from field-tested work)

When implementing write-path or migration changes for the live Fact Store, the most reusable pattern is:

1. Put shared normalization / validation / create / update logic in one helper module near the store layer so backend, server, and migration code all call the same rules.
2. Expose both HTTP write routes and CLI migration wrappers from that same rule set to avoid schema/behavior drift.
3. Add a direct `get_fact(fact_id)` accessor in the holographic store when write/update flows need exact row reloading for validation or promotion.
4. Keep the dashboard backend and the memory server on the same helper and schema constants; avoid duplicate column lists in each file.
5. Support legacy SQLite migration by renaming `fact_records` to `facts` when present, then adding the new Fact / Fact+ / Fact* fields and rebuilding indexes/FTS rather than dropping the table.
6. Verify the migration on a temporary legacy DB before touching real data.
7. Add a small CLI wrapper (for example `hermes-fact-migrate` and `hermes-fact-validate`) so the same logic can be driven from shell scripts, tests, and ops flows.
8. Backstop the change with an end-to-end test that exercises both migration and write API behavior over HTTP, not only unit tests.

### Concrete evidence from the current implementation

- Shared helper: `hermes-workspace/memory-graph/fact_store_api.py`
- Store accessor added: `hermes-agent/plugins/memory/holographic/store.py::get_fact()`
- Server/backend REST routes now include:
  - `GET /api/facts` (list with query filters)
  - `GET /api/facts/{fact_id}` (read one)
  - `POST /api/facts` (create)
  - `PATCH /api/facts/{fact_id}` (update)
  - `DELETE /api/facts/{fact_id}` (remove)
- Both `fact_graph_backend.py` and `memory_graph_server.py` should share the same helper-backed behavior instead of drifting separately.
- Query filters that were proven useful: `category`, `fact_type`, `fact_star`, `fact_plus`, `verify_before_use`, `verification_status`, `min_trust`, `limit`
- Parsing rule that mattered in practice: treat boolean query params via a small helper (`true/false/1/0/yes/no`) instead of relying on raw strings.
- Migration CLI: `hermes-workspace/memory-graph/fact_migrate.py`
- Shell wrapper: `~/.local/bin/hermes-fact-migrate`
- Legacy DB migration behavior: rename `fact_records` -> `facts`, then add the new Fact* columns and rebuild supporting indexes
- Verification: py_compile + pytest on the write API test file passed after the shared-helper refactor


### Pitfalls discovered

- Avoid duplicating schema constants between the dashboard backend and memory server; that is where drift appears first.
- When validating update paths, reload the full row from the DB before schema checks so DB-only fields and missing timestamps do not cause false failures.
- For legacy rows, normalize JSON-string arrays such as `tags` / `related_entities` before validation.
- If a migration can preserve the old table by renaming it first, prefer that over dropping/recreating, because it keeps recovery options open.
- Keep HTTP error handling separate for malformed JSON versus schema validation errors; tests are easier to read and users get clearer feedback.

## When to update this skill

Update this skill if Boss changes the meaning of Fact / Fact+ / Fact*, if the Fact Store schema adds new required fields or verification states, or if a new runtime gate pattern is discovered for validation/migration/tooling.
