# บทที่ 15 — Subagents

Tool `Task` ช่วยให้ agent หลัก **มอบหมายงาน** ให้กับ sub-agent ซึ่งก็คือ
copy ของ agent ที่แยกออกมาต่างหาก โดยมี tool scope และเป้าหมาย
เป็นของตัวเอง เหมาะกับงานที่ต้องแตกสาขา (เช่น explore หลายแนวทาง
แบบขนาน) การปกป้อง context หลัก (รันการสำรวจที่มีข้อมูลรก ๆ ใน child)
หรืองานเฉพาะทาง (เช่น ส่งต่อให้ agent แบบ "reviewer" ที่ใช้ tools
แบบอ่านอย่างเดียว)

Subagents เป็นส่วนหนึ่งของ process เดียวกัน โดยรันอยู่ใน memory ไม่ได้แยก
เป็น OS process ต่างหาก หากต้องการ parallelism จริง ๆ ข้าม process
ให้ดู Agent Teams ในบทที่ 17

## หน้าตาเป็นอย่างไร

```
❯ are the REST endpoints in this repo consistent with our naming
  convention in AGENTS.md?

[tool: Task: (agent=reviewer, prompt=Check every route under src/api …)] …
  [child:reviewer] Using Glob to find route files…
  [child:reviewer] Found 14 routes; 3 don't match the convention
[tool: Task] ✓

Looking at the sub-agent's findings:
- `src/api/v1/getUsers.ts` should be `get_users.ts` per convention.
- `src/api/v1/FetchOrders.ts` should be `fetch_orders.ts`.
- `src/api/v2/createPost.ts` should be `create_post.ts`.
```

Parent จะเห็นเพียง response ที่เป็น text สุดท้ายของ sub-agent เท่านั้น
เสียงรบกวนจากการใช้ tool ระหว่างทางจึงไม่ไหลเข้ามาใน context หลัก

## การนิยาม agent

พฤติกรรมเฉพาะของ sub-agent ตั้งค่าได้ที่
`.thclaws/agents/*.md` (ระดับโปรเจกต์) หรือ `~/.config/thclaws/agents/*.md`
(ระดับผู้ใช้)

```markdown
---
name: reviewer
description: Read-only code review with focus on conventions
model: claude-haiku-4-5
tools: Read, Glob, Grep, Ls
permissionMode: auto
maxTurns: 20
color: cyan
---

You are a code reviewer. Look at the code the parent points you at.
Flag:
- Naming inconsistencies with the project's `AGENTS.md` conventions.
- Missing tests alongside new code.
- Security-sensitive patterns (raw SQL, unsanitised input).

Return a concise bullet list. Don't propose fixes unless asked.
```

ฟิลด์ใน frontmatter:

| Field | วัตถุประสงค์ |
|---|---|
| `name` | id ที่ไม่ซ้ำ (ค่าเริ่มต้นใช้ชื่อไฟล์) |
| `description` | ข้อความที่ parent จะเห็น บอกว่าควรใช้ agent นี้เมื่อไร |
| `model` | override โมเดลสำหรับ agent นี้ |
| `tools` | tool allowlist คั่นด้วย comma |
| `disallowedTools` | tool denylist |
| `permissionMode` | `auto` หรือ `ask` (เหมาะกับ agent แบบ "อ่านอย่างเดียว") |
| `maxTurns` | จำนวน iteration สูงสุด (ค่าเริ่มต้น 200) |
| `color` | สีในเทอร์มินัลสำหรับ output ของ child |
| `isolation` | `worktree` ให้ agent นี้มี git worktree ของตัวเอง (ใช้ได้เฉพาะใน teams) |

## การเรียกใช้

Agent หลักเรียกผ่าน `Task`:

```
Task(agent: "reviewer", prompt: "Check src/api for naming violations")
```

โดยทั่วไปคุณไม่ต้องเรียกตรง ๆ เพียงถามคำถามกับ parent เป็นภาษาอังกฤษ
แล้วตัวโมเดลจะตัดสินใจเอง เพราะจะเห็นรายการ agent ที่ใช้ได้
ใน system prompt (ซึ่ง render มาจากการนิยาม agent)

## การเรียกซ้อน (Recursion)

Sub-agent สามารถ spawn sub-agent เพิ่มได้ลึกถึง `max_depth = 3` ตาม
ค่าเริ่มต้น โดยแต่ละระดับจะมีขอบเขตแคบลงไปเรื่อย ๆ

```
parent (depth 0)
 ├─ reviewer (depth 1) — "look at auth routes"
 │   └─ specialist (depth 2) — "audit JWT signing"
 └─ tester (depth 1) — "write integration tests"
```

เมื่อถึง depth 3 tool Task จะถูกปิดเพื่อป้องกันการเรียกซ้อนแบบไม่รู้จบ

## ลำดับการโหลด

`~/.config/thclaws/agents.json` → `~/.claude/agents/*.md` →
`~/.config/thclaws/agents/*.md` → `.thclaws/agents/*.md` โดยตัวหลังจะชนะ
เมื่อชื่อซ้ำกัน

### Agent ที่มาจาก plugin

Plugins (บทที่ 16) สามารถส่ง agent def มาได้ผ่านรายการ `agents` ใน
manifest โดย directory เหล่านั้นจะถูก walk **หลังจาก** ที่อยู่มาตรฐาน
และถูก merge แบบ **เพิ่มเข้าไป** เท่านั้น agent จาก plugin ไม่สามารถ override
agent ของผู้ใช้หรือโปรเจกต์ที่ใช้ชื่อซ้ำกันได้ ซึ่งหมายความว่า

- สามารถติดตั้ง plugin ที่ส่ง `reviewer` + `tester` +
  `architect` มาได้ และทั้งสามจะพร้อมใช้งานผ่าน `Task(agent: "…")`
  รวมถึงการ spawn ภายใน team
- หากต่อมาคุณเพิ่ม `.thclaws/agents/reviewer.md` ของตัวเอง ของคุณจะชนะ
  ส่วนของ plugin จะถูกละเว้นไปจนกว่าคุณจะลบของตัวเองออก
- `/plugin show <name>` จะแสดงรายการ `agent dirs` ที่ plugin นั้นเพิ่มเข้ามา

## Subagents vs Teams

| | Subagents | Teams |
|---|---|---|
| **โมเดล process** | อยู่ใน process เดียว ทำทีละ agent | หลาย process ของ `thclaws --team-agent` ประสานด้วย tmux |
| **Parallelism** | Serial (ความลึกของ recursion ไม่ใช่ concurrency) | Concurrent อย่างแท้จริง |
| **การแยกส่วน** | ใช้ sandbox ร่วมกัน | เลือกใช้ git worktree แยกต่อคนได้ |
| **การสื่อสาร** | ไม่มี — child คืนค่าเป็น string | Filesystem mailbox + task queue |
| **Overhead** | น้อยมาก | สูง — ต้องเปิด process เพิ่มอย่างน้อย 1 ตัว |
| **เหมาะกับ** | โฟกัสปัญหาย่อย ลดขนาด context | สายงานแบบขนานที่ต้องมีการประสาน |

กฎง่าย ๆ คือ เริ่มจาก subagents ก่อน แล้วค่อยใช้ teams เมื่อมีงานที่
แตกสาขาจริง ๆ (เช่น "สร้าง backend ในขณะที่ฉันสร้าง frontend")
