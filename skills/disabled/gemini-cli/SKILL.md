---
name: gemini-cli
description: สั่งงาน Google Gemini CLI - ใช้ Gemini API ผ่าน command line เขียนโค้ด วิเคราะห์ และสร้าง content
skills: []
---

# Gemini CLI Skill

## คำอธิบาย
สกิลสำหรับเรียกใช้ Google Gemini ผ่าน CLI หรือ API โดยตรง

## ความต้องการเบื้องต้น
- `pip install google-generative-ai`
- หรือ `pip install google-generativeai`
- Gemini API Key (จาก Google AI Studio)

## การตั้งค่า
```bash
export GEMINI_API_KEY="your-api-key-here"
```

## วิธีใช้งาน

### 1. ผ่าน CLI Script (ที่น้องเมสสร้างให้)
```bash
# Generate code
gemini "เขียน Python function สำหรับ sort list"

# Analyze file
gemini --file script.py "วิเคราะห์โค้ดนี้"

# Multi-turn chat
gemini --chat "สร้าง API endpoint สำหรับ user login"
```

### 2. ผ่าน Python (ใน Hermes)
```python
from skills.autonomous-ai-agents.gemini_cli import generate_with_gemini

response = generate_with_gemini(
    prompt="เขียน docstring สำหรับฟังก์ชันนี้",
    model="gemini-pro"
)
```

## โมเดลที่รองรับ
- `gemini-pro` - สำหรับ text (ฟรี)
- `gemini-pro-vision` - รองรับรูปภาพ
- `gemini-ultra` - รุ่น advanced

## เปรียบเทียบกับสกิลอื่น
| สกิล | Provider | Strength |
|------|----------|----------|
| **gemini-cli** | Google | ฟรี, เร็ว, context 1M tokens |
| claude-code | Anthropic | Code quality สูง |
| codex | OpenAI | GPT-4, แพงกว่า |
| opencode | Community | Open source |

## เมื่อใช้
- ต้องการ **ฟรี** quota (1,500 req/day)
- ต้องการ **context ยาว** (1M tokens)
- ต้องการ **multimodal** (text + image)
- ทำงานพร้อมกับ **Google Cloud ecosystem**

## Limitations
- ไม่ support function calling เท่า Claude
- Code quality อาจน้อยกว่า Claude บางกรณี

## Troubleshooting
- `pip install google-generativeai`
- `export GEMINI_API_KEY=xxx`
- Test: `python -c "import google.generativeai; print('OK')"`
