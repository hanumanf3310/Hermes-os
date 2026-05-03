---
name: hermes-os-context-mode-safe-integration
description: |
  Phased Context Mode integration for Hermes OS with safety checkpoints.
  Implements proactive context retrieval (passive + active) with Policy Gateway
  compliance, following safe-update patterns with evidence gates at each phase.
version: 1.0.0
author: hanuman3310
tags: [hermes-os, context-mode, integration, safety, checkpoints, phased]
trigger: |
  When needing to:
  - Implement Context Mode infrastructure for Hermes OS
  - Build proactive context retrieval with pattern detection
  - Follow safe-update workflow with rollback plans
  - Integrate Policy Compliance at each checkpoint
  - Deploy infrastructure changes safely to live runtime
  - Update Dashboard graph as implementation progresses

  Use this skill for Hermes OS phased infrastructure work that requires
  safety gates, evidence validation, and checkpoint-based progress.
---

# Hermes OS Context Mode Safe Integration

Phased implementation of Context Mode runtime hooks with safety checkpoints.

## Pattern Overview

```
Phase A: Setup (Index → Evidence)
    ↓ Checkpoint 1: VALIDATE
Phase B: RAG Integration (Hook → Tests → Deploy)
    ↓ Checkpoint 2: VERIFY
Phase C: Policy Compliance (Checker → Scan → Dashboard)
    ↓ Checkpoint 3: COMPLY
Phase D: Active Retrieval (Pattern Detection → Integration)
    ↓ Checkpoint 4: OPERATIONAL
```

## Phase A: Context Mode Setup

**Goal**: Index documentation and establish evidence base

**Actions**:
1. Load and index Hermes OS skills (`skill_view`)
2. Read Policy Gateway documentation
3. Verify Dashboard working path map
4. Collect evidence for design decisions

**Checkpoint Gate**:
- [ ] Context documents indexed
- [ ] Policy rules understood
- [ ] Dashboard structure verified

## Phase B: RAG Integration (Passive Retrieval)

**Goal**: Build context_mode_retrieval.py with runtime hook

**Pattern (TDD)**:
1. Write RED tests (5-6 test cases)
2. Run tests → confirm failures
3. Implement module (fail-soft, fenced blocks)
4. Patch run_agent.py `pre_llm_call` hook
5. Tests GREEN
6. Deploy to live runtime (dev → live sync)
7. Restart gateway
8. Verify with live tests

**Safety**:
- Fail-soft: try/except with pass on error
- Token limit: <20,000 chars
- Non-authoritative: `<context-mode-retrieval>` fenced block

**Checkpoint Gate**:
- [ ] Tests pass (dev + live)
- [ ] Hook integrated without crashes
- [ ] Gateway restart successful

## Phase C: Policy Compliance Integration

**Goal**: Validate code against Policy Gateway rules

**Pattern**:
1. Create `policy_compliance_checker.py` (read-only)
2. TDD: 6 tests (RTK, UTC+7, Evidence-first)
3. Scan 5-10 real files for violations
4. Fix safe violations (defer risky ones)
5. Deploy to live runtime
6. Update Dashboard (+1 node, +links)
7. Validate graph: nodes=N, links=L, missing_refs=0

**Policy Rules**:
- RTK-MES: `terminal()` must use `rtk run`
- UTC+7: `datetime.now()` must use `ZoneInfo("Asia/Bangkok")`
- Evidence-first: Results need evidence markers

**Checkpoint Gate**:
- [ ] 6/6 tests pass
- [ ] Violations documented (fixed or deferred)
- [ ] Dashboard updated and validated
- [ ] Live runtime deployed

## Phase D: Active Context Retrieval

**Goal**: Proactive pattern detection with task-specific context

**Pattern**:
1. **Design Checkpoint**:
   - Trigger patterns (code, analysis, config, safety)
   - RAG boundaries (max tokens, timeout, sources)
   - Rollback plan per failure mode

