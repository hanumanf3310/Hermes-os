---
name: hermes-os-communication-protocol-v2
title: Hermes OS Communication Protocol v2.0 (Hybrid Heartbeat)
version: 2.0.0
description: |
  Hybrid Heartbeat Protocol สำหรับ Hermes OS
  ผสมผสาน Pre-announce + Heartbeat + Checkpoint
  แก้ปัญหา timeout 60 วินาทีของระบบ
  
  Algorithm:
  - งาน < 30 วิ: Protocol 1.0 (บอกก่อน + ยืนยันตอนจบ)
  - งาน 30-60 วิ: Heartbeat ที่ 30 วิ + Completion
  - งาน > 60 วิ: Auto-resume + Checkpoint ทุก 45 วิ
  
tags:
  - protocol
  - heartbeat
  - timeout-handling
  - hybrid
  - v2
requires_tools:
  - terminal
author: Hermes OS
date: 2025-04-26
---

# Hermes OS Communication Protocol v2.0
## Hybrid Heartbeat Protocol

**Status:** ✅ OFFICIAL STANDARD (Replaces v1.0)  
**Approved by:** Boss  
**Effective Date:** 2025-04-26  
**Replaces:** hermes-os-communication-protocol v1.0  
**Timeout Handling:** 60 วินาที (forced by system)

---

## 🎯 Core Algorithm: Time-Based Response Strategy

```
┌─────────────────────────────────────────────────────────┐
│         TIME-BASED RESPONSE STRATEGY                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   0s         30s         45s         60s         90s   │
│   │          │           │           │           │     │
│   ▼          ▼           ▼           ▼           ▼     │
│ ┌────┐    ┌────┐      ┌────┐     ┌────┐     ┌────┐   │
│ │ ⏳ │    │ 🔄 │      │ 🔄 │     │ ↻↻ │     │ ✅ │   │
│ │Start│    │ HB │      │ CP │     │Auto│     │End │   │
│ └────┘    └────┘      └────┘     └────┘     └────┘   │
│                                                         │
│ Legend:                                                 │
│   ⏳ = Start message (Pre-announce)                      │
│   🔄 = Heartbeat (ยังทำอยู่)                           │
│   ↻↻ = Auto-resume (ถ้า timeout)                        │
│   ✅ = Completion confirmation                           │
│   HB = Heartbeat at 30s                                 │
│   CP = Checkpoint ทุก 45s                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Tier 1: Fast Tasks (< 30 seconds)

**Criteria:** งานที่ใช้เวลา < 30 วินาที

**Protocol:**
```markdown
⏳ [Hermes-OS] กำลัง {action}...
รายละเอียด: {what}
ระยะเวลา: ~{time}s (< 30s)
รอสักครู่นะคะ Boss 🙏

[ทำงาน...]

✅ **เสร็จแล้วค่ะ Boss!**

📋 **สรุปผล:**
...
```

**Example:**
```markdown
⏳ [Hermes-OS] กำลังสร้างไฟล์...
รายละเอียด: test.txt
ระยะเวลา: ~2s (< 30s)
รอสักครู่นะคะ Boss 🙏

✅ **เสร็จแล้วค่ะ Boss!**

📋 **สรุปผล:**
- ✅ สร้าง test.txt สำเร็จ
```

---

## 📋 Tier 2: Medium Tasks (30-60 seconds)

**Criteria:** งานที่ใช้เวลา 30-60 วินาที

**Protocol:**
```markdown
⏳ [Hermes-OS] กำลัง {action}...
รายละเอียด: {what}
ระยะเวลา: ~{time}s (ต้อง Heartbeat)
รอสักครู่นะคะ Boss 🙏

[ทำงาน 30 วินาที...]

🔄 **[Heartbeat]** ยังทำอยู่ค่ะ...
สถานะ: {current_status}
เวลาที่ใช้: 30s / ~{total}s
รอต่ออีกนิดนะคะ Boss 💪

[ทำงานต่อ...]

✅ **เสร็จแล้วค่ะ Boss!**

