---
name: auto-memory-audit-cron
title: Auto Memory Audit from Recent Sessions (Cron Workflow)
version: 1.0.0
description: |
  Cron job workflow for automatically detecting and saving important memories
  from recent sessions. Focuses on completion indicators, corrections, feedback,
  and preferences with 5W1H structured extraction.
  
  Trigger: Hourly cron job
  Scope: Conversations within last 1 hour
  Criteria: importance >= 3, completion signals, corrections, feedback
  Output: fact_store.jsonl with 5W1H structure
  
tags:
  - cron
  - memory
  - audit
  - automation
  - 5W1H
  - completion-detection
requires_tools:
  - session_search
  - execute_code
  - skill_view (optional)
author: Hermes Agent
date: 2026-04-27
---

# Auto Memory Audit (Cron Workflow)

## Overview

Automatically detect, extract, and save important memories from recent sessions.
Designed for hourly cron execution with minimal manual intervention.

**Trigger:** Scheduled cron job (recommended: every hour)  
**Scope:** Sessions within last 1 hour  
**Storage:** `~/.hermes/fact_store.jsonl`  
**Format:** JSON with 5W1H structure + importance scoring

---

## When to Use

**Cron Job:** Run automatically every hour  
**Manual:** Run when Boss asks to "check recent memory" or "audit conversations"

**Do NOT use when:**
- Boss explicitly requests SILENT mode for specific session
- Session is still active and ongoing

---

## The Process

### Phase 1: Discovery

```python
# 1. Find recent sessions
session_search(limit=5)  # Get 5 most recent

# 2. Search for completion signals
session_search(
    query="เสร็จแล้ว OR done OR เรียบร้อย OR completed OR finished OR "
          "correction OR feedback OR preference OR remember OR 'ค่ะ Boss'",
    limit=3
)

# 3. Filter by source (non-cron only for manual runs)
session_search(
    query="source:telegram OR source:cli OR source:discord",
    limit=5
)
```

**Completion Signals (Thai + English):**
| Signal | Thai | English |
|--------|------|---------|
| Done | เสร็จแล้ว | done, finished |
| Ready | เรียบร้อย, พร้อม | ready, completed |
| Boss confirm | ค่ะ Boss | - |
| Approved | อนุมัติ, ตกลง | approved, confirmed |

---

### Phase 2: Validation

```python
# Validate session is within 1-hour window
current_time = datetime.now()
one_hour_ago = current_time - timedelta(hours=1)

if session_timestamp >= one_hour_ago:
    # Process this session
```

**Check file timestamps:**
- `~/.hermes/fact_store.jsonl` - check last modification
- `~/.hermes/memory-events.jsonl` - verify recent entries

---

### Phase 3: 5W1H Extraction

For each completed task, extract:

```json
{
  "what": "What was completed",
  "who": "Who did the work (Hermes / Boss / User)",
  "where": "Where did it happen (file path, system)",
  "when": "ISO timestamp of completion",
  "why": "Why was this done (reason/context)",
  "how": "How was it accomplished (method/tools)"
}
```

**Example:**
```json
{
  "what": "Hermes repository prepared for actual update",
  "who": "Hermes Agent",
  "where": "/home/hanuman3310/.hermes/hermes-agent",
  "when": "2026-04-27T05:42:00+07:00",
  "why": "Boss requested 'ทำให้พร้อม update จริง'",
  "how": "Created safety commit (8b81e04c), rebased origin/main, cleaned working tree"
}
```

---

### Phase 4: Importance Scoring

**Automatic scoring:**
| Factor | Score | Condition |
|--------|-------|-----------|
| Boss completion signal | +2 | "เสร็จแล้ว", "เรียบร้อย", etc. |
| Critical system impact | +2 | Changes to core infrastructure |
| Multiple test passes | +1 | Test results confirmed success |
| Correction/feedback | +1 | User corrected previous behavior |
| Preference stated | +1 | User expressed preference |
| Base | +1 | Any completed task |

**Threshold:** Only save if `importance >= 3`

---

### Phase 5: Storage

```python
fact = {
    "id": "fact_{type}_{timestamp}",
    "timestamp": "2026-04-27T06:00:00+07:00",
    "content": "Human-readable summary",
    "importance": 5,
    "tags": ["completion", "git", "update", "testing", "critical_task"],
    "5W1H": {
        "what": "...",
        "who": "...",
        "where": "...",
        "when": "...",
        "why": "...",
        "how": "..."
    },
    "source_session": "session_id_here"
}

# Append to file
with open(fact_store_path, 'a') as f:
    f.write(json.dumps(fact, ensure_ascii=False) + '\n')
```

---

## Decision Tree

```
Start
│
├─ Search recent sessions
│   └─ Any sessions within 1 hour?
│       ├─ No → Output [SILENT]
│       └─ Yes → Continue
│
├─ Check for completion signals
│   └─ Signals found?
│       ├─ No → Output [SILENT]
│       └─ Yes → Extract details
│
├─ Check importance >= 3
│   └─ Passes threshold?
│       ├─ No → Output [SILENT]
│       └─ Yes → Format 5W1H
│
└─ Save to fact_store
    └─ Output report
```

