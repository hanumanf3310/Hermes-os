---
name: dashboard-html-safe-update
title: Safe Dashboard HTML Update Process
version: 1.0.0
description: |
  เครื่องมือและขั้นตอนการ update dashboard.html อย่างปลอดภัย
  ใช้สำหรับเพิ่ม nodes/links เข้า Hermes Memory Graph visualization
  โดยไม่ทำให้ graph visualization แตก
  
  บทเรียนจาก incident: Memory Enhancement Phase 1-3 integration
  ที่เกิด error "node not found: main_hermes" และ graph ไม่แสดง
  
tags:
  - dashboard
  - d3js
  - visualization
  - safety
  - validation
requires_tools:
  - terminal
  - file
  - skill_view
author: Hermes OS
based_on: dashboard-html-incident-2026-04-26
prerequisites:
  - Understanding of dashboard.html structure
  - Basic JSON knowledge
  - Browser DevTools familiarity
---

# Dashboard HTML Safe Update Process

## 🎯 Overview

Skill นี้รวบรวม best practices และ validation steps สำหรับการ update `dashboard.html` 
เพื่อป้องกันข้อผิดพลาดที่เกิดขึ้นจริง เช่น:
- Graph visualization ไม่แสดง
- JavaScript errors ("node not found")
- Broken links references
- JSON syntax errors

---

## 🚨 Problem Statement

ตอนทำ **Memory Enhancement Phase 1-3** เกิดปัญหาหลายครั้ง:

```
❌ Error: node not found: main_hermes
❌ Graph ไม่แสดงผล
❌ JSON syntax เสียจาก manual edit
```

ใช้เวลา debug นานกว่าที่ควรจะเป็น

---

## ✅ Safe Update Procedure

### Step 1: Pre-Update Checklist

```bash
📋 Before touching dashboard.html:

1. □ Extract existing node IDs
   grep -o '"id": "[^"]*"' dashboard.html | sort | uniq

2. □ List all target nodes for new links
   verify: target_node in existing_nodes

3. □ Backup original file
   cp dashboard.html dashboard.html.bak.$(date +%Y%m%d-%H%M%S)

4. □ Test current version opens correctly
   open in browser → verify graph displays
```

### Step 2: Validation Script

When validating the real dashboard, run the repo validator against the explicit file path:

```bash
rtk run "$HOME/.hermes/scripts/validate-dashboard-graph.py --json /home/hanuman3310/hermes-workspace/memory-graph/dashboard.html"
```

### Step 3: Safe Node Insertion

```javascript
// ⚠️ NEVER do this directly in Python without testing:
// BAD: content.replace("old", "new")  // Can break JSON

// ✅ Instead, use structured approach:

// 1. Identify insertion point
const insertAfterNode = "enterprise_fleet";

// 2. Format new nodes with proper indentation
const newNodes = [
    {
        id: "memory_enhancement",
        name: "🧠 Memory Enhancement",
        type: "memory",
        color: "#ec4899",
        size: 28,
        desc: "Claude OS inspired memory system"
    },
    // ... more nodes
];

// 3. Verify data structure before insert
console.log("Nodes valid:", validateNodes(newNodes));

// 4. Insert and verify JSON syntax
const updatedData = {
    ...existingData,
    nodes: [...existingNodes, ...newNodes]
};

// 5. Test parse
JSON.stringify(updatedData); // Throws if invalid
```

### Step 4: Safe Link Insertion

```javascript
// Critical: Validate all link references exist

const newLinks = [
    {source: "memory_enhancement", target: "hermes_os_core", type: "extends"},
    // ... more links
];

// Validation
const nodeIds = new Set(data.nodes.map(n => n.id));
const invalidLinks = newLinks.filter(l => 
    !nodeIds.has(l.source) || !nodeIds.has(l.target)
);

if (invalidLinks.length > 0) {
    throw new Error(`Invalid links: ${JSON.stringify(invalidLinks)}`);
}
```

