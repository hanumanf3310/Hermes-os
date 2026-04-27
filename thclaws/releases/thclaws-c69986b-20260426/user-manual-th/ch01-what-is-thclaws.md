# บทที่ 1 — thClaws คืออะไร?

![logo](../user-manual-img/logo/thClaws-logo-line-art-banner.png)

thClaws คือ **workspace สำหรับ AI agent ที่เขียนด้วย Rust แบบ native** ซึ่ง
รันบนเครื่องของคุณเอง ไม่ได้ทำได้แค่เขียนโค้ด แต่ยังแก้โค้ด ทำงาน
อัตโนมัติแทนคุณ ค้น knowledge base ของคุณ และประสานงานทีม agent
หลายตัวได้ — ทั้งหมดรวมอยู่ใน binary เดียว แค่บอกเป็นภาษาธรรมชาติว่า
ต้องการอะไร แล้ว agent จะอ่านไฟล์ รันคำสั่ง ใช้ tool และพูดคุยโต้ตอบ
กับคุณระหว่างทำงาน

สามอินเทอร์เฟซ รวมอยู่ใน binary เดียว:

- **Desktop GUI** (`thclaws` โดยไม่ใส่ flag) — หน้าต่าง native ประกอบด้วย
  แท็บ Terminal ที่รัน REPL ตัวเดียวกับโหมด `--cli`, แท็บ Chat แบบ
  streaming, Files browser และแท็บ Team (ตัวเลือกเสริม)
- **CLI REPL** (`thclaws --cli`) — prompt โต้ตอบใน terminal เหมาะกับการใช้
  ผ่าน SSH, เซิร์ฟเวอร์ headless หรือเมื่อไม่ต้องการ overhead ของ GUI
- **โหมดไม่โต้ตอบ** (`thclaws -p "prompt"` รูปแบบเต็มคือ `--print`)
  — รันแค่หนึ่ง turn แล้วออก สะดวกสำหรับสคริปต์ CI pipeline หรือ
  one-liner ใน shell

## สิ่งที่ทำให้ thClaws แตกต่าง

- **native บนเครื่อง คุมข้อมูลเอง** — Rust binary ตัวเดียว ไม่ต้องมี service
  เบื้องหลัง ไม่ต้อง cloud จะรันกับ Ollama แบบ offline ล้วน ๆ ก็ได้
- **รองรับหลาย provider อย่างเท่าเทียม** — Anthropic, OpenAI, Gemini,
  DashScope, OpenRouter, Ollama (+ Anthropic-compat) และ Agentic Press
  อยู่ใน binary เดียว สลับกลางคันด้วย `/model` หรือ `/provider` ได้
  ([บทที่ 6](ch06-providers-models-api-keys.md))
- **เหมาะกับทุกสายงาน ไม่ใช่แค่วิศวกร** — Chat tab แบบ streaming สำหรับ
  นักวิจัย PM ฝ่ายกฎหมาย/การตลาด Terminal REPL สำหรับวิศวกร — ใช้
  session และ config ชุดเดียวกัน สลับไปมาได้โดยไม่เสีย context
  ([บทที่ 4](ch04-desktop-gui-tour.md))