📋 **สรุปผล:**
...
```

**Example:**
```markdown
⏳ [Hermes-OS] กำลังสร้าง skill...
รายละเอียด: hermes-session-manager
ระยะเวลา: ~45s (ต้อง Heartbeat)
รอสักครู่นะคะ Boss 🙏

[ทำงาน 30 วิ...]

🔄 **[Heartbeat]** ยังทำอยู่ค่ะ...
สถานะ: กำลังสร้างไฟล์ core/...
เวลาที่ใช้: 30s / ~45s
รอต่ออีกนิดนะคะ Boss 💪

[ทำงานต่ออีก 15 วิ...]

✅ **เสร็จแล้วค่ะ Boss!**

📋 **สรุปผล:**
- ✅ Session state system
- ✅ Category detector
- ✅ CLI tool
- ✅ Skill created
```

---

## 📋 Tier 3: Long Tasks (> 60 seconds)

**Criteria:** งานที่ใช้เวลา > 60 วินาที

**Protocol:**
```markdown
⏳ [Hermes-OS] กำลัง {action}...
รายละเอียด: {what}
ระยะเวลา: ~{time}s (>60s, จะมี Checkpoint)
Checkpoint ทุก: 45 วินาที
รอสักครู่นะคะ Boss 🙏

[ทำงาน 45 วินาที...]

🔄 **[Checkpoint 1/X]** เสร็จส่วนแรกแล้วค่ะ...
✅ {completed_items}
⏳ เหลือ: {remaining_items}
เวลาที่ใช้: 45s
ประมาณอีก: ~{estimate}s

[ทำงานต่ออีก 45 วิ...]

🔄 **[Checkpoint 2/X]** กำลังทำส่วนต่อ...
⚠️ **[System Notice]** ข้อความก่อนหน้า timeout
🔄 น้องเมสยังทำอยู่นะคะ ไม่หายไปไหน 💪

[ทำงานต่อ...]

✅ **[Auto-Resume]** เสร็จแล้วค่ะ!

⚠️ *ข้อความก่อนหน้านี้ timeout เมื่อ 60s ที่แล้ว*
*น้องเมสทำต่อจนเสร็จแล้วค่ะ*

📋 **สรุปผลทั้งหมด:**
...

⏱️ **เวลารวม:** {actual_time}s
```

**Example:**
```markdown
⏳ [Hermes-OS] กำลัง deploy production...
รายละเอียด: อัปเดทเวอร์ชัน v2.0.0 บน AWS
ระยะเวลา: ~120s (>60s, จะมี Checkpoint)
Checkpoint ทุก: 45 วินาที
รอสักครู่นะคะ Boss 🙏

[ทำงาน 45 วิ...]

🔄 **[Checkpoint 1/3]** เสร็จส่วนแรกแล้วค่ะ...
✅ Build Docker image
✅ Push to ECR
⏳ เหลือ: Deploy to ECS, Health check
เวลาที่ใช้: 45s
ประมาณอีก: ~75s

[ทำงานอีก 45 วิ...]

🔄 **[Checkpoint 2/3]** กำลัง deploy...
⚠️ **[System Notice]** ข้อความก่อนหน้า timeout
🔄 น้องเมสยังทำอยู่นะคะ ไม่หายไปไหน 💪
✅ Deployed to ECS
⏳ เหลือ: Health check, DNS update

[ทำงานอีก 30 วิ...]

✅ **[Auto-Resume]** เสร็จแล้วค่ะ!

⚠️ *ข้อความก่อนหน้านี้ timeout เมื่อ 60s ที่แล้ว*
*น้องเมสทำต่อจนเสร็จแล้วค่ะ*

📋 **สรุปผลทั้งหมด:**
- ✅ Build Docker image
- ✅ Push to ECR
- ✅ Deploy to ECS
- ✅ Health check passed
- ✅ DNS updated

⏱️ **เวลารวม:** 120s
```

---

## 🔄 Special Cases

### Case: Tool Failure

```markdown
⏳ [Hermes-OS] กำลัง {action}...
รายละเอียด: {what}
...

❌ **[Failed]** ไม่สำเร็จค่ะ Boss

🔴 **Error:** {error_message}
📍 **Location:** {file}:{line}

