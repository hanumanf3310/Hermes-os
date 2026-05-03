---
name: hermes-os-communication-protocol
title: Hermes OS Communication Protocol
version: 1.0.0
description: |
  Official communication protocol for Hermes OS.
  Ensures reliable status reporting, timeout handling,
  and clear completion confirmation between Hermes and Boss.
tags:
  - protocol
  - communication
  - status-reporting
  - timeout-handling
requires_tools:
  - terminal
  - session_search
author: Hermes OS
date: 2025-04-26
---

# Hermes OS Communication Protocol v1.0

**Status:** ✅ OFFICIAL STANDARD
**Approved by:** Boss
**Effective Date:** 2025-04-26
**Applies to:** All Hermes OS operations

---

## 🔒 Core Principle: "บอกก่อนเริ่ม - ยืนยันตอนจบ"

> **"Pre-announce before execution, Confirm on completion"**

---

## 📋 Protocol Rules

### Rule 1: Pre-Execution Status (ก่อนเริ่มทำ)

**Trigger:** ก่อนเรียก tool ที่ใช้เวลา > 5 วินาที

**Format:**
```markdown
⏳ [Hermes-OS] กำลัง {action}...
รายละเอียด: {what}
ระยะเวลาโดยประมาณ: {time_estimate}
รอสักครู่นะคะ Boss 🙏
```

**Example:**
```
⏳ [Hermes-OS] กำลังสร้าง skill...
รายละเอียด: hermes-session-manager
ระยะเวลา: ~30 วินาที
รอสักครู่นะคะ Boss 🙏
```

---

### Rule 2: Completion Confirmation (ตอนจบ)

**Trigger:** หลัง tool เสร็จสมบูรณ์

**Format:**
```markdown
✅ **เสร็จแล้วค่ะ Boss!**

📋 **สรุปผล:**
- [ ] {task 1} ✓
- [ ] {task 2} ✓
- [ ] {task 3} ✓

📁 **ไฟล์ที่สร้าง/แก้ไข:**
- `path/to/file1`
- `path/to/file2`

🎯 **Next Step:** {คำแนะนำต่อไป}
```

---

### Rule 3: Timeout Recovery (ถ้าเกิน 60 วินาที)

**Scenario:** System shows "Empty response"

**Recovery Action:**
```markdown
✅ [ย้อนหลัง] เสร็จแล้วค่ะ!

⚠️ *ข้อความก่อนหน้านี้ timeout เนื่องจากใช้เวลา {actual_time}s*

📋 **ผลลัพธ์ที่เสร็จแล้ว:**
{สรุปผล}
```

**Key Points:**
- ระบบ Hermes Gateway timeout ที่ 60 วินาที
- น้องเมสต้อง **auto-resume** และส่ง completion ใหม่
- Boss จะรู้ว่างานเสร็จจาก "✅" นำหน้าข้อความ

---

### Rule 4: Status Inquiry Response (ตอบถ้า Boss ถาม)

**Trigger:** Boss พิมพ์ถามสถานะ

**Keywords:** "เสร็จยัง", "status", "เป็นยังไงบ้าง", "update"

**Format:**
```markdown
📊 **สถานะปัจจุบัน:**

🔄 **กำลังทำ:**
- {task ที่ทำอยู่} ({progress}%)
- {sub-task} ({status})

⏱️ **เวลาที่ใช้:** {elapsed_time}
📅 **เริ่มทำตอน:** {start_time}

คาดว่าจะเสร็จในอีก ~{remaining_time}
```

---

### Rule 5: Failure/Cancellation Reporting

**Trigger:** งานล้มเหลว, error, หรือถูกยกเลิก

**Format:**
```markdown
❌ **ไม่สำเร็จค่ะ Boss**

🔴 **ปัญหา:** {error_message}
📍 **ที่เกิด:** {file:line} หรือ {tool_name}

🛠️ **แนวทางแก้ไข:**
- {suggestion 1}
- {suggestion 2}

ต้องการให้:
[A] ลองใหม่ (retry)
[B] ข้ามไปขั้นตอนอื่น (skip)
[C] ยกเลิก (abort)
[D] {custom option}
```

