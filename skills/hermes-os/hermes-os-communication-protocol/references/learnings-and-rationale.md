# Learnings & Rationale: Hermes OS Communication Protocol

## Why This Protocol Exists

**Problem Discovered:** Hermes Gateway has a **60-second timeout** on tool calls. If Hermes takes longer than 60 seconds to respond after tool execution, the system displays "Empty response" — which confused Boss about whether work was complete.

## The Trial-and-Error Discovery

### Initial Approach (Failed)
- Wait for all tools to complete, then send comprehensive summary
- Result: Frequent "Empty response" when operations took > 60s
- Boss couldn't tell if work was done or not

### Solution Found (After Multiple Iterations)

1. **Pre-announce** (before tool calls): Set expectations immediately
   - Format: `⏳ [Hermes-OS] กำลัง {action}...`
   - Boss knows work has started

2. **Auto-resume** (after timeout): Send confirmation with "[ย้อนหลัง]" marker
   - Format: `✅ [ย้อนหลัง] เสร็จแล้วค่ะ!`
   - Boss knows work completed (even if delayed)

3. **Visual indicators**: Use ✅ / ⏳ / ❌ so Boss knows status at a glance
   - No guessing needed

4. **Hybrid approach**: If timeout occurs, the follow-up message confirms completion

## Key Insight

Boss wanted **certainty**, not perfection. The protocol ensures:
- Boss **always knows** work has started (⏳)
- Boss **always knows** if work completed (✅) even after timeout
- Boss **never has to guess** whether "Empty response" means done or not

## Adaptation Required

This protocol requires Hermes to:
1. **Estimate time** before starting (build time awareness)
2. **Resume gracefully** after timeout (don't abandon ship)
3. **Use status indicators consistently** (train Boss to recognize patterns)

## Approved Pattern

Boss explicitly approved: **"บอกก่อนเริ่ม - ยืนยันตอนจบ"**

This is now **official standard** for all Hermes OS operations.

---

**Written:** 2025-04-26
**Author:** Hermes Assistant
**Status:** ✅ LOCKED - Official Protocol