💡 **แนวทางแก้ไข:**
[A] ลองใหม่
[B] ข้ามไปข้อต่อไป
[C] ยกเลิก
```

### Case: User Inquiry During Work

```markdown
Boss: เสร็จยัง?

🔄 **[Status Update]** ยังทำอยู่ค่ะ Boss

📊 **Progress:**
🔄 กำลัง: {current_task}
✅ เสร็จแล้ว: {completed}/{total}
⏱️ เวลา: {elapsed}s / ~{estimated}s

คาดว่าอีก ~{remaining}s เสร็จค่ะ 💪
```

---

## 📊 Comparison: v1.0 vs v2.0

| Scenario | v1.0 Result | v2.0 Result |
|----------|-------------|-------------|
| งาน 20 วิ | ✅ ทัน | ✅ ทัน (เหมือนเดิม) |
| งาน 45 วิ | ⚠️ Timeout | ✅ Heartbeat ที่ 30s |
| งาน 90 วิ | ⚠️ Timeout | ✅ Checkpoint ทุก 45s |
| งาน 120 วิ | ❌ Empty response | ✅ Auto-resume + Report |

---

## 🧪 Testing Protocol v2.0

```bash
# Test Tier 1 (< 30s)
hermes-test protocol --scenario=fast --duration=20

# Test Tier 2 (30-60s)
hermes-test protocol --scenario=medium --duration=45

# Test Tier 3 (> 60s)
hermes-test protocol --scenario=long --duration=90

# Test Heartbeat
hermes-test protocol --scenario=heartbeat

# Test Auto-resume
hermes-test protocol --scenario=resume
```

---

## 📝 Implementation Guide

### For Developers

```python
from hermes_os.protocol import HybridProtocol

protocol = HybridProtocol()

# Estimate time before execution
estimated_time = 75  # seconds

# Start with auto-detection
tier = protocol.detect_tier(estimated_time)
# Returns: "fast" | "medium" | "long"

# Execute with appropriate strategy
protocol.execute(
    action="deploy",
    estimated_time=estimated_time,
    callback=your_function
)
```

### Message Templates

```python
TEMPLATES = {
    "start": "⏳ [Hermes-OS] กำลัง {action}...\nรายละเอียด: {detail}\nระยะเวลา: ~{time}s{tier_note}\nรอสักครู่นะคะ Boss 🙏",
    
    "heartbeat": "🔄 **[Heartbeat]** ยังทำอยู่ค่ะ...\nสถานะ: {status}\nเวลาที่ใช้: {elapsed}s / ~{total}s\nรอต่ออีกนิดนะคะ Boss 💪",
    
    "checkpoint": "🔄 **[Checkpoint {num}/{total}]** {message}\n✅ {completed}\n⏳ เหลือ: {remaining}\nเวลา: {elapsed}s, ประมาณอีก: ~{estimate}s",
    
    "timeout_notice": "⚠️ **[System Notice]** ข้อความก่อนหน้า timeout\n🔄 น้องเมสยังทำอยู่นะคะ ไม่หายไปไหน 💪",
    
    "completion": "✅ **เสร็จแล้วค่ะ Boss!**\n\n📋 **สรุปผล:**\n{results}",
    
    "auto_resume": "✅ **[Auto-Resume]** เสร็จแล้วค่ะ!\n\n⚠️ *ข้อความก่อนหน้านี้ timeout เมื่อ {timeout_time}s ที่แล้ว*\n*น้องเมสทำต่อจนเสร็จแล้วค่ะ*\n\n📋 **สรุปผลทั้งหมด:**\n{results}\n\n⏱️ **เวลารวม:** {actual_time}s"
}
```

---

## 📚 Related Documents

- hermes-os-communication-protocol v1.0 (DEPRECATED)
- hermes-session-manager
- rtk-mes

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-04-26 | Hybrid Heartbeat Protocol (Replaces v1.0) |
| 1.0.0 | 2025-04-26 | Initial Basic Protocol |

---

**Approved by:** Boss (อนุมัติ Protocol D)  
**Official Status:** ACTIVE  
**Next Review:** After 1 week of usage
