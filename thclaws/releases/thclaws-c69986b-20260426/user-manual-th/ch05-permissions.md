# บทที่ 5 — สิทธิการใช้งานเครื่องมือ

thClaws รัน tool แทนคุณ ทั้งแก้ไฟล์ รันคำสั่ง shell ดึง URL
และเรียก MCP server ส่วน **Permissions** คือตัวกำหนดว่าอะไร
ทำได้โดยไม่ต้องขออนุญาตคุณก่อน

## สองโหมด

| โหมด | พฤติกรรม |
|---|---|
| `ask` (ค่าเริ่มต้น) | tool ที่เปลี่ยนข้อมูลหรืออาจสร้างความเสียหายได้จะขออนุญาตก่อนรัน ส่วน tool อ่านอย่างเดียวจะรันอัตโนมัติ |
| `auto` | tool ทุกตัวรันอัตโนมัติ agent จึงรัน edit และ bash ต่อเนื่องได้โดยไม่ถูกขัดจังหวะ |

ตั้งโหมดตอนเริ่มต้น:

```bash
thclaws --cli --permission-mode ask      # explicit
thclaws --cli --accept-all               # alias for --permission-mode auto
```

หรือกลาง session:

```
❯ /permissions auto
permissions: auto

❯ /permissions ask
permissions: ask
```

![thClaws Permissions](../user-manual-img/ch-05/thClaws-permissions.png)

## หน้าขออนุญาตหน้าตาเป็นยังไง

ในโหมด `ask` เมื่อ agent เรียก tool ที่เปลี่ยนข้อมูล (เช่น `Bash`,
`Write`, `Edit`, `WebFetch`) thClaws จะหยุดรอคำตอบจากคุณก่อน — GUI
กับ CLI แสดงคนละแบบแต่ decision 3 ตัวเหมือนกัน

### Desktop GUI

![thClaws Permissions Ask](../user-manual-img/ch-05/thClaws-permissions-ask.png)

modal กลางหน้าจอจะบอกชื่อ tool และ input (JSON preview) ที่ agent
ส่งมา พร้อมปุ่มสามปุ่ม:

- **Allow** — อนุมัติการเรียกครั้งนี้
- **Allow for session** — สลับไปโหมด auto สำหรับ session ที่เหลือ
  การเรียก tool ครั้งต่อ ๆ ไปจะผ่านโดยไม่ถาม
- **Deny** — ปฏิเสธ model จะได้ผลลัพธ์กลับไปว่า tool ถูก deny
  ซึ่งมักทำให้มันปรับวิธีใหม่

ถ้ามีหลาย request เข้าคิว (เช่น agent ยิง tool พร้อม ๆ กัน) modal
จะแสดงทีละตัวและขึ้นบรรทัด "+N more pending" ที่ด้านล่างให้รู้ว่ายังเหลืออีกเท่าไร

### CLI REPL

ใน terminal แบบโต้ตอบจะเห็น prompt คล้าย ๆ กัน:

```
[tool: Bash: npm install express] ?
 [y] yes   [n] no   [yolo] approve everything for this session
```

`y` = Allow, `n` = Deny, `yolo` = Allow for session

คำสั่งที่อาจสร้างความเสียหายได้อย่าง `rm -rf`, `sudo`, `curl … | sh`,
`dd`, `mkfs` ฯลฯ จะมีบรรทัดเตือนสีเหลือง `⚠ destructive command
detected: …` โผล่มาใน terminal ก่อนที่ prompt ขออนุญาตจะขึ้น เพื่อให้
คุณดูให้แน่ใจอีกรอบก่อนอนุมัติ

## ค่าเริ่มต้น: อ่านอย่างเดียว vs เปลี่ยนข้อมูล

| อ่านอย่างเดียว (auto ในโหมด `ask`) | เปลี่ยนข้อมูล (ขออนุญาตในโหมด `ask`) |
|---|---|
| `Ls`, `Read`, `Glob`, `Grep` | `Write`, `Edit` |
| `AskUser`, `EnterPlanMode`, `ExitPlanMode` | `Bash` |
| `TaskCreate`, `TaskUpdate`, `TaskGet`, `TaskList` | `WebFetch`, `WebSearch` |
|   | `Task` (spawn subagent) |
|   | MCP tool ทั้งหมด |