---

## Expected Output

### Silent Mode (no findings)
```
[SILENT]
```

### Report Mode (findings detected)
```
## Auto-Memory Audit Report

**เวลาตรวจสอบ:** 2026-04-27 06:00 AM
**ช่วงเวลา:** ย้อนหลัง 1 ชั่วโมง

### ✅ งานที่จบสิ้น

| # | งาน | สัญญาณ | Importance |
|---|-----|--------|------------|
| 1 | ... | ... | 5 |

### 📁 รายละเอียด

**Memory 1:**
- **What:** ...
- **Who:** ...
- ...

### 📈 สถิติ
- Sessions: N รายการ
- ความทรงจำใหม่: N รายการ
- fact_store: N entries
```

---

## Edge Cases

### Case 1: No sessions found
```
Result: [SILENT]
Reason: No conversations in last hour
```

### Case 2: Only cron sessions found
```
Result: [SILENT] or analyze based on context
Reason: Recursive cron loops don't create new memories
```

### Case 3: Session spans multiple hours
```
Action: Extract only the final completion signal
Storage: Timestamp of completion (not session start)
```

### Case 4: Multiple completion signals
```
Action: Create separate memory entries for each distinct task
Do NOT merge unrelated completions
```

---

## Tool Patterns

### Required Tool Sequence

```python
# 1. session_search (recent mode)
session_search(limit=5)

# 2. session_search (keyword mode)
session_search(
    query="เสร็จแล้ว OR done OR ...",
    limit=3
)

# 3. execute_code (validate timestamps)
execute_code(python_script_for_timestamp_check)

# 4. execute_code (save to fact_store)
execute_code(python_script_for_jsonl_append)
```

---

## Validation Checklist

Before marking audit complete:

- [ ] Sessions searched (recent + keyword)
- [ ] Timestamps validated (within 1 hour)
- [ ] Completion signals detected
- [ ] 5W1H structure complete
- [ ] Importance scored (>= 3 threshold)
- [ ] No duplicates (check existing entries)
- [ ] JSONL append successful
- [ ] Report generated (if findings)

---

## Trial and Error Learnings

### Issue 1: Recursive Cron Loops

**Problem:** Cron jobs detecting only other cron summaries
```
Session 1: Cron audit
Session 2: Cron audit
Session 3: Cron audit
```

**Solution:** Filter for `source:telegram OR source:cli` in validation step

---

### Issue 2: Timestamp Confusion

**Problem:** Session start time vs completion time
```
Session started: 05:30
Completed: 05:45
Current time: 06:00
```

**Solution:** Validate completion events, not session starts

---

### Issue 3: Importance Threshold Too Low

**Problem:** Too many trivial memories being saved

**Solution:** Set threshold to >= 3, with strict scoring

---

## Integration

### Cron Configuration

```yaml
# config.yaml
cron_jobs:
  - name: memory-audit
    schedule: "0 * * * *"  # Every hour
    prompt: |
      Run auto-memory audit from last hour.
      Save important memories to fact_store.
    enabled_toolsets: ["session_search", "execute_code"]
```

### Fact Store Path

```
~/.hermes/fact_store.jsonl
```

Format: NDJSON (newline-delimited JSON)

---

## Example Facts Created

### Example 1: Pre-update Completion
```json
{
  "id": "fact_preupdate_ready_20260427_0600",
  "timestamp": "2026-04-27T06:00:00+07:00",
  "content": "Hermes repository prepared for actual update...",
  "importance": 5,
  "tags": ["completion", "git", "update", "testing"],
  "5W1H": {
    "what": "Repository prepared for actual update",
    "who": "Hermes Agent",
    "where": "/home/hanuman3310/.hermes/hermes-agent",
    "when": "2026-04-27T05:42:00+07:00",
    "why": "Boss requested full update preparation",
    "how": "Safety commit + rebase + clean working tree + test validation"
  }
}
```

### Example 2: Multi-agent Rules Update
```json
{
  "id": "fact_delegate_rules_20260427_0600",
  "timestamp": "2026-04-27T06:00:00+07:00",
  "content": "Multi-agent behavior rules updated based on latest test results...",
  "importance": 5,
  "tags": ["completion", "multi_agent", "sub_agent", "testing"],
  "5W1H": {
    "what": "Updated multi-agent/sub-agent behavior rules",
    "who": "Hermes Agent",
    "where": "hermes-delegation-rules skill",
    "when": "2026-04-27T05:50:00+07:00",
    "why": "Boss requested adjustment based on latest test results",
    "how": "Patched skill + documented test-based constraints"
  }
}
```

---

## References

**Related Skills:**
- hermes-session-manager
- hermes-os-memory-system-integration

**External Patterns:**
- Claude OS memory approach (session state)
- 5W1H journalism framework

**Related Facts (in store):**
- Fact #259+: Memory system operational

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-27 | Initial - Auto-memory audit with 5W1H extraction, importance scoring, Thai/English completion detection |

---

**Status:** Production Ready ✅  
**Test Coverage:** Validated with 2 memory saves  
**Next Review:** After 1 week of cron runs

---

**END OF SKILL DOCUMENTATION**
