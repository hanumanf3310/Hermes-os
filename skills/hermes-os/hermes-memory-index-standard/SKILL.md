---
name: hermes-memory-index-standard
description: Define and maintain Hermes OS memory as a compact pointer/index layer that links to Fact Store records, reports, files, and dashboards instead of duplicating prose.
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [memory, index, pointer, fact_store, report, dashboard, hermes-os, governance]
---

# Hermes Memory Index Standard

- Boss wants memory to behave like an index or directory rather than a duplicate knowledge base.
- Boss asks to curate or reorder `MEMORY.md` / `USER.md`, remove duplicates, or keep top-priority anchors at the top.
- Boss wants a consistent bootstrap order in memory files: read merged-hard-gate-policy first, Tiny Trade Protocol second, Fact Store-first when unclear third.

## Core idea

Memory should store *pointers* only.
The source of truth lives in:
- Fact Store records
- reports / markdown artifacts
- live dashboards
- code files when appropriate

### Source-of-truth chain
`Memory Index → Master Index Fact → Fact Store → Report/File/Dashboard`

### Master index pattern
For Hermes OS, prefer a single master pointer record (for example a Fact Store record such as `Hermes-OS-ROOT`) that serves as the top-level index for state, command, and mode details. Memory entries should point to the master index rather than duplicating the underlying prose.

### Operational gate
If Boss says not to add memory, or requires confirmation before memory writes, obey that as a strict workflow gate. Prefer Fact Store updates and short pointer entries over new memory prose whenever possible.

### Memory write discipline
When memory usage is near the limit or the content is operationally sensitive:
1. Compact existing memory entries first.
2. Replace long prose with short pointer summaries.
3. Move durable content into Fact Store or report files.
4. Keep the memory entry as a stable index to the source of truth.
5. Avoid adding multiple overlapping entries for the same concept.
6. Do not write new memory unless the user has explicitly confirmed the memory write requirement; if the user requires two confirmations, treat that as a hard gate before any add/replace action.

## When to use
- Boss asks to remember a stable fact without duplicating long prose
- Boss wants memory to link to Fact Store IDs or report paths
- You need to reduce memory bloat or avoid repeating long content
- You want memory to remain searchable and compact across sessions

## What to store in memory
Keep entries short and structured:
- memory key
- short summary
- fact IDs
- canonical file/report paths
- related entities/tags
- status
- verification marker when needed

### Suggested record shape
```yaml
memory_key: string
kind: fact_pointer | report_pointer | skill_pointer | dashboard_pointer | workflow_pointer | policy_pointer
summary: string
fact_ids: [integer, ...]
paths: [string, ...]
entities: [string, ...]
status: active | deprecated | needs_review
verify_before_use: boolean
last_verified_at: string | null
scope: [string, ...]
notes: string | null
```

## Classification rules

### 1) Fact pointer
Use when the memory item should point to a Fact Store record.

Example:
```yaml
memory_key: gemini_research_workflow
kind: fact_pointer
summary: Hermes → Gemini → Hermes verification workflow exists and is routed through /gemini-research
fact_ids: [359]
paths:
  - /home/hanuman3310/hermes-agent/hermes_cli/gemini_workflow.py
  - /home/hanuman3310/hermes-agent/hermes_cli/commands.py
status: active
verify_before_use: true
last_verified_at: 2026-04-27T00:00:00Z
scope: [hermes_os, routing, learning]
notes: Treat as Fact+*
```

### 2) Report pointer
Use when the source of truth is a report or generated artifact.

Example:
```yaml
memory_key: controlled_update_parity_20260427
kind: report_pointer
summary: Restore parity summary for the 2026-04-27 controlled update round
fact_ids: [298, 310, 318, 326]
paths:
  - /home/hanuman3310/hermes-os-mode/reports/upstream-audit/HERMES_CONTROLLED_UPDATE_PARITY_20260427_123136.md
status: active
verify_before_use: false
last_verified_at: 2026-04-27T12:31:36Z
scope: [hermes_os, update]
notes: Keep as evidence pointer, not duplicated prose
```

### 3) Memory-only pointer
Use when the item is just a recall aid and does not need a fact record.

Example:
```yaml
memory_key: controlled_update_one_page_template
kind: report_pointer
summary: One-page controlled update template for future rounds
fact_ids: [351]
paths:
  - /home/hanuman3310/hermes-os-mode/reports/upstream-audit/HERMES_CONTROLLED_UPDATE_ONE_PAGE_TEMPLATE.md
status: active
verify_before_use: false
last_verified_at: 2026-04-27T12:51:35Z
scope: [hermes_os]
notes: Worked example is 2026-04-27
```

## Rules of thumb
- Never store long logs or full report bodies in memory.
- Prefer a Fact-linked pointer if the item affects Hermes OS behavior.
- Prefer a report-linked pointer if the evidence already exists.
- If the record changes, update the pointer target or status rather than duplicating the old text.
- If the item is `Fact*`, `verify_before_use` must be true.
- Memory is for recall. Facts are for truth. Reports are for evidence.

## Workflow
1. Create or update the Fact Store record first if the item is substantive.
2. Create the memory pointer as a short index to that fact or report.
3. Include a canonical path for quick retrieval.
4. Mark verification state when the item is operationally sensitive.
5. Keep the record compact enough to scan in one glance.

## What not to do
- Do not duplicate the full prose of a fact in memory.
- Do not store raw command output or long logs.
- Do not keep secrets or temporary session-only data.
- Do not let memory drift away from the current source-of-truth.

## Practical benefits
- Lower memory usage
- Faster retrieval
- Less duplication
- Easier updates when facts change
- Clearer governance for `Fact*` items

## Validation checklist
- [ ] Memory entry is short
- [ ] Source of truth is linked, not copied
- [ ] Fact IDs are present when available
- [ ] `Fact*` items are marked `verify_before_use: true`
- [ ] Canonical path is included for reports/files
- [ ] No long prose duplication

## Pitfalls
- **Memory limit errors when adding too much text**
  - Fix: replace or remove lower-priority memory entries and keep the pointer compact.
- **Fact* items look like ordinary memory**
  - Fix: always mark `verify_before_use: true` and point to the Fact Store record.
- **Reports get summarized twice**
  - Fix: use the report path, not a rewritten summary.
- **Pointers become stale**
  - Fix: update the memory target and status when the report or fact is superseded.

## Update this skill when
- the memory schema changes,
- Boss changes how pointers should be stored,
- a new report/fact linking pattern is discovered,
- or memory should integrate with a new dashboard or fact flow.
