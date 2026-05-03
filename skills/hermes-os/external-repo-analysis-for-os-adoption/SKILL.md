---
name: external-repo-analysis-for-os-adoption
title: External Repository Analysis for Hermes OS Adoption
version: 1.0.0
description: |
  Research and analyze external GitHub repos, coding tools, or AI agent frameworks
  — then produce a structured adoption report comparing against Hermes OS
  capabilities, identifying gaps, and proposing actionable improvements.

  Evidence-first. RTK-first. UTC+7.

tags:
  - research
  - github
  - analysis
  - adoption
  - hermes-os
requires_tools:
  - browser
  - terminal
  - file
author: Boss (Hermes OS Operator)
based_on: mattpocock/skills analysis workflow
---

# External Repository Analysis for Hermes OS Adoption

## Philosophy
When Boss encounters interesting external repos, tools, or frameworks, do not just summarize — analyze them against Hermes OS's existing capabilities and produce an actionable adoption plan.

**Evidence-first:** Browser snapshot, structured extraction, not just vibe reading.
**Hermes OS lens:** Compare against policy gateway, fact store, checkpoint discipline, multi-platform support.

---

## When to Use

Trigger this skill when:
- Boss shares a GitHub repo link and asks "ดูให้หน่อย"
- Boss says "เอามาปรับใช้กับ Hermes OS"
- Boss shares an article/blog about AI coding best practices
- Boss encounters a new external agent skill / plugin / tool

Do NOT use when:
- Boss asks to clone/use the repo directly (use `github` skill instead)
- Boss wants to delegate coding to external agent (use `delegate_task`)

---

## Workflow

### Phase 1: Inspect External Source

```
1. browser_navigate to source
2. browser_snapshot for full content (if article)
3. browser_click into README.md, skills/ directory
4. Extract: author, stars, forks, license, core concepts, key features
5. Read representative files (SKILL.md, README.md, docs/)
```

Evidence to capture:
- Stars/forks count (if GitHub)
- Last commit date (freshness)
- Key files/directories
- Core philosophy / design principles

### Phase 2: Structured Analysis

Analyze against these Hermes OS dimensions:

| Dimension | Hermes OS Status | External Tool Status | Gap? |
|-----------|-----------------|---------------------|------|
| Policy enforcement | merged-hard-gate-policy.yaml (fail-closed) | [external] | [high/med/low/none] |
| Evidence tracking | Fact Store (433+ facts, trust scoring) | [external] | |
| Checkpoint discipline | go/no-go gate (Lesson 7) | [external] | |
| Token optimization | RTK (60-90% compression) | [external] | |
| Multi-platform gateway | CLI + Telegram + Discord + ... | [external] | |
| Dashboard visualization | D3.js memory graph (93+ nodes) | [external] | |
| Timezone enforcement | Asia/Bangkok UTC+7 lock | [external] | |
| Direct vs delegate | explicit command only | [external] | |

### Phase 3: Gap Classification

For each gap found, classify:

```
ALREADY_SUPERIOR: Hermes OS already better — note for confidence
CAN_ADOPT: Hermes OS should adopt this concept
NEW_OPPORTUNITY: Neither has it — co-development potential
NOT_APPLICABLE: External-specific, not relevant to Hermes OS
```

### Phase 4: Adoption Plan

Propose concrete changes:

| Priority | Action | Expected Impact | Evidence |
|----------|--------|----------------|----------|
| P0 | [immediate action] | [why] | [how to verify] |
| P1 | [short-term] | | |
| P2 | [medium-term] | | |
| P3 | [research-only] | | |

### Phase 5: Evidence Artifact

Write report:
```
~/hermes-os-blueprint/reports/{source-name}-analysis-YYYYMMDD.md
```

Must include:
- Executive Summary
- Source metadata (author, stars, license)
- Dimension comparison table
- Gap classification
- Adoption plan with priorities (phase-based)
- Hermes OS superiority list
- Evidence references (browser snapshots, file reads)
- Rollback evidence (if implementation fails)

#### Phase-Based Implementation (Lesson from Matt Pocock + GitNexus)

Never implement all-at-once. Use phases:

| Phase | Scope | State-Changing? | Example |
|-------|-------|-------------------|---------|
| P0 | Read-only analysis / index | ❌ No | Parse source code, build graph data JSON |
| P1 | Skill creation / policy addition | ❌ No | Create SKILL.md, CONTEXT.md, cron schedules |
| P2 | Graph integration (with bridge links) | ✅ Yes | Add nodes to dashboard WITH links to existing nodes |
| P3 | Full production deployment | ✅ Yes | Enable hooks, schedule cron, enforce policy |

**Critical rule from incident:** Code nodes injected into dashboard MUST have bridge links to memory nodes (e.g., `code_run_agent.py → skill_hermes_agent`). Without bridge links → isolated components → `connected_components > 1` → validator fails → rollback required.

#### Rollback as First-Class

If P2/P3 fails:
1. Restore from backup (document backup path)
2. Re-validate (must return `ok=true`)
3. Write rollback evidence file
4. Learn → adjust P0/P1 → retry

This is NOT optional. It is the definition of done for state-changing phases.

---

## Hermes OS Specific Additions

### Tiny Trade Protocol Check
Before analyzing external tools:
```python
# Check if external tool requires integration risk
if external_tool.requires_runtime_changes:
    run tiny_trade_protocol()  # spend tiny token, assess risk
```

### Fact Store Integration
After analysis, record as Fact+:
```
fact_store.add(
    category="external-research",
    content="Repo X analyzed. Hermes OS superior in [dimensions]. Gaps to adopt: [list].",
    tags="research,external,adoption,{repo_name}"
)
```

---

## Example Output Structure

```markdown
# {Repo} Analysis for Hermes OS

**Date:** YYYY-MM-DD
**Timezone:** Asia/Bangkok UTC+7
**Source:** {URL}
**Author:** {Name}
**Stats:** {stars}⭐ {forks}🍴

## 1. Executive Summary
{2-3 sentences}

## 2. Dimension Comparison
| Dimension | Hermes OS | External | Gap |
|-----------|-----------|----------|-----|
...

## 3. Gap Classification
- ✅ ALREADY_SUPERIOR: [list]
- 🔵 CAN_ADOPT: [list]
- 🔴 NEW_OPPORTUNITY: [list]

## 4. Adoption Plan
| Priority | Action |
|----------|--------|
| P0 | ... |

## 5. Evidence
- Browser snapshots: [refs]
- File reads: [paths]
- Commands run: [rtk run outputs]
```

---

## Related Skills
- hermes-os-blueprint (training context)
- fact-store-evidence-reporting (evidence artifact writing)
- github-repo-reconnaissance (shallow repo inspection)
- awesome-agent-skills-radar (external skills catalog)
- research-paper-writing (academic source analysis)
