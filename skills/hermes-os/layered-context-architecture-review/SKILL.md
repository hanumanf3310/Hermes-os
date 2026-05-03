---
name: layered-context-architecture-review
description: Compare Hermes Context Mode, OpenContext, Fact store, and similar context systems by classifying their roles, overlap, and source-of-truth boundaries.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes-os, context, memory, mcp, facts, integration]
---

# Layered Context Architecture Review

Use this skill when the user asks whether two or more memory/context systems overlap, can work together, or should be treated as redundant.

## When to Use

- Comparing Hermes Context Mode with another MCP/context store
- Evaluating whether a new tool duplicates Fact, memory, or context compression
- Explaining how multiple knowledge systems should coexist in Hermes OS
- Reviewing integration candidates for role overlap and source-of-truth boundaries

## Core Model

Classify systems into three layers:

1. **Working memory**
   - Session-level, short-lived, tool-output heavy
   - Examples: Context Mode, compression layers, session caches

2. **Long-term knowledge base**
   - Human-readable docs, manifests, stable links, searchable library
   - Examples: OpenContext-style stores, doc libraries, external knowledge vaults

3. **Canonical facts / policy**
   - Short, verified, high-trust statements used as source of truth
   - Examples: Fact store records, policy gates, stable verified system facts

## Workflow

1. **Probe the facts first**
   - Use `fact_store probe` / `related` / `reason` for the relevant entities.
   - If the topic is cross-session, use `session_search` before answering.

2. **Inspect the candidate system**
   - Read README, package/config, entrypoints, and MCP config if applicable.
   - Identify whether it is active, installed, or only documented.

3. **Map responsibilities**
   - Determine what the system stores: raw context, docs, stable facts, or runtime session data.
   - Determine its access pattern: agent tool, human UI, or backend service.

4. **Check overlap**
   - Ask whether it duplicates working memory, long-term knowledge, or canonical facts.
   - Note partial overlap explicitly; avoid calling everything redundant.

5. **Assign a role**
   - Working memory: use during the task
   - Knowledge base: persist for later retrieval
   - Facts: use for verified truth and policy

6. **Decide integration stance**
   - **Complementary**: different layer, safe to co-exist
   - **Redundant**: same layer and same retrieval purpose
   - **Nested**: one system feeds another, with clear boundaries
   - **Conflicting**: overlapping truth source or duplicate persistence rules

## Decision Rules

- `Context Mode`-style tools are usually **working memory**.
- `OpenContext`-style tools are usually **long-term knowledge bases**.
- `Fact` is **not** a general context store; it is a verified truth/policy layer.
- Two systems can both “remember” things and still be non-redundant if they operate at different layers.
- Do not assume an installed MCP server is active unless discovery or runtime evidence confirms it.

## Output Format

When responding, prefer a compact table:

| System | Layer | Stores | Best use | Overlap |
|---|---|---|---|---|

Then add:
- one sentence on whether they are redundant
- one sentence on the safest integration pattern
- one sentence on what is source of truth

## Pitfalls

- Do not equate “has search” with “same purpose”.
- Do not equate “can persist” with “Fact”.
- Do not claim redundancy without checking data model, lifecycle, and intended use.
- Do not assume a tool is in production just because it is installed or documented.
- When multiple systems exist, prefer **layered architecture** over replacement unless they truly duplicate the same role.

## Good Example Claims

- "Context Mode and OpenContext overlap in retrieval, but at different layers: working memory vs long-term knowledge."
- "Fact is the canonical verified layer, so it should not be treated as a general context cache."
- "The systems are complementary if each has a distinct lifecycle and source-of-truth boundary."
