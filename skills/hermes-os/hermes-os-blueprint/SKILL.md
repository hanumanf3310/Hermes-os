---
name: hermes-os-blueprint
description: Hermes OS Operator Blueprint — model-agnostic interactive lesson flow for teaching and using Hermes OS with policy-first, evidence-first, STOP/ACTION/CHECKPOINT gates, dashboard-aware workflow mapping, delegation discipline, and checkpoint/rollback control.
version: 0.1.0
author: hanuman3310
category: hermes-os
tags:
  - hermes-os
  - blueprint
  - operator-training
  - model-agnostic
  - evidence-first
  - dashboard
  - checkpoint
  - delegation
requires_tools:
  - file
  - terminal
  - skills
---

# Hermes OS Operator Blueprint

## Trigger

Use this skill when Boss wants to start, run, inspect, or maintain the Hermes OS Operator Blueprint.

Canonical Blueprint path:

```text
/home/hanuman3310/hermes-os-blueprint
```

Canonical instructor manual:

```text
/home/hanuman3310/hermes-os-blueprint/AGENT.md
```

Compatibility shims:

```text
/home/hanuman3310/hermes-os-blueprint/AGENTS.md
/home/hanuman3310/hermes-os-blueprint/CLAUDE.md
```

## Supported command style

This skill is automatically available as a skill slash command in Hermes surfaces that scan `~/.hermes/skills`:

```text
/hermes-os-blueprint
/hermes_os_blueprint
```

Use the text after the command as the learner request. Examples:

```text
/hermes-os-blueprint Start Lesson 1
/hermes-os-blueprint Start Lesson 8
/hermes-os-blueprint status
/hermes-os-blueprint run smoke test
```

If the command is unavailable in a runtime, open the Blueprint folder and tell the active model:

```text
Read AGENT.md and Start Lesson 1
```

## Operating contract

- Hermes OS is the nervous/control layer.
- Hermes Agent core remains the body/main cognition.
- Normal messages remain direct by default.
- Fleet, thClaws, OMX, and other execution limbs run only through explicit commands or policy-approved paths.
- The Blueprint teaches by doing, but every risky action must stop at CHECKPOINT.
- Do not edit dashboard, register additional skills, write durable memory/facts, restart gateway, deploy, or invoke external limbs unless Boss approves the exact scope and rollback notes.
- Evidence-first: never claim lesson or integration success without direct file/tool/runtime evidence.
- Terminal commands in Hermes Agent must be RTK-first.
- Use Asia/Bangkok when timestamps or day boundaries matter.

## How to run a lesson

When Boss asks to start a lesson:

1. Read `AGENT.md`.
2. Resolve the lesson number from the request.
3. Read the matching lesson file under `lesson-modules/N-*/LESSON.md`.
4. Guide the learner interactively.
5. Stop at every `STOP:` block.
6. Treat every `CHECKPOINT:` block as a go/no-go gate.
7. Follow `ACTION:` branches based on Boss's response.
8. Write or request the lesson evidence artifact only when in scope.
9. Report with `Verified`, `Inferred`, `Blocked`, and `Needs confirmation` labels.

Lesson map:

```text
1. Foundations — policy, RTK, evidence, direct execution
2. Context Binding — global mode, chat binding, gateway behavior
3. Memory / Fact Store — durable memory, facts, session recall
4. Skills Registry — reuse, patch, create, validate
5. Delegation / Fleet — narrow prompts, acceptance criteria, external limbs
6. Dashboard Evidence — working path map, safe update validation
7. Checkpoint / Rollback — go/no-go and recovery discipline
8. Real Workflow — end-to-end Hermes workflow build
```

Blueprint versions:

- **v0.1** — Passive (instructor-led, Boss observes).
- **v0.2** — Interactive / Boss-as-instructor (Boss teaches, junior operator persona responds; lessons under `lesson-modules-v02/`). Assistant plays a junior operator who asks Boss the STOP questions instead of presenting options. Fast-Forward Mode still applies — Boss says `ต่อเลย` → assistant selects the safe option and proceeds immediately.

## Fast-Forward Mode

Use Fast-Forward Mode when Boss shows these patterns:

- Boss types `ต่อเลย` (repeat "continue" without choosing from options).
- Boss says `ไม่ต้องถามฉัน` / `เลือกแบบที่ดี/ปลอดภัยให้ฉัน`.
- Boss says `skip exercises` or `ข้าม exercises`.
- Boss has already demonstrated Lesson knowledge (e.g., completed earlier Lessons).
- Boss prefers concise execution over interactive STOP/question loops.

In Fast-Forward Mode:

1. Skip STOP-marker questions that ask Boss to choose/explain/classify.
2. Instead, **instructor selects** the safest Boss-aligned option automatically.
3. Still **execute** the correct branch content (not skip the lesson material).
4. Still **respect CHECKPOINT blocks** for state-changing operations (dashboard edit, skill register, service restart).
5. Autogenerate the evidence artifact file (e.g., `lesson-N-completion-evidence.md`) without asking Boss.
6. Report with Verified/Inferred/Blocked labels.
7. End with "ผลลัพธ์ [evidence]" not "Lesson X Complete" without proof.

Exception — always pause:

- If the next step edits `dashboard.html`.
- If the next step registers/creates a new skill.
- If the next step restarts gateway or any service.
- If the next step invokes Fleet/thClaws/OMX.
- If evidence is incomplete for a success claim.

## Status check

A Blueprint status check should verify:

```text
/home/hanuman3310/hermes-os-blueprint exists
README.md exists
AGENT.md exists
AGENTS.md exists
CLAUDE.md exists
RUNTIME-COMPATIBILITY.md exists
8 lesson modules exist
Each lesson has STOP:, ACTION:, and CHECKPOINT:
Each lesson references its evidence artifact
Dashboard contains Hermes OS Blueprint node if integration is expected
Skill command scanner sees /hermes-os-blueprint if command integration is expected
```

## Smoke test

A read-only smoke test may:

- verify file structure
- verify lesson marker coverage
- build a skill invocation message for `/hermes-os-blueprint Start Lesson 1`
- verify dashboard node/link validation

A smoke test must not:

- restart gateway
- edit dashboard after validation
- create additional skills
- write memory/facts
- deploy
- invoke Fleet/thClaws/OMX

## Dashboard integration

Dashboard node id:

```text
skill_hermes_os_blueprint
```

Project node id:

```text
proj_hermes_os_blueprint
```

Expected dashboard relationships:

```text
cat_hermes_os -> skill_hermes_os_blueprint
skill_hermes_os_blueprint -> proj_hermes_os_blueprint
hermes_os_core -> proj_hermes_os_blueprint
user_profile -> proj_hermes_os_blueprint
proj_memory_graph -> proj_hermes_os_blueprint
skill_writing_plans -> proj_hermes_os_blueprint
skill_hermes_os_blueprint -> skill_dashboard_validator
```

Dashboard presence is only a working-path map. It is not live proof that a lesson was run.

## Post-completion production integration (NEW)

After Boss passes all 8 lessons of v0.2 (or is already certified), the next step is applying blueprint discipline to the live Hermes OS system:

### Integration workflow

1. **Run Weekly Hermes Health Check**
   - Skill: `weekly-hermes-health-check`
   - Verify all 5 layers (Core State, Policy, Dashboard, Infrastructure, Security)
   - Evidence artifact: `~/hermes-os-blueprint/weekly-hermes-health-check-YYYYMMDD-evidence.md`

2. **Dashboard production update (if node/link design approved in Lesson 6)**
   - Follow `dashboard-html-safe-update` skill
   - Backup → validate → inject → re-validate → evidence
   - Note: validator regex `\{\s*"id":\s*"` must be used if injecting nodes with newline+space after `{`

3. **Checkpoint discipline for state-changing actions**
   - Stop → prerequisites (backup, validator, target verification) → Boss confirms go/no-go → execute
   - Never "go" on no-backup/no-validator assumptions

4. **Create skills from workflow (if Lesson 8 workflow is reusable)**
   - New skill at `~/.hermes/skills/<name>/SKILL.md`
   - Based on Boss-designed workflow + narrow scope + measurable acceptance criteria