- **ยึดมาตรฐานเปิด ไม่ผูกกับ vendor** — ใช้
  [MCP](https://modelcontextprotocol.io/) สำหรับ tool,
  [`AGENTS.md`](https://agents.md) สำหรับ instruction (มาตรฐานที่
  Google, OpenAI, Cursor, Sourcegraph, Factory ใช้), `SKILL.md` สำหรับ
  workflow และ `.mcp.json` สำหรับตั้งค่า MCP server — config
  ขนย้ายไปใช้กับเครื่องมืออื่นที่พูดมาตรฐานเดียวกันได้
- **ประกอบ agent เองจาก building block** —
  **Skill** ([บทที่ 12](ch12-skills.md)) สำหรับ workflow ที่ใช้ซ้ำได้,
  **MCP server** ([บทที่ 14](ch14-mcp.md)) สำหรับเสียบ tool ภายนอก
  (GitHub, DB, Browser, Slack ฯลฯ),
  **Plugin** ([บทที่ 16](ch16-plugins.md)) สำหรับแพ็กทุกอย่างรวมกัน,
  **Knowledge base** ([บทที่ 9](ch09-knowledge-bases-kms.md)) สำหรับ
  wiki ที่ agent ค้นและอ่านเอง,
  **Sub-agent** ([บทที่ 15](ch15-subagents.md)) กับ
  **Agent Team** ([บทที่ 17](ch17-agent-teams.md)) สำหรับงานขนาน
- **จำสิ่งที่สำคัญในระยะยาว** — `AGENTS.md` (หรือ `CLAUDE.md`) ในโปรเจกต์
  โดนฉีดเข้า prompt อัตโนมัติ memory store ที่
  `~/.config/thclaws/memory/` เก็บข้อเท็จจริงที่ agent เรียนรู้เกี่ยวกับ
  ตัวคุณและโปรเจกต์ ทั้งหมดเป็น markdown ที่คุณอ่าน แก้ไข หรือ commit ได้
  ([บทที่ 8](ch08-memory-and-agents-md.md))
- **ความปลอดภัยมาก่อน** — filesystem sandbox จำกัดขอบเขตของ tool
  ไฟล์อยู่ที่ working directory tool ที่เปลี่ยนสถานะต้อง approve
  (ยกเว้นจะตั้ง auto-approve เอง) API key เก็บใน OS keychain หรือ
  `.env` ตามที่คุณเลือกตอนเปิดใช้ครั้งแรก
  ([บทที่ 5](ch05-permissions.md))
- **Settings อยู่ในไฟล์ JSON ไฟล์เดียว** — permission mode, thinking
  budget, allowed/disallowed tool, endpoint ของ provider, KMS ที่แนบไว้
  รวมอยู่ใน `.thclaws/settings.json` (ระดับโปรเจกต์ commit ลง repo ได้)
  หรือ `~/.config/thclaws/settings.json` (ระดับผู้ใช้ทั้งระบบ)
- **Deploy งานที่สร้างเสร็จได้เลย** — landing page, web app, API และ
  agent ไปอยู่บน [Agentic Press Hosting](https://agentic-press.com)
  (ร่วมมือกับ SIS Cloud Service และ Artech.Cloud) ได้ หรือใช้ host
  อื่นก็ได้ — flow การ deploy มาในรูป plugin host จึงสลับเปลี่ยนได้
  ไม่มีการล็อก client
- **Shell escape** — ใส่ `!` นำหน้าบรรทัดใน REPL เพื่อรันคำสั่ง shell
  โดยตรง ไม่เสีย token ไม่มี prompt ขออนุมัติ (เช่น `! git status`)

## สิ่งที่คุณต้องมี

- OS ที่รองรับ: macOS (arm64 หรือ x86_64), Linux (arm64 หรือ x86_64)
  หรือ Windows (arm64 หรือ x86_64)
- API key ของ LLM อย่างน้อยหนึ่งเจ้า — Anthropic, OpenAI, Gemini,
  Agentic Press, OpenRouter หรือ DashScope (หรือจะติดตั้ง Ollama
  บนเครื่องเอง ถ้าต้องการใช้แบบ offline)

[บทที่ 2](ch02-installation.md) จะพาติดตั้งและเปิดใช้ครั้งแรก
[บทที่ 6](ch06-providers-models-api-keys.md) อธิบายว่าจะวาง
key ที่ไหนและอย่างไร

## คู่มือเล่มนี้จัดเรียงอย่างไร

**ส่วนที่ 1** (บทที่ 2–14) คือ reference อธิบายวิธีติดตั้ง ตามด้วยทุก
ฟีเจอร์ที่ผู้ใช้สัมผัสได้ ทีละเรื่อง พร้อมคำสั่งและการตั้งค่าที่จำเป็น

**ส่วนที่ 2** (บทที่ 15–21) คือ walkthrough ของโปรเจกต์จริงตั้งแต่เริ่มต้น
— landing page แบบ static, เว็บจอง, agent รวบรวมข่าว — จบด้วยการ
deploy ขึ้น Agentic Press Hosting แต่ละบทอ่านแยกกันได้

ถ้าเพิ่งเริ่ม อ่านบทที่ 2 ต่อได้เลย ถ้าย้ายมาจาก Claude Code แนะนำให้
ข้ามไปบทที่ 6, 7, 11 และ 13
