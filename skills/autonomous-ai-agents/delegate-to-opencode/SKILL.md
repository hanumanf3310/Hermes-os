---
name: delegate-to-opencode
description: สั่งงาน OpenCode CLI เป็น sub-agent เขียนโค้ด แล้ว Hermes ตรวจสอบผลลัพธ์ รายงาน Boss
skills: []
---

# Delegate to OpenCode CLI

สกิลสำหรับให้ Hermes สั่งงาน OpenCode CLI (ฟรี quota หลาย models) แล้วตรวจสอบผลลัพธ์

## Workflow

```
Boss สั่งงาน → Hermes วิเคราะห์ → สั่ง OpenCode CLI → รอผล
                                                    ↓
Boss ← รายงาน ← Hermes ตรวจสอบ ← ผลลัพธ์
         ↑                              |
         └──────── ถ้าผิด ──────────────┘
              สั่ง OpenCode CLI แก้
```

## การใช้งาน

### 1. ผ่าน Hermes (อัตโนมัติ)
```
Boss: "เขียน Python script สำหรับจัดการ CSV"

Hermes:
├── วิเคราะห์: เป็นงานเขียนโค้ด → Delegate ให้ OpenCode CLI
├── สั่ง OpenCode CLI (Big Pickle model):
│   "npx opencode run --agent build --model opencode/big-pickle"
├── รอผลลัพธ์ (~30-90 วินาที)
├── ตรวจสอบ:
│   ├── Syntax check ✅
│   ├── Logic check ✅
│   └── Error handling ✅
└── รายงาน Boss:
    "OpenCode CLI (Big Pickle) สร้างโค้ดเสร็จแล้ว
     ✅ ผ่านการตรวจสอบทั้งหมด
     โค้ดสมบูรณ์พร้อมใช้งาน"
```

### 2. ถ้า model หลัก fail → Auto fallback
```
OpenCode Big Pickle fail → ลอง MiniMax → ลอง Nemotron → ลอง GPT-5 Nano
         ↓
    Hermes fallback (ถ้าทุก model fail)
         ↓
    รายงาน Boss พร้อมผลลัพธ์
```

## ข้อดี

| ข้อดี | รายละเอียด |
|-------|-----------|
| ฟรี | OpenCode ใช้ฟรีหลาย models |
| เร็วกว่า Gemini | ~30-90 วิ vs ~120+ วิ (Gemini CLI) |
| Auto file creation | สร้างไฟล์จริง ไม่ต้อง copy-paste |
| Multi-model fallback | 4 models พร้อม fallback chain |
| ไม่ต้อง auth ซับซ้อน | ใช้งานได้ทันที |

## Model Fallback Chain

| ลำดับ | Model | คุณสมบัติ |
|--------|-------|-----------|
| 1 | `opencode/big-pickle` | เร็ว แม่นยำ |
| 2 | `opencode/minimax-m2.5-free` | Free tier |
| 3 | `opencode/nemotron-3-super-free` | Free tier |
| 4 | `opencode/gpt-5-nano` | สำรอง |

## Requirements

- Node.js + npm (npx)
- OpenCode CLI (ติดตั้งผ่าน npm): `npm install -g opencode-ai`

## Usage

```python
from skills.autonomous_ai_agents.delegate_to_opencode import OpenCodeDelegator

delegator = OpenCodeDelegator()
result = delegator.delegate(
    task="สร้าง BMI Calculator พร้อม docstring",
    output_path="./bmi.py",
    focus=['syntax', 'logic', 'docstring']
)

print(f"✅ Model: {result['model_used']}")
print(f"✅ Score: {result['validation']['score']}/4")
print(f"📄 File: {result['file_path']}")
```

## Troubleshooting

### OpenCode ไม่ทำงาน
```bash
npx opencode --version  # เช็ค version
npx opencode models     # ดู models ที่มี
```

### Model name ไม่ถูกต้อง
ต้องมี prefix `opencode/` เสมอ:
- ✅ `opencode/big-pickle`
- ❌ `big-pickle` (ไม่มี prefix)

### Permission denied (WSL)
ใช้ `~/workspace/` แทน `/tmp/` (OpenCode ไม่มีสิทธิ์เขียน /tmp/ บน WSL)
