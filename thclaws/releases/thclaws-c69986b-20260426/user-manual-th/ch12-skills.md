# บทที่ 12 — Skills

Skill คือ **เวิร์กโฟลว์ที่นำกลับมาใช้ใหม่ได้** ซึ่งบรรจุเป็นไดเรกทอรีที่มี:

- `SKILL.md` — YAML frontmatter (name, description, whenToUse) พร้อม
  คำสั่ง Markdown ให้โมเดลทำตาม
- `scripts/` (ไม่บังคับ) — shell / Python / Node script ที่ SKILL.md
  อ้างถึง โดยโมเดลจะเรียกผ่าน `Bash` เท่านั้น ไม่เคยเขียนใหม่เอง

skill คือวิธีย่อ "ช่วย deploy ตามพิธีกรรม 6 ขั้นของเราหน่อย" ให้
เหลือเพียงการเรียก tool ครั้งเดียว โมเดลจะอ่าน SKILL.md ทำตามคำสั่ง
แล้วใช้ script ที่คุณเตรียมไว้

## การค้นพบ (Discovery)

ตอนเริ่มต้น thClaws จะไล่หาในไดเรกทอรีเหล่านี้ตามลำดับ:

1. `.thclaws/skills/` — scope ของโปรเจกต์
2. `~/.config/thclaws/skills/` — scope ระดับ user
3. `~/.claude/skills/` — เพื่อรองรับ Claude Code
4. ไดเรกทอรีที่ plugin เพิ่มเข้ามา

`/skills` แสดงรายการที่โหลดไว้ ส่วน `/skill show <name>` พิมพ์เนื้อหา
SKILL.md ฉบับเต็มพร้อม path ที่ resolve เรียบร้อยแล้ว

## การติดตั้ง skill

### จาก git repo

```
❯ /skill install https://github.com/anthropics/skills.git
  cloned https://github.com/anthropics/skills.git → .thclaws/skills/skills
  bundle detected; installed 20 skill(s): canvas-design, docx, pdf, ...
```

thClaws ตรวจจับ bundle ได้อัตโนมัติ (repo ที่มี skill หลายตัวใน
subdirectory) แล้วเลื่อน sub-skill แต่ละตัวขึ้นมาเป็น sibling ให้

### จาก URL `.zip`

```
❯ /skill install https://agentic-press.com/api/skills/deploy-v1.zip
  downloaded https://agentic-press.com/...zip (4210 bytes) → extracted
  installed skill 'deploy-v1' (single)
```

- จำกัดขนาดที่ 64 MB
- ป้องกัน zip-slip (path ที่เป็นอันตรายใน archive จะถูกปฏิเสธ)
- คง exec bit ของ Unix ไว้ เพื่อให้ script ที่มาในชุดยังรันได้
- หากมี wrapper directory ระดับบนสุดเพียงอันเดียว (`pack-v1/...`)
  จะถูก unwrap ให้อัตโนมัติ

### Scope

`--user` จะติดตั้งลง `~/.config/thclaws/skills/` แทนที่จะลง
`.thclaws/skills/` ของโปรเจกต์ โดยดีฟอลต์จะใช้ scope โปรเจกต์

### เขียนทับชื่อที่ระบบตั้งให้เอง

```
❯ /skill install https://example.com/deploy.zip ourdeploy
```

## การเรียกใช้ skill

มีสามวิธีที่ให้ผลเทียบเท่ากัน:

1. **ให้โมเดลตัดสินใจเอง** — trigger `whenToUse` ของ skill จะปรากฏใน
   system prompt โมเดลจะเรียก `Skill(name: "…")` เองเมื่อเจอเคสที่ตรง

   ```
   ❯ make me a PDF from this data
   Using the `pdf` skill to generate a PDF...
   [tool: Skill: pdf] ✓
   [tool: Bash: .../scripts/pdf_from_data.py] ✓
   ```

2. **ใช้ทางลัด slash ตรง ๆ** — `/pdf [args]` จะถูกเขียนใหม่เป็น
   การเรียก `Skill(name: "pdf")` ให้เอง

   ```
   ❯ /pdf from the report markdown, 10pt font
   (/pdf → Skill(name: "pdf"))
   ```

3. **ระบุชัดเจนใน prompt** — เช่นสั่งว่า "ใช้ pdf skill เพื่อ…" แล้วโมเดลจะทำตาม