### Step 4.5: Report-first change control for governance-sensitive edits

If the user explicitly asks to "report first" before editing, do not patch immediately.

1. Inspect the current page and summarize exactly what will change.
2. State which file(s) are in scope and which are out of scope.
3. Confirm whether the page is intended to remain read-only.
4. Only then apply the patch.

This is especially important when the requested outcome is:
- removing CRUD controls entirely
- preserving read-only behavior for governance dashboards
- changing summary/legend text without changing data flow

### Step 4.6: Anti-loop checkpoint rule

When the requested change risks becoming an endless audit or repeated refinement loop, stop and insert an explicit checkpoint before doing more work.

Use a checkpoint to decide one of three paths:
- continue with the current plan,
- switch to a better approach,
- or stop because the current state is already good enough.

Prefer a checkpoint when:
- the dashboard is already current and the user asks for a small update, not a re-audit,
- the same file keeps pulling the workflow back into old context,
- the work starts revisiting prior reports instead of changing the live artifact,
- or the user explicitly warns about infinite-loop behavior.

At the checkpoint, report only:
- what is already current,
- what still needs to change,
- and the go/no-go decision.

Do not keep expanding scope past the checkpoint unless the user clearly asks for it.

### Step 4.6: Read-only dashboard rule

For Hermes Memory Graph / Fact governance dashboards:
- do not add UI actions for create/update/delete unless the user explicitly asks for CRUD controls
- keep the surface read-only by default
- if CRUD endpoints exist in the backend, the dashboard may mention them in facts or legends, but it must not expose buttons/forms for them
- when enforcing read-only mode, verify that the only visible controls are navigation/inspection controls (e.g. reset, physics, export) and not content mutation controls

---

## 🔌 Debugging Common Issues

### Issue 1: "node not found: X"

```bash
# Find if node exists
grep '"id": "X"' dashboard.html

# If not found, check similar names
grep '"id": ".*X.*"' dashboard.html

# Compare with link references
grep '"source\|target": "X"' dashboard.html
```

**Solution:**
1. Find correct node ID
2. Replace broken reference
3. Verify node exists before link

### Issue 1.5: Validator reports only a few nodes while browser renders many

**Symptom:** browser runtime shows the graph is healthy (for example `data.nodes.length` and SVG circles are high, missing refs are zero), but `validate-dashboard-graph.py` reports `nodes=3` or many missing references.

**Root cause pattern:** the validator may be parsing the static JavaScript arrays with a naive split such as `split('],', 1)`. This breaks when node objects contain nested arrays, for example `impact_scope: [...]`, and truncates the nodes array before the real end.

**Fix:** update the validator parser to extract the top-level `nodes` / `links` arrays with bracket-aware parsing that respects quoted strings and nested brackets. Then rerun:

```bash
rtk run "$HOME/.hermes/scripts/validate-dashboard-graph.py --json /home/hanuman3310/hermes-workspace/memory-graph/dashboard.html"
```

**Bracket-aware injection pattern (Python):**