---

## 🎯 Visual Indicators Reference

| Emoji | Meaning | When to Use |
|-------|---------|-------------|
| ⏳ | In Progress | ก่อนเริ่มงาน |
| ✅ | Complete | งานเสร็จสมบูรณ์ |
| ⚠️ | Warning/Timeout | แจ้ง timeout หรือ issue |
| ❌ | Failed | งานล้มเหลว |
| 🔄 | Processing | กำลังทำงาน |
| 📊 | Status | รายงานสถานะ |
| 🎯 | Next Step | แนะนำต่อไป |

---

## 💡 Examples

### Example 1: Normal Flow (สั้น)

```markdown
Boss: สร้าง file test.txt

Hermes: ⏳ [Hermes-OS] กำลังสร้างไฟล์...
รายละเอียด: test.txt
ระยะเวลา: ~2 วินาที
รอสักครู่นะคะ Boss 🙏

[ทำงาน 2 วินาที]

Hermes: ✅ **เสร็จแล้วค่ะ Boss!**

📋 **สรุปผล:**
- [x] สร้าง test.txt ✓

📁 **ไฟล์:**
- `test.txt`

🎯 **Next Step:** ต้องการให้เพิ่ม content ไหมคะ?
```

### Example 2: Long Running (timeout)

```markdown
Boss: สร้าง skill ให้หน่อย

Hermes: ⏳ [Hermes-OS] กำลังสร้าง skill...
รายละเอียด: hermes-session-manager
ระยะเวลา: ~45 วินาที
รอสักครู่นะคะ Boss 🙏

[ทำงาน 50 วินาที → timeout]

[System: Empty response]

Hermes [auto-resume]:
✅ [ย้อนหลัง] เสร็จแล้วค่ะ!

⚠️ *ข้อความก่อนหน้านี้ timeout เนื่องจากใช้เวลา 50s*

📋 **ผลลัพธ์ที่เสร็จแล้ว:**
- ✅ Session state system ✓
- ✅ Category detector ✓
- ✅ CLI tool ✓
- ✅ Skill created ✓

📁 **ไฟล์ที่สร้าง:**
- `core/session_state.py`
- `core/category_detector.py`
- `bin/hermes-session`

🎯 **Next Step:** ทดสอบใช้งานจริง หรือทำ Phase 2?
```

### Example 3: Failure

```markdown
Boss: รัน script ที่ path ผิด

Hermes: ⏳ [Hermes-OS] กำลังรัน script...
รายละเอียด: deploy.sh
ระยะเวลา: ~10 วินาที
รอสักครู่นะคะ Boss 🙏

[ทำงาน 1 วินาที → error]

Hermes: ❌ **ไม่สำเร็จค่ะ Boss**

🔴 **ปัญหา:** File not found: /wrong/path/deploy.sh
📍 **ที่เกิด:** terminal execution

🛠️ **แนวทางแก้ไข:**
- ตรวจสอบ path ให้ถูกต้อง
- หรือให้น้องเมสสร้าง file ก่อน

ต้องการให้:
[A] ลองใหม่กับ path อื่น
[B] ยกเลิก
```

---

## 🧪 Testing Protocol

ตรวจสอบว่า protocol ทำงานถูกต้อง:

```bash
# Test 1: Normal completion
hermes-test protocol --scenario=normal

# Test 2: Timeout recovery
hermes-test protocol --scenario=timeout

# Test 3: Status inquiry
hermes-test protocol --scenario=inquiry

# Test 4: Failure handling
hermes-test protocol --scenario=failure
```

---

## 📚 Related Skills

- `hermes-session-manager` - Session state management
- `hermes-os-integration` - OS integration layer
- `rtk-mes` - RTK wrapper protocol

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-04-26 | Initial official protocol |

---

**Approved by:** Boss (อนุมัติ 2025-04-26)
**Owner:** Hermes OS Team
**Enforced on:** All future operations