5. **Fact store integration**
   - Add Fact+* records for: completion, validator bugs fixed, new skills created, dashboard changes
   - Categories: `hermes-os-blueprint`, `dashboard-validator`, `skill-registry`, `dashboard`, `weekly-health-check`

### Pitfalls post-certification
- Do not skip backup just because "เคยทำมาแล้ว" — every production run needs its own backup
- Do not trust validator blindly after a patch — verify by browser console + grep
- Do not mix v0.1 (passive) and v0.2 (interactive) evidence naming in the same artifact

---

## Done criteria for full-system availability

The Hermes OS Blueprint is fully available when:

- ✅ The local Blueprint content exists and verifies.
- ✅ The `hermes-os-blueprint` skill exists under `~/.hermes/skills/hermes-os/`.
- ✅ Skill slash-command scanning exposes `/hermes-os-blueprint`.
- ✅ Dashboard contains connected Blueprint nodes and links.
- ✅ Dashboard node `proj_hermes_os_blueprint` description updated to v0.1 VERIFIED.
- ✅ Dashboard validator returns `ok: true` (missingRefs = 0 verified).
- ✅ A read-only command smoke test can load the skill and build an invocation for `Start Lesson 1`.
- ✅ (v0.2+) Post-completion integration evidence exists if Boss has completed all lessons

**v0.1 Integration Status: COMPLETE as of 2026-05-02**
- 8 lessons + evidence artifacts verified (under root blueprint directory).
- Dashboard node + skill both present.
- Task 5 (dashboard integration) done.

**v0.2 Status**
- Interactive lesson modules exist under `lesson-modules-v02/`.
- Evidence artifacts follow pattern: `v02-evidence/boss-lesson-N-evidence.md`.
- Boss acts as instructor; assistant assumes junior operator persona.
- Fast-Forward Mode preserved (`ต่อเลย` pattern).
- Pending: full v0.2 lesson completion and master evidence consolidation.

## Lesson execution patterns (v0.2 interactive)

### Node draft (Lesson 6)

Boss writes node draft พร้อม Hermes OS context:

```markdown
Node ID: hermes_os_blueprint_v02
Label: Hermes OS Blueprint v0.2 — Interactive Training
Type: training_blueprint
Purpose: Active-learning ... RTK enforcement, UTC+7 normalization, policy gateway ...
Evidence: /path/to/v02-plan.md, lesson-modules-v02/, v02-evidence/boss-lesson-*.md
Status: Lessons 1–5 complete; RTK enabled; UTC+7 enforced; Hermes OS mode active
```

Junior operator validates:
1. Target ID exists in dashboard ✅
2. New ID doesn't collide ✅
3. Hermes OS context in description ✅
4. Links use verified source/target ✅

### Checkpoint / Rollback (Lesson 7)

Checkpoint decision flow:
```
STOP when:
- No backup → create backup first
- No validator → run validator first
- Target unverified → verify target exists
- Scope unclear → stop and scope

After prerequisites met → re-ask go/no-go
```

Junior operator ตรวจแล้วถามใหม่:
1. Backup created (`dashboard.html.bak.YYYYMMDD-HHMMSS`)
2. Validator returns `ok: true, missingRefs: 0`
3. Target node exists
4. ถาม Boss: "backup + validator พร้อมแล้ว ยืนยัน go ไหม?"

Handle emotional pressure:
- "แค่ node เดียว" = assumption → unsafe
- Backup + validate < time to fix if broken
- ไม่ใช่เสียเวลา = invest เพื่อ safety

### Evidence file naming

v0.2 pattern:
```
v02-evidence/boss-lesson-N-evidence.md
```

## Pitfalls

- Do not treat `CLAUDE.md` as canonical; it is only a compatibility shim.
- Do not claim live runtime proof from dashboard presence alone.
- Do not auto-route normal messages to Fleet, thClaws, or OMX.
- Do not promote temporary lesson artifacts into durable memory/facts without confirmation.
- Do not add more system integrations without a checkpoint.
- Do not claim Lesson N passed without evidence file (or chat-only mode with clear note).
- Do not skip re-asking go/no-go after prerequisites are prepared — checkpoint ต้อง double-gate.
- Do not let Boss skip backup because "น่าจะไม่พัง" — นั่นคือ assumption ไม่ใช่ evidence.
