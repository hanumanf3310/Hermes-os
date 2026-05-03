---
name: hermes-fleet-bridge
description: Built-in skill for Hermes OS that seamlessly connects Hermes Agent with Enterprise Agent Fleet. Auto-routes tasks between Hermes and Fleet based on complexity.
category: hermes-os
---

# Hermes Fleet Bridge Skill

สกิล built-in สำหับ Hermes OS ที่เชื่อมต่อ Hermes Agent กับ Enterprise Agent Fleet แบบไร้รอยต่อ

## When to Use

สกิลนี้ถูกโหลดอัตโนมัติเมื่อ Hermes OS mode active (หลังจาก `hermes-os`)

## Features

1. **Auto-Routing**: ระบบตัดสินใจเองว่าใช้ Hermes หรือ Fleet
2. **Unified Commands**: `/fleet` commands ทำงานได้เลย
3. **Seamless Integration**: Boss ไม่ต้องรู้ว่าทำงานผ่านตัวไหน

## Commands

| Command | คำอธิบาย |
|---------|---------|
| `/fleet status` | ดูสถานะ Fleet |
| `/fleet plan "task"` | Dry run ก่อน execute |
| `/fleet run "task"` | ส่ง task ไป Fleet |
| `/fleet tasks` | ดู recent tasks |

## Auto-Routing Logic

Hermes จะวิเคราะห์ task อัตโนมัติ:

- **งานง่าย** (file, search, calendar) → Hermes handle เอง
- **งานซับซ้อน** → Auto-routing ไป Fleet
- **งาน critical** → Fleet + Safety Gate

ผลลัพธ์มาในรูปแบบเดียวกันหมด Boss ไม่ต้องรู้ว่าผ่านตัวไหน