เจตนาคือ: การดูโค้ดของคุณทำได้ฟรีเสมอ ส่วนการแก้โค้ด
รันคำสั่ง หรือออก network เป็นเรื่องที่คุณต้องเป็นคนตัดสินใจ

## allow / deny list แบบละเอียด

สำหรับ config ระดับโปรเจกต์หรือ user ฟิลด์ `permissions` ใน
`.thclaws/settings.json` (หรือ `~/.config/thclaws/settings.json`) รับค่า
ได้สองรูปแบบ:

### โหมดเป็น string แบบง่าย

```json
{ "permissions": "auto" }
```

### รูปแบบ allow/deny ตาม Claude Code

```json
{
  "permissions": {
    "allow": ["Read", "Glob", "Grep", "Write", "Edit", "Bash(*)"],
    "deny":  ["WebFetch"]
  }
}
```

- รายการใน `allow` จะรันโดยไม่ถาม (เหมือนเป็น `auto` เฉพาะรายการเหล่านี้)
- รายการใน `deny` จะไม่รันเด็ดขาด ถ้าพยายามเรียกจะส่ง error กลับไปยัง model
- `Bash(*)` อนุญาต bash ทุกคำสั่ง ส่วน `Bash(git *)` จำกัด allow
  ให้เฉพาะคำสั่ง git (matching แบบ glob บน string คำสั่ง)

รูปแบบแบนก็ใช้ได้:

```json
{
  "permissions": "auto",
  "allowedTools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
  "disallowedTools": ["WebFetch", "WebSearch"]
}
```

## CLI flag สำหรับการรันครั้งเดียว

```bash
thclaws --cli \
  --permission-mode auto \
  --allowed-tools "Read,Write,Edit,Bash" \
  --disallowed-tools "WebFetch"
```

flag เหล่านี้จะ override settings file เฉพาะใน process นั้น ๆ เท่านั้น

## sandbox ของ filesystem

แยกออกมาจากเรื่องการขออนุญาต: **tool ที่เกี่ยวกับไฟล์จะถูกจำกัด
ให้อยู่ใน working directory เสมอ** ไม่ว่าจะเป็น path ที่หลุดออกไป
ด้วย `..` path แบบ absolute ที่ชี้ออกนอก หรือการตาม symlink
ออกไป จะถูกปฏิเสธตั้งแต่ก่อน tool จะได้รันโดยไม่สนโหมด permission
นี่คือการ์ดที่ทำให้ `yolo` น่ากลัวน้อยลง

### ตั้งค่าเมื่อเปิด session

ตอน thClaws เริ่มทำงาน จะอ่าน `current working directory` ตอนนั้น
แล้วเก็บเป็น **sandbox root** ค่านี้คงที่ตลอด session — `cd` ใน
`Bash` tool ไม่เปลี่ยน root เพราะ subprocess `cd` จะมีผลเฉพาะ shell
ลูก ไม่กระทบ process แม่ของ thClaws

ใน GUI ถ้าใช้ "change directory" modal เปลี่ยน folder ระหว่างทาง
sandbox จะถูก re-init ให้ตรงกับ folder ใหม่ แต่ tool call ที่ค้างอยู่
ก่อนหน้าใช้ root ก่อนเปลี่ยน

### path resolution

| ตัว path ที่ tool ส่งมา | resolve ยังไง |
|---|---|
| relative (`src/foo.rs`) | join กับ cwd ของ thClaws (= sandbox root ในกรณีเดี่ยว) |
| absolute (`/Users/me/proj/foo.rs`) | ใช้ตามที่ส่งมา ไม่แตะ |
| มี `..` หรือ `.` ปน | คลี่ออกตามไวยากรณ์ก่อน เช่น `cwd/../etc/passwd` กลายเป็น `/etc/passwd` แล้วเช็ค containment |
| symlink ที่ชี้ออกนอก root | `canonicalize` เปิดเผย target จริง ถ้าหลุด root จะ deny |

