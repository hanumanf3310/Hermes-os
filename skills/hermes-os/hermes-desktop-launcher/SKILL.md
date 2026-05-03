---
name: hermes-desktop-launcher
description: |
  Skill Launcher สำหรับติดตั้งและใช้งาน Hermes Desktop (fathah/hermes-desktop)
  บน Ubuntu/WSL พร้อมความปลอดภัยและการตรวจสอบความขัดแย้งกับ Hermes OS ที่มีอยู่
version: 1.0.0
author: hanuman3310
category: hermes-os
tags:
  - hermes-desktop
  - gui
  - electron
  - desktop
  - launcher
requires_tools:
  - terminal
  - file
  - web
---

# Hermes Desktop Launcher Skill

## Overview

Skill Launcher สำหรับจัดการ Hermes Desktop - GUI companion สำหรับ Hermes Agent
GitHub: https://github.com/fathah/hermes-desktop

## Philosophy

- **Safety First**: Backup ก่อนติดตั้งเสมอ
- **No Conflict**: ตรวจสอบความขัดแย้งกับ Hermes OS ที่มีอยู่
- **Mobile Preserved**: เก็บ Telegram Gateway ไว้ใช้งานบนมือถือ
- **Boss Control**: ต้องได้รับอนุมัติก่อนทำการติดตั้ง

## Commands

| Command | รูปแบบ CLI | รูปแบบ Telegram | ผลลัพธ์ |
|---------|-----------|----------------|---------|
| `hermes-desktop check` | ✅ | ✅ | ตรวจสอบความพร้อมติดตั้ง |
| `hermes-desktop install` | ✅ | ⚠️ CLI Only | ติดตั้ง Hermes Desktop |
| `hermes-desktop start` | ✅ | ⚠️ CLI Only | เริ่มต้น Hermes Desktop |
| `hermes-desktop status` | ✅ | ✅ | ตรวจสอบสถานะ |
| `hermes-desktop backup` | ✅ | ⚠️ CLI Only | สำรอง Hermes |
| `hermes-desktop remove` | ✅ | ⚠️ CLI Only | ถอนการติดตั้ง |
| `hermes-desktop report` | ✅ | ✅ | แสดงรายงานความเข้ากันได้ |

## Prerequisites

### ระบบที่รองรับ
- ✅ Ubuntu 20.04+ / 22.04 / 24.04
- ✅ WSL2 (Windows 10/11)
- ✅ macOS 12+ (Intel/Apple Silicon)
- ✅ Debian-based distributions

### ความต้องการเบื้องต้น
- Node.js 18+ (มีอยู่: 22.22.2 ✅)
- npm 9+ (มีอยู่: 10.9.7 ✅)
- 4GB+ RAM (Desktop + Electron)
- 2GB+ Disk space

## ⚠️ IMPORTANT: INSTALLATION BLOCKED

**Status: FORBIDDEN - DO NOT INSTALL**

Hermes Desktop installation is **BLOCKED** by Boss directive. Despite technical compatibility, installation poses risks to Hermes OS stability:

### Blocked Reasons
1. **Gateway Conflicts** - Cannot run Desktop Gateway alongside Telegram Gateway
2. **Database Locking** - SQLite session conflicts when CLI and Desktop both active
3. **Config Contention** - Risk of config corruption between interfaces
4. **Hermes OS Disruption** - Potential interference with control layer

### Alternative Commands (Safe)
```bash
hermes-desktop check      # ✅ Check compatibility (safe)
hermes-desktop report     # ✅ View compatibility report (safe)
hermes-desktop status     # ✅ Check if installed elsewhere (safe)
```

### FORBIDDEN Commands
```bash
hermes-desktop install    # ❌ BLOCKED - Do not use
hermes-desktop start      # ❌ BLOCKED - Do not use
hermes-desktop remove     # ⚠️ Only if previously installed
```

## Original Installation Methods (BLOCKED)

~~Method 1: .deb Package~~ - **BLOCKED**
~~Method 2: AppImage~~ - **BLOCKED**
~~Method 3: Build from Source~~ - **BLOCKED**

For reference only - see Compatibility Report at:
`~/.hermes-os-mode/reports/HERMES_DESKTOP_COMPATIBILITY_REPORT.md`

## Safety Checks

ก่อนติดตั้ง ระบบจะตรวจสอบ:

1. ✅ Hermes ที่มีอยู่จะถูก backup อัตโนมัติ
2. ✅ Config files (`~/.hermes/config.yaml`, `~/.hermes/.env`) จะถูก preserve
3. ✅ Telegram Gateway จะถูกตั้งค่าไม่ให้ชนกัน
4. ✅ Node.js version compatibility
5. ✅ OS compatibility

## Post-Installation Configuration

```yaml
# ~/.hermes/config.yaml - Desktop section
hermes_desktop:
  installed: true
  version: "0.2.3"
  install_date: "2026-04-29"

  # Conflict prevention
  auto_start_gateway: false  # ใช้ Telegram Gateway ที่มีอยู่

  # UI preferences
  theme: dark
  language: th

  # Mobile settings
  mobile_primary: telegram    # เก็บ Telegram เป็น primary
  desktop_primary: gui        # Desktop สำหรับทำงานบน PC
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Hermes OS Controller                    │
│                    (hermes-os skill)                       │
└────────────────────┬──────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
┌────────▼────────┐   ┌────────▼────────┐
│ Hermes Desktop  │   │ Hermes Agent    │
│ (GUI Layer)     │   │ (CLI Core)      │
│                 │   │                 │
│ • Electron 39   │   │ • Terminal      │
│ • React 19      │   │ • Skills        │
│ • TypeScript 5.9│   │ • Tools         │
└────────┬────────┘   └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │   Shared Resources     │
         │   ~/.hermes/           │
         │   • config.yaml        │
         │   • .env               │
         │   • hermes-agent/      │
         │   • skills/            │
         │   • state.db           │
         └────────────────────────┘
```

## Mobile Strategy (Boss Requirement)

Hermes Desktop **ไม่รองรับ Mobile** โดยตรง (เป็น Desktop app)
แนะนำให้ใช้ **hybrid approach**:

### Primary Mobile Access: ✅ Telegram (เก็บไว้)
- ใช้ Telegram Gateway ที่มีอยู่
- ไม่ต้องตั้งค่าใหม่
- ทำงานบนมือถือได้ทุกที่

### Secondary Desktop GUI: Hermes Desktop
- ใช้บน PC/Laptop เมื่อต้องการ GUI
- Visual skill management
- Session browser
- Memory editor

### Integration
```
Mobile (Telegram) ────┐
                       ├──→ Hermes Gateway ──→ Hermes Agent Core
Desktop (GUI) ────────┘
```

## Risk Mitigation

| ความเสี่ยง | การป้องกัน |
|-----------|-----------|
| ทับ config เดิม | Backup ก่อนติดตั้ง |
| Gateway ชนกัน | ปิด auto-start ใน Desktop |
| Database lock | ใช้ทีละ interface |
| หายจาก mobile | เก็บ Telegram ไว้ |

## Troubleshooting

### Desktop ไม่ detect Hermes ที่มีอยู่
```bash
hermes-desktop backup
# แล้วลองติดตั้งใหม่
```

### Gateway conflict
```bash
# ใน Desktop: Settings → Gateway → Uncheck "Auto-start"
# ใช้ Telegram Gateway ที่มีอยู่แทน
```

### Session ไม่ sync ระหว่าง CLI และ Desktop
- ปิด CLI chat ก่อนเปิด Desktop
- หรือรอ 30 วินาทีระหว่างสลับ

## Integration with Hermes OS

```
/hermes-os status      → แสดง Hermes Desktop ในสถานะ
/hermes-desktop status → ตรวจสอบเฉพาะ Desktop
/hermes-os dashboard   → รวม Desktop status
```

## Policy Gateway

- **RTK**: ทุกคำสั่งติดตั้งผ่าน `rtk run`
- **UTC+7**: Normalize เวลาก่อน log
- **Evidence**: ต้องมี backup ก่อน install

## Testing Checklist

- [ ] Installation completes without error
- [ ] Existing Hermes config preserved
- [ ] Telegram Gateway still works
- [ ] Desktop detects existing sessions
- [ ] Skills are accessible in Desktop
- [ ] Mobile access (Telegram) unchanged
- [ ] Backup restored successfully (test)

## License

MIT - Compatible with Hermes OS

## References

- Compatibility Report: `~/.hermes/reports/HERMES_DESKTOP_COMPATIBILITY_REPORT.md`
- Upstream: https://github.com/fathah/hermes-desktop
- Hermes OS: `~/.hermes/skills/hermes-os/`
