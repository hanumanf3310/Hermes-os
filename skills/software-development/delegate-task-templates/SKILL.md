---
name: delegate-task-templates
description: Ready-to-paste delegate_task templates for fast, narrow sub-agent work. Includes investigation, implementation, test verification, and review prompts.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [delegation, subagent, template, workflow, qa]
    related_skills: [subagent-driven-development, systematic-debugging, test-driven-development]
---

# Delegate Task Templates

Use these templates when you want a sub-agent to work fast with a narrow scope.

## Rules
- One delegate = one goal.
- Keep the allowed file list tiny.
- State what is forbidden to touch.
- Define acceptance criteria that can be checked.
- Ask for proof: targeted test, diff summary, or exact output.
- Do not combine implementation, review, and verification unless the task is intentionally tiny.

## Ultra-short one-liners

Use these when you need to paste a delegate prompt fast.

- **Investigation:** `Investigate why [bug/failure] happens in [file/module]. Allowed: [list]. Forbidden: [list]. Deliver root cause + evidence only.`
- **Implementation:** `Fix [single behavior] in [file/module]. Allowed: [list]. Forbidden: [list]. Deliver change summary + exact tests.`
- **Regression test:** `Add a regression test for [bug] in [test file]. Do not change production code. Deliver test only + pass/fail.`
- **Spec review:** `Review whether [files] match the original spec. No refactors. Deliver PASS/FAIL + exact gaps.`
- **Quality review:** `Review code quality of [files] only. Do not implement changes. Deliver issues + verdict.`

## Copy/Paste Templates

### 1) Investigation-only

```text
Goal: Investigate why [bug / failure] happens.

Context:
- Repo: [path]
- Failing command/test: [exact command]
- Symptom: [short description]
- Allowed files: [list]
- Forbidden files: [list]

Deliverable:
- Root cause only
- No code changes yet
- Include evidence and the exact line/file responsible
- Suggest the smallest fix path
```

### 2) Implementation-only

```text
Goal: Implement [single behavior] in [one file or one narrow module].

Context:
- Target file(s): [list]
- Must not touch: [list]
- Behavior to add/change: [specific]
- Acceptance criteria:
  1. [test or behavior]
  2. [test or behavior]
  3. [no regression]

Process:
- Make the smallest safe change
- Add or update only the targeted regression test(s)
- Run only the targeted test(s)
- Report the exact commands and results

Deliverable:
- Summary of the change
- Test command(s)
- Pass/fail result
```

### 3) Regression-test-only

```text
Goal: Add a regression test for [bug].

Context:
- Bug: [short description]
- Target file: [test file]
- Production file: [one file]
- Must not change production code
- Expected failing behavior before fix: [describe]
- Expected passing behavior after fix: [describe]

Deliverable:
- One focused test
- Explain why it fails before the fix
- Do not broaden scope
```

### 4) Spec review-only

```text
Goal: Review whether the implementation matches the original spec.

Context:
- Original spec: [paste bullets]
- Implemented files: [list]
- Do not propose refactors unless they are spec-critical

Checklist:
- [ ] All requirements implemented
- [ ] No scope creep
- [ ] File paths and behavior match the spec
- [ ] Any missing item listed explicitly

Deliverable:
- PASS or FAIL
- Exact gaps, if any
```

### 5) Code-quality review-only

```text
Goal: Review code quality of the changed files only.

Context:
- Files: [list]
- Focus: bugs, style, edge cases, test coverage, maintainability
- Do not re-litigate the spec unless there is a clear quality issue

Deliverable format:
- Critical issues
- Important issues
- Minor issues
- Verdict: APPROVED or REQUEST_CHANGES
```

## Fast Prompt Formula

Use this order:
1. Goal
2. Context
3. Allowed files
4. Forbidden files
5. Acceptance criteria
6. Deliverable format

## Example: bug fix

```text
Goal: Fix the Plan A live fetch path so it never falls back to cache.

Context:
- File: gateway/codex_bridge.py
- Test file: tests/gateway/test_codex_status_regressions.py
- Must not touch: unrelated gateway files
- Acceptance criteria:
  1. Plan A calls live status only
  2. Stale cache is ignored in Plan A
  3. Targeted regression test passes

Deliverable:
- Short summary
- Exact test command
- Result
```

## Example: compare mode

```text
Goal: Implement compare_plans() for Codex status.

Context:
- File: gateway/codex_bridge.py
- Callers: cli.py and gateway/run.py
- Must not touch: unrelated UI code
- Acceptance criteria:
  1. compare_plans returns plan_a and plan_b entries
  2. each plan includes success, latency_ms, and data
  3. winner and speedup are present
  4. targeted tests pass

Deliverable:
- Implementation summary
- Test command
- Result
```

## Two usage modes

### Mode 1: Standard form
Use when:
- The task is important
- Scope is a little risky or ambiguous
- You want the sub-agent to stay tightly bounded
- You need explicit acceptance criteria

Best for:
- bug fixes
- feature work
- regression tests
- reviews

### Mode 2: Ultra-short form
Use when:
- The task is tiny
- Scope is already obvious
- You need speed over detail
- Only one file / one behavior is involved

Best for:
- trivial fixes
- one-off checks
- very small edits

## Good defaults
- If the task is risky, split it into investigation -> implementation -> verification.
- If a sub-agent stalls, shrink the scope instead of widening it.
- If the task touches multiple files, each file should be necessary for the same single behavior.
- Default to the standard form unless the task is clearly tiny.
- For hermes-os-mode work, use the standard form by default, especially for state, persistence, CLI behavior, or any command-mode change; reserve the ultra-short one-liner for trivial checks only.