หลังจาก resolve แล้ว path สุดท้ายต้องอยู่ "ใต้" sandbox root ถึงจะ
ผ่าน — เช็คเทียบ component ไม่ใช่ตัวอักษร

### Write กับโฟลเดอร์ที่ยังไม่มีอยู่

`Write` สามารถเขียนไฟล์ที่ตัวมันเองและ folder กลางทางยังไม่มีได้
เลย เช่น `Write("src/api/handlers/auth.ts")` ในโปรเจกต์ที่เพิ่ง
สร้าง — sandbox จะไต่ขึ้นไปหา ancestor ที่มีอยู่จริงตัวแรก
(`src/api/`, ถ้าไม่มีก็ `src/`, ถ้าไม่มีก็ root) แล้วเช็คว่า ancestor
นั้นอยู่ใน sandbox หรือเปล่า ถ้าอยู่ ก็ปล่อยให้ Write ไป
`mkdir -p` แล้วเขียนไฟล์ตามปกติ

### deny list ในตัว

นอกจากเช็คขอบเขตแล้ว มี policy อีกชั้นสำหรับการ **เขียน**
(`Write`, `Edit`):

- ห้ามเขียนใต้ `<root>/.thclaws/` — โฟลเดอร์นี้เก็บ team config,
  inbox, task queue, และไฟล์ภายในของ harness ถ้า agent อยากแก้
  team state ต้องผ่าน team tool (`SendMessage`, `TeamTaskCreate`,
  ฯลฯ) เท่านั้น

ส่วนการ **อ่าน** ใน `.thclaws/` ทำได้ปกติ — ไม่กระทบกับ
`/team/inboxes/*.json` ที่บางทีคุณอยาก inspect ด้วยตนเอง

### override

ถ้าอยากให้ agent แตะอะไรที่อยู่นอก directory ปัจจุบัน ให้เปิด thClaws
จาก directory แม่แทน (ซึ่งจะขยาย sandbox ให้กว้างขึ้น) หรือ
copy / symlink ไฟล์เข้ามาก่อน ไม่มี flag ให้ "ปิด sandbox" เพราะ
มันเป็นเส้นตายที่ทำให้ `yolo` ปลอดภัยพอจะเปิดได้

ในบริบทของ Agent Teams (บทที่ 17) sandbox จะกว้างขึ้นโดยอัตโนมัติ
เพื่อรองรับ git worktree — ดูรายละเอียดที่นั่น

## ด่านความปลอดภัยของ MCP

MCP server และ tool ของมันผ่านการขออนุญาตสองจุดที่ทำงานคนละเรื่อง
กัน อย่าสับสนกัน

### 1. ตอน agent เรียก tool ของ MCP

MCP tool ทุกตัวนับเป็น mutating (เหมือน `Bash`, `Write` ฯลฯ) — ใน
โหมด `ask` thClaws จะหยุดรอคำตอบผ่าน approval modal ตัวเดียวกับที่
ใช้กับ tool ในตัว (หัวข้อ *หน้าขออนุญาตหน้าตาเป็นยังไง* ด้านบน) ชื่อ
tool ใน modal จะขึ้นเป็น `<server>__<tool>` เช่น `weather__get_forecast`
เพื่อให้รู้ว่ามาจาก MCP server ตัวไหน

![thClaws MCP tool call — approval modal ถาม weather__get_forecast ที่ MCP ส่งขึ้นมา](../user-manual-img/ch-05/thClaws-mcp-ask.png)

Allow / Allow for session / Deny ทำงานเหมือน tool อื่น ๆ ทุกประการ

### 2. ตอน spawn subprocess ของ MCP stdio ครั้งแรก

MCP stdio server คือ subprocess ที่ spawn ขึ้นมาจาก config JSON
ซึ่งอาจ clone มาจาก repo ที่ไม่น่าเชื่อถือก็ได้ (`.thclaws/mcp.json`
หรือไฟล์ทำนองเดียวกัน — ดู[บทที่ 14](ch14-mcp.md)) เนื่องจากฟิลด์
`command` คือ path ไปยัง binary อะไรก็ได้ thClaws จึงคุมการ spawn
**ครั้งแรก** ของแต่ละ binary ด้วยด่านแยกต่างหาก ที่ทำงานก่อน agent
จะได้สิทธิ์เรียก tool ของ server นั้นเสียอีก

