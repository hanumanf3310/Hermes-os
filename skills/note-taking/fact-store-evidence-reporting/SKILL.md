---
name: fact-store-evidence-reporting
description: Build grounded reports from Fact Store data with explicit separation of facts, preferences, and inferences, and no unsupported praise or speculation.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [fact-store, reporting, evidence, grounding, citations, no-hype]
    related_skills: [hermes-os-memory-system-integration, phase10-knowledge-integration, phase11-registry-governance-hardening]
---

# Fact Store Evidence Reporting

Use this skill when the user wants a report about a person, project, or system based on Fact Store evidence.

## When to Use
- The user asks for a profile, analysis, summary, or report grounded in stored facts.
- The output must avoid praise, hype, or unsupported interpretation.
- You need to convert cross-session facts into a readable document or summary.
- The user wants a "real data" report with traceability.

## Core Rule

**Do not invent. Do not embellish. Do not overstate.**

If a claim cannot be backed by a fact, label it as:
- not found
- inference
- tentative observation

## Workflow

### 1) Gather evidence first
Use Fact Store in this order:
1. `probe` the main entity
2. `search` related concepts and preferences
3. `reason` across multiple entities when the user asks for a synthesis
4. capture the fact IDs and trust levels you rely on

### 2) Separate the report into layers
Use distinct sections such as:
- Facts / observations
- Preferences / operating rules
- Inferences from multiple facts
- Gaps or missing evidence

### 3) Stay grounded
For every non-trivial statement:
- tie it to one or more fact IDs
- avoid adding praise or negative judgment unless the facts support it
- do not fill gaps with guesses

### 4) Preserve traceability
Include one of these in the output:
- fact IDs in brackets, e.g. `[Fact 311]`
- a compact evidence appendix
- a short note on what was not found

### 4.5) Promote stable preferences after reporting
If the report reveals a durable user preference, workflow rule, or operating style that is likely to matter in future sessions, promote it out of the conversation immediately:
- update user profile / memory with the stable preference
- keep the wording compact and declarative
- do not leave a report-derived preference only in chat if it is clearly reusable
- do not overstore one-off observations that are not stable

Examples of report-derived items to promote:
- evidence-first working style
- proof-before-polish preference
- strict no-guessing / no-hype rule
- reuse-existing-skills-first behavior

If the item is important to system behavior, treat it as traceable evidence and keep the fact IDs or report path in the surrounding notes.

### 5) Deliver in the requested form
If the user wants a document:
- write the report in a doc or markdown file
- keep the title neutral
- keep language factual and readable

## Recommended Structure

```text
Title

1. Scope
2. Evidence used
3. Working style
4. Decision-making
5. Planning and problem solving
6. Tools / governance rules
7. Inferences
8. Evidence gaps
```

## Good Practices
- Prefer direct quotes or paraphrases only when backed by facts.
- If the user requests a profile, separate observed behavior from interpretation.
- Use the smallest number of facts needed to support each point.
- If facts conflict, say so instead of choosing a side silently.
- Keep the tone neutral and non-admiring.
- If the user forbids exaggeration, treat that as a hard constraint.

## Common Pitfalls
- Turning facts into praise.
- Presenting an inference as a fact.
- Mixing system rules and user preferences without labeling them.
- Omitting fact IDs, which breaks traceability.
- Searching only for positive evidence and ignoring contradictory facts.

## Verification Checklist
- [ ] Evidence gathered with Fact Store
- [ ] Facts and inferences separated
- [ ] No unsupported claims
- [ ] Fact IDs included where useful
- [ ] Tone is neutral and non-hype
- [ ] Report matches user’s requested format

## Example Use

When asked: "Write a real-data report about Boss's working style"

Do:
1. probe Boss-related facts
2. search for planning / debugging / governance preferences
3. write a report with fact-backed sections
4. cite fact IDs
5. avoid praise or exaggeration
