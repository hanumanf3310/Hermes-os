---
name: hermes-restore-recall-workflow
description: Reusable workflow for retrieving prior Hermes restoration/recovery decisions from fact store, especially around /gpts and /model behavior after updates.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [fact_store, recall, recovery, restore, gpts, model, hermes-update, memory]
---

# Hermes Restore / Recall Workflow

Use this when the user asks about:
- restoring or recovering prior behavior,
- `/gpts` or `/model` after update,
- rollback / recovery / revert / restore history,
- or whether a previous fix already exists in memory.

This skill captures a reliable retrieval pattern:
1. search facts with broad recovery keywords,
2. inspect the highest-trust matches,
3. map the result back to the user’s intended recovery target,
4. summarize what is already known and what is still missing.

## Step 1: Search with broad recovery terms
Use `fact_store.search` with OR queries, because narrow AND searches often miss relevant records.

Good query patterns:
- `gpts OR model OR restore OR recovery OR rollback`
- `restore OR recovered OR recovery OR revert OR rollback`
- `gpts OR model picker OR codex bridge OR pretty card`
- `hermes update OR protected behavior OR custom behavior`

If the first search is empty, try a second pass with the specific target words from the user.

## Step 2: Prefer durable facts over session memory
When matching results exist, prefer facts that:
- mention an explicit restore/recovery outcome,
- mention regression tests or validation,
- describe protected custom behavior,
- identify triggers or user preferences,
- or connect the restore target to a concrete file/module.

## Step 3: Interpret restore scope carefully
Classify the user’s request into one of these buckets:
- `/gpts` status / Codex bridge recovery
- `/model` picker / catalog parity recovery
- custom behavior preservation after Hermes update
- rollback or backup planning
- general memory recall / prior decision lookup

Do not assume all recovery requests mean code changes; sometimes the user only wants the prior decision summarized.

## Step 4: Look for trigger phrases and durable preferences
Search for facts that mention trigger phrases or protected behaviors.
Examples of useful signals:
- `/gpts`
- `/model`
- `restore`
- `recovery`
- `rollback`
- `custom behavior`
- `update`
- `regression tests`
- `pretty card`
- `Codex bridge`

If a fact explicitly says custom `/gpts` or `/model` behavior must be restored/protected after update, treat that as a high-priority durability fact.

## Step 5: Summarize with provenance
Return a compact answer with:
- what was found,
- the relevant fact IDs or source references if available,
- what the remembered restoration target is,
- and any caveat if the search results are partial.

Example response shape:
- "Found prior restore work for `/gpts` and `/model` in fact X and Y."
- "It was verified with regression tests."
- "The durable preference is to restore custom behavior after update."

## Pitfalls
- **Using only exact-match search**
  - Fix: search broad OR queries first.

- **Confusing command docs with recovery history**
  - Fix: separate operational command facts from restore/recovery facts.

- **Assuming the latest session is the source of truth**
  - Fix: prefer durable fact store entries and trust-scored matches.

- **Treating recall as code mutation**
  - Fix: if the user only asks to find or summarize, do not propose edits yet.

## Verification
Before answering, confirm:
- the search actually found relevant facts,
- the result matches the requested recovery target,
- and the summary distinguishes remembered behavior from current implementation.