2. **Implement**:
   - `active_context_retrieval.py`
   - Pattern detection with confidence scores
   - Task-specific context building
   - Fail-soft logging

3. **Integrate**:
   - Add to run_agent.py hook (after passive retrieval)
   - Token limit: <4,000 chars
   - Error handling: debug log only

4. **Validate**:
   - Test pattern detection
   - Verify context injection
   - Check no interference with normal flow

**Checkpoint Gate**:
- [ ] Design approved
- [ ] Implementation complete
- [ ] Tests pass
- [ ] Integration verified

## Safety Checkpoints (All Phases)

### Pre-flight Checklist
Before ANY code change:
- [ ] Backup target files (`.bak.YYYYMMDD-HHMMSS`)
- [ ] Policy compliance check current state
- [ ] Verify rollback commands work

### Evidence Requirements
Every claim must have:
- Tool output showing result
- File path evidence
- Timestamp (UTC+7)

### Rollback Plan
| If Problem | Action |
|------------|--------|
| Test failures | Fix before proceeding |
| Gateway crash | Revert run_agent.py patch, restart |
| False positive triggers | Disable specific pattern |
| Context too large | Truncate + log warning |

## Key Files

```
agent/
  context_mode_retrieval.py        # Task B: Passive
  policy_compliance_checker.py     # Task C: Validation
  active_context_retrieval.py      # Task D: Proactive

tests/agent/
  test_context_mode_retrieval.py
  test_policy_compliance_checker.py

gateway/run.py                     # Runtime context injection
~/.hermes/gateway_hermes_os_mode.json   # Chat binding state
```

## Dashboard Graph Updates

At each phase completion:
1. Backup `dashboard.html`
2. Add node for new component
3. Add links to related nodes
4. Validate: `python validate-dashboard-graph.py`
5. Evidence: `nodes=N, links=L, missing_refs=0`

## Testing Strategy

```bash
# Dev tests
pytest tests/agent/test_*.py -v

# Live runtime verification
cd ~/.hermes/hermes-agent
pytest tests/agent/test_*.py -v

# Policy scan
python -c "from agent.policy_compliance_checker import check_compliance; print(check_compliance('target.py')['report'])"

# Dashboard validation
python ~/.hermes/scripts/validate-dashboard-graph.py dashboard.html
```

## Common Patterns

### Fail-Soft Hook Pattern
```python
try:
    from agent.xxx import build_context
    context = build_context(...)
    if context and len(context) < LIMIT:
        system_message += "\n\n" + context
except Exception as exc:
    logger.debug("Hook failed: %s", exc)  # Never crash
```

### Phased Deploy Pattern
```
Dev checkout: ~/hermes-agent/
Live runtime: ~/.hermes/hermes-agent/

1. Implement in dev
2. Test in dev
3. Copy to live: cp dev/file live/file
4. Test in live
5. Restart gateway
6. Smoke test
```

### UTC+7 Fix Pattern
```python
# Before (violation)
from datetime import datetime
now = datetime.now()

# After (compliant)
from datetime import datetime
from zoneinfo import ZoneInfo
now = datetime.now(ZoneInfo("Asia/Bangkok"))
```

## Lessons from Implementation

1. **Safety over speed**: Defer risky core file changes
2. **Evidence gates**: No phase completion without verification
3. **Token limits**: Context blocks must have strict bounds
4. **Fail-soft**: Hooks must never crash the main loop
5. **Backup first**: Every file change needs rollback path

## Verification Commands

```bash
# Verify Hermes OS state
cat ~/.hermes/state/hermes-os.json
cat ~/.hermes/gateway_hermes_os_mode.json

# Verify Policy Compliance
python -m tools.merged_policy_validator website/docs/reference/merged-hard-gate-policy.yaml

# Verify Dashboard
hermes-os dashboard
```

## When Complete

System should have:
- ✅ Passive context retrieval (skill-based)
- ✅ Active context retrieval (pattern-based)
- ✅ Policy compliance validation
- ✅ Safety checkpoint system
- ✅ Dashboard graph tracking all components