```python
#!/usr/bin/env python3
from pathlib import Path

dashboard = Path("/home/hanuman3310/hermes-workspace/memory-graph/dashboard.html")
content = dashboard.read_text()

def find_close_bracket(content, start_idx):
    """Find the ']' that closes the array starting at start_idx,
    accounting for strings, nested braces, and escape sequences."""
    brace = 0
    in_string = False
    escape = False
    for i in range(start_idx, len(content)):
        ch = content[i]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == '{':
                brace += 1
            elif ch == '}':
                brace -= 1
            elif ch == ']':
                if brace == 0:
                    return i
    return -1

def find_last_brace(content, end_pos, start_pos):
    """Find the index of the closing '}' of the last object
    in the range [start_pos, end_pos]."""
    bracket = 0
    in_str = False
    esc = False
    for j in range(end_pos - 1, start_pos - 1, -1):
        ch = content[j]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == '}':
                bracket += 1
                if bracket == 1:
                    return j
            elif ch == '{':
                bracket -= 1
    return -1

# Locate arrays
nodes_start = content.find('"nodes": [') + len('"nodes": [')
nodes_end   = find_close_bracket(content, nodes_start)
links_start = content.find('"links": [', nodes_end) + len('"links": [')
links_end   = find_close_bracket(content, links_start)

# Find last item braces
last_node_brace = find_last_brace(content, nodes_end, nodes_start)
last_link_brace = find_last_brace(content, links_end, links_start)

# Inject after last_node_brace + 1
new_node_entry = (
    "\n                ,\n"
    "                {\n"
    '                    "id": "new_feature_x",\n'
    '                    "label": "New Feature X",\n'
    '                    "description": "...",\n'
    '                    "type": "feature"\n'
    "                }")
content = content[:last_node_brace + 1] + new_node_entry + content[last_node_brace + 1:]

# Re-calc links bounds after node injection (indices shift)
# ... repeat find_close_bracket / find_last_brace on updated content
new_link_entry = "..."
# content = content[:last_link_brace + 1] + new_link_entry + content[last_link_brace + 1:]

# Save
Path("dashboard.html").write_text(content, encoding="utf-8")
print("Injected safely")
```

**Key safety rules:**
- Never use `content.replace()`, `split('],')`, or regex on the raw JS object.
- Always account for `"` inside strings and `\\` escape sequences.
- After injecting a node, re-locate the links array because character offsets shift.
- Verify by browser runtime (`data.nodes.length`) and grep (`grep '"id": "new_feature_x"'`), not by a validator whose parser may share the same naive split bug.

**Verification:** validator counts must match browser runtime counts:

```javascript
({
  dataNodes: data.nodes.length,
  dataLinks: data.links.length,
  circles: document.querySelectorAll('circle').length,
  lines: document.querySelectorAll('line').length,
  missingRefs: data.links.filter(l => !new Set(data.nodes.map(n => n.id)).has(typeof l.source === 'object' ? l.source.id : l.source) || !new Set(data.nodes.map(n => n.id)).has(typeof l.target === 'object' ? l.target.id : l.target)).length
})
```

### Issue 1.6: Graph crashes from an accidental array hole / double comma

**Symptom:** the dashboard page contains the new node text and the raw JavaScript may pass syntax checks, but the D3 force simulation fails with an error like:

```text
TypeError: Cannot set properties of undefined (setting 'index')
```

or the browser render count is `circles: 0`, `lines: 0` even though the static text exists.

**Root cause pattern:** an insertion added an extra comma between node objects, creating a sparse array entry / `undefined` node:

```javascript
{ /* previous node */ },

,
{ id: "new_node", ... }
```

JavaScript can parse this, but D3 receives an `undefined` node and crashes when assigning indexes.

**Fix:** inspect the inserted node boundary and remove the stray comma/blank sparse entry so the array is contiguous:

```javascript
{ /* previous node */ },
{ id: "new_node", ... }
```

**Verification:** after the fix, run both structural and runtime checks:

```bash
rtk run "node --check /tmp/dashboard_inline.js"
rtk run "$HOME/.hermes/scripts/validate-dashboard-graph.py --json /home/hanuman3310/hermes-workspace/memory-graph/dashboard.html"
```

Then browser-check rendered counts match validator counts:

```javascript
({
  circles: document.querySelectorAll('circle').length,
  lines: document.querySelectorAll('line').length,
  bodyHasNewNode: document.body.innerText.includes('New Node Name')
})
```

### Issue 2: Graph not displaying

```javascript
// Check browser console
// 1. Open DevTools (F12)
// 2. Look for red error messages

// Common errors:
// - SyntaxError: Unexpected token
// - ReferenceError: data is not defined
// - TypeError: Cannot read property 'x' of undefined
// - TypeError: Cannot set properties of undefined (setting 'index')

// Fix: Validate JSON structure and inspect for sparse array entries / double commas
const data = JSON.parse(jsonString); // Should not throw for JSON payloads
```

