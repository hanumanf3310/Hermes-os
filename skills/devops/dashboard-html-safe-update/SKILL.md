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

### Issue 2: Graph not displaying

```javascript
// Check browser console
// 1. Open DevTools (F12)
// 2. Look for red error messages

// Common errors:
// - SyntaxError: Unexpected token
// - ReferenceError: data is not defined
// - TypeError: Cannot read property 'x' of undefined

// Fix: Validate JSON structure
const data = JSON.parse(jsonString); // Should not throw
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