## กายวิภาคของ SKILL.md

```markdown
---
name: deploy-to-staging
description: Deploy the current branch to staging and run smoke tests
whenToUse: When the user asks to deploy or ship to staging
---

1. Ensure the working tree is clean (`git status`). Abort if dirty.
2. Run `{skill_dir}/scripts/build.sh` to build the production bundle.
3. Upload `dist/` via `{skill_dir}/scripts/push-to-staging.sh`.
4. Run `{skill_dir}/scripts/smoke-test.sh` — it should exit 0.
5. Report the staging URL to the user.

If any step fails, abort and report the failing step.
```

ฟิลด์ใน frontmatter:

| Field | จำเป็น | วัตถุประสงค์ |
|---|---|---|
| `name` | ใช่ | id ของ skill ที่ไม่ซ้ำกัน (ดีฟอลต์จะตรงกับชื่อไฟล์) |
| `description` | แนะนำ | คำอธิบายสั้นบรรทัดเดียวที่จะแสดงใน `/skills` |
| `whenToUse` | แนะนำ | คำใบ้ trigger ที่โมเดลใช้ตัดสินใจว่าจะเรียกเมื่อไหร่ |

`{skill_dir}` ในเนื้อหาจะถูกแทนด้วย absolute path ของไดเรกทอรี skill
ตอนโหลด ดังนั้น path ของ script จึง resolve ได้เสมอ ไม่ว่าผู้ใช้จะ
เปิด thClaws จากที่ใดก็ตาม

## เขียน skill ของคุณเอง

skill ที่เล็กที่สุดเท่าที่จะเป็นไปได้มีหน้าตาแบบนี้:

```
.thclaws/skills/hello/
  SKILL.md
```

```markdown
---
name: hello
description: Say hi in all caps
whenToUse: User asks to say hi loudly
---

Reply with exactly "HELLO!" and nothing else.
```

แค่นี้ก็ใช้งานได้แล้ว skill ที่เป็น prompt อย่างเดียวไม่ต้องมี script

สำหรับงานที่ต้องขับเคลื่อนด้วย script:

```
.thclaws/skills/greet/
  SKILL.md
  scripts/
    greet.sh
```

```markdown
---
name: greet
description: Run the greeting script with the user's name
whenToUse: User asks to greet someone
---

Run `bash {skill_dir}/scripts/greet.sh <name>` where <name> is the
person to greet.
```

```bash
# scripts/greet.sh
#!/bin/sh
echo "Hello, $1! Glad to see you."
```

ทำให้ script execute ได้ด้วย `chmod +x` แล้ว `Bash` tool จะรันให้โดยตรง

## การ refresh ขณะรันไทม์

หลังจาก `/skill install` thClaws จะค้นพบ skill ใหม่ทันที อัปเดตทั้ง
live store ของ SkillTool และตัว resolver ของทางลัด `/<skill-name>`
พร้อมสร้าง system prompt ใหม่ให้ skill ใหม่โผล่ขึ้นในส่วน
`# Available skills` — ไม่ต้อง restart ใช้ได้ทั้ง CLI REPL และ GUI
ทั้งสองแท็บ

## เขียน skill สำหรับโมเดลที่ต่างกัน

โมเดลในเครื่องที่เล็กกว่า (เช่น Gemma ผ่าน Ollama หรือ Qwen ขนาด
7-12B พารามิเตอร์) จะทำตามคำสั่ง skill ที่ชัดเจนและออกคำสั่งตรง ๆ ได้
ดีกว่าคำสั่งแบบหลวม ๆ หากต้องการให้ skill ใช้งานได้กว้าง ให้

- เขียนว่า "รัน X" แทน "พิจารณารัน X"
- ใส่เลขลำดับขั้นตอน
- รวมการจัดการความล้มเหลวไว้ที่ท้ายสุด ไม่กระจายไปในแต่ละขั้น
- เลี่ยง bullet ซ้อนชั้นใน Markdown เพราะ tokenizer บางตัวจัดการได้ไม่ดี

skill ที่ใช้งานได้บน Claude Sonnet ไม่การันตีว่าจะใช้งานได้บน
`ollama/gemma3:12b` ดังนั้นควรทดสอบกับโมเดลเป้าหมายของคุณเสมอ