#### Desktop GUI

หลังจากคุณเลือก working directory และปิด dialog เลือกที่เก็บ key
เสร็จแล้ว (รายละเอียดใน[บทที่ 3](ch03-working-directory-and-modes.md#first-launch-setup))
ถ้ามี MCP stdio server ที่ยังไม่เคยอนุมัติใน allowlist thClaws จะหยุดรอ
คำตอบผ่าน modal ก่อนจะ spawn — mount หลังจาก launch modal เสร็จ จึง
ไม่ไปทับหน้าเลือก folder

![thClaws MCP spawn ask — modal ถามว่าจะให้ spawn `npx` สำหรับ MCP server 'weather' ไหม](../user-manual-img/ch-05/thClaws-mcp-spawn-ask.png)

modal จะบอก command ที่จะรัน ชื่อ MCP server ที่ร้องขอ และเตือนว่า
binary จะรันด้วย user privileges ของคุณ มีสองปุ่ม:

- **Allow** — อนุมัติและบันทึกลง allowlist แบบถาวร (ไม่มี "Allow for
  session" เพราะ Allow เทียบเท่ากันอยู่แล้ว)
- **Deny** — ปฏิเสธ การ spawn ล้มเหลว server ตัวนั้นไม่ขึ้น

#### CLI REPL

`thclaws --cli` (หรือ SSH/terminal ที่ไม่ได้เปิด GUI) จะใช้ prompt
แบบ text ที่อ่านจาก stdin แทน — output เหล่านี้โผล่ใน terminal ที่
launch โปรแกรม:

```
[mcp] New MCP stdio server wants to spawn:
      name:    filesystem-mcp
      command: npx
      args:    @modelcontextprotocol/server-filesystem /tmp

This will run the binary with your user privileges. Only
approve if you trust the MCP config that requested it.
Approve and remember? [y/N]
```

ตอบ `y` = อนุมัติและเก็บ, อย่างอื่น = ปฏิเสธ

#### allowlist file

ไม่ว่าจะ GUI หรือ CLI การ Allow จะเก็บ string `command` ลงใน
`~/.config/thclaws/mcp_allowlist.json` (ไฟล์และ folder ถูกสร้างให้
อัตโนมัติถ้ายังไม่มี) การ spawn ครั้งต่อ ๆ ไปของคำสั่งเดียวกันจะผ่าน
ได้โดยไม่ถาม allowlist จะใช้เฉพาะฟิลด์ `command` เป็น key เท่านั้น
การเปลี่ยน args ไม่ได้ trigger ให้ต้องขออนุมัติใหม่ ดังนั้นต้อง
ระวังเวลาอนุมัติ runner ทั่ว ๆ ไปอย่าง `npx` หรือ `python`

**บริบทแบบ headless แท้ ๆ** (CI, โหมด `-p`/`--print`, หรือ SSH ที่ไม่มี
controlling TTY) จะ fail แบบปิดไปเลย เว้นแต่คุณจะตั้ง
`THCLAWS_MCP_ALLOW_ALL=1` ไว้อย่างชัดเจนในสภาพแวดล้อมที่ไว้ใจได้
อย่าตั้งตัวแปรนี้บนเครื่องที่ใช้ร่วมกันหรือผ่านไฟล์ `.env` ของโปรเจกต์
— ตัวโหลด dotenv บล็อกไว้ด้วยเหตุผลนี้โดยเฉพาะ

## override ระดับ agent

Agent Team และ tool sub-agent `Task` สามารถตั้ง `permissionMode`
ของตัวเองในไฟล์นิยาม agent ได้ ซึ่งมีประโยชน์เวลาอยากให้ agent
แบบ "reviewer" รันได้เฉพาะ read-only แม้ว่า lead จะอยู่ในโหมด
`auto` ก็ตาม ดูรายละเอียดในบทที่ 15 และบทที่ 17