### Issue 3: Blank canvas

```bash
# Check D3.js loaded
curl -sI https://d3js.org/d3.v7.min.js | head -1

# Check console for CORS errors

# Check width/height values
grep -E "const (width|height)" dashboard.html

# Should be:
# const width = window.innerWidth;
# const height = window.innerHeight;
```

---

## 📝 Checklist Template

```markdown
## Dashboard Update Checklist

### Pre-Update
- [ ] Extract all existing node IDs
- [ ] Verify link target nodes exist
- [ ] Backup dashboard.html
- [ ] Document changes

### During Update
- [ ] Run validation script
- [ ] Add nodes first, then links
- [ ] Format proper JSON
- [ ] Check indentation

### Post-Update
- [ ] Open in browser
- [ ] Check console for errors
- [ ] Verify graph displays
- [ ] Test node hover/click
- [ ] Test search functionality
- [ ] If any fail → restore from backup

### Sign-off
- [ ] Visual inspection passed
- [ ] No console errors
- [ ] All interactive features work
```

---

## 🎨 Color Coding Standards

| Type | Color | Usage |
|------|-------|-------|
| Memory (existing) | #a855f7 | Original purple |
| Memory (new) | #ec4899 | Pink for additions |
| Categories | #f97316 | Orange |
| Skills | #3b82f6 | Blue |
| Projects | #2ecc71 | Green |
| Missing | #e63946 | Red for gaps |

### Fact* / Fact+* dashboard-specific pattern

When adding `Fact*` or `Fact+*` visualization support:
- give `Fact*` a dedicated `type` or flag such as `fact_star`
- give `Fact+*` a dedicated `type` or flag such as `fact_plus_star`
- use distinct fill/stroke colors so `Fact*`, `Fact+`, and `Fact+*` are visually separable from regular memory nodes
- include the star fields in `exportGraph()` so exported JSON preserves governance metadata
- render separate sidebar sections for `fact_type`, `verify_before_use`, `importance_level`, `star_reason`, `impact_scope`, and `verification_status`
- if backend summary stats can drift from the data actually rendered, compute header counts from the same payload used to render nodes/links (for example `data.nodes`) instead of trusting a separate stats object
- verify the DOM after load with browser/console checks, not by static inspection alone

---

## 📡 Incident Report

**Date:** 2026-04-26  
**Project:** Hermes Memory Enhancement Phase 1-3  
**Impact:** Graph visualization failed for ~30 minutes  

**Root Causes:**
1. Added links referencing non-existent node `main_hermes`
2. Python string manipulation corrupted JSON structure
3. Insufficient testing before declaring complete

**Prevention:**
- Always validate node references
- Use validation script before updates
- Check browser console before sign-off
- Maintain backup strategy

**Documentation:**
- Full post-mortem: reports/POSTMORTEM-dashboard-html-incident.md
- Facts: #266, #267, #268

---

## 🎯 Usage Example

```bash
# Safe update workflow example

# 1. Backup
cp dashboard.html dashboard.html.backup

# 2. Validate proposed changes
python3 validate_dashboard_update.py \
    dashboard.html \
    proposed_changes.json

# 3. Apply if valid
# ... apply changes ...

# 4. Test
open dashboard.html  # Check browser

# 5. Review
# - No console errors?
# - Graph displays?
# - Nodes clickable?
# ✓ All pass → commit
# ✗ Any fail → restore backup
```

---

## 📚 References

- D3.js Force Simulation: https://github.com/d3/d3-force
- JSON Validation: https://jsonlint.com/
- Original dashboard: /home/hanuman3310/hermes-workspace/memory-graph/dashboard.html
- Backup location: /home/hanuman3310/hermes-workspace/memory-graph/*.backup

---

**Maintainer:** Hermes OS  
**Version:** 1.0.0  
**Last Updated:** 2026-04-26  
**Based on:** Real incident experience
