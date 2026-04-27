---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior. 4-phase root cause investigation — NO fixes without understanding the problem first.
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
    related_skills: [test-driven-development, writing-plans, subagent-driven-development]
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Someone wants it fixed NOW (systematic is faster than thrashing)

## The Four Phases

You MUST complete each phase before proceeding to the next.

---

## Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

### 1. Read Error Messages Carefully

- Don't skip past errors or warnings
- They often contain the exact solution
- Read stack traces completely
- Note line numbers, file paths, error codes

**Action:** Use `read_file` on the relevant source files. Use `search_files` to find the error string in the codebase.

### 2. Reproduce Consistently

- Can you trigger it reliably?
- What are the exact steps?
- Does it happen every time?
- If not reproducible → gather more data, don't guess

**Action:** Use the `terminal` tool to run the failing test or trigger the bug:

```bash
# Run specific failing test
pytest tests/test_module.py::test_name -v

# Run with verbose output
pytest tests/test_module.py -v --tb=long
```

### 3. Check Recent Changes

- What changed that could cause this?
- Git diff, recent commits
- New dependencies, config changes

**Action:**

```bash
# Recent commits
git log --oneline -10

# Uncommitted changes
git diff

# Changes in specific file
git log -p --follow src/problematic_file.py | head -100
```

### 4. Gather Evidence in Multi-Component Systems

**WHEN system has multiple components (API → service → database, CI → build → deploy):**

**BEFORE proposing fixes, add diagnostic instrumentation:**

For EACH component boundary:
- Log what data enters the component
- Log what data exits the component
- Verify environment/config propagation
- Check state at each layer

Run once to gather evidence showing WHERE it breaks.
THEN analyze evidence to identify the failing component.
THEN investigate that specific component.

### 5. Trace Data Flow

**WHEN error is deep in the call stack:**

- Where does the bad value originate?
- What called this function with the bad value?
- Keep tracing upstream until you find the source
- Fix at the source, not at the symptom

**Action:** Use `search_files` to trace references:

```python
# Find where the function is called
search_files("function_name(", path="src/", file_glob="*.py")

# Find where the variable is set
search_files("variable_name\\s*=", path="src/", file_glob="*.py")
```

### Phase 1 Completion Checklist

- [ ] Error messages fully read and understood
- [ ] Issue reproduced consistently
- [ ] Recent changes identified and reviewed
- [ ] Evidence gathered (logs, state, data flow)
- [ ] Problem isolated to specific component/code
- [ ] Root cause hypothesis formed

**STOP:** Do not proceed to Phase 2 until you understand WHY it's happening.

---

## Phase 2: Pattern Analysis

**Find the pattern before fixing:**

### 1. Find Working Examples

- Locate similar working code in the same codebase
- What works that's similar to what's broken?

**Action:** Use `search_files` to find comparable patterns:

```python
search_files("similar_pattern", path="src/", file_glob="*.py")
```

### 2. Compare Against References

- If implementing a pattern, read the reference implementation COMPLETELY
- Don't skim — read every line
- Understand the pattern fully before applying

### 3. Identify Differences

- What's different between working and broken?
- List every difference, however small
- Don't assume "that can't matter"

### 4. Understand Dependencies

- What other components does this need?
- What settings, config, environment?
- What assumptions does it make?

---

## Phase 3: Hypothesis and Testing

**Scientific method:**

### 1. Form a Single Hypothesis

- State clearly: "I think X is the root cause because Y"
- Write it down
- Be specific, not vague

### 2. Test Minimally

- Make the SMALLEST possible change to test the hypothesis
- One variable at a time
- Don't fix multiple things at once

### 3. Verify Before Continuing

- Did it work? → Phase 4
- Didn't work? → Form NEW hypothesis
- DON'T add more fixes on top

### 4. When You Don't Know

- Say "I don't understand X"
- Don't pretend to know
- Ask the user for help
- Research more

---

## Phase 4: Implementation

**Fix the root cause, not the symptom:**

### 1. Create Failing Test Case

- Simplest possible reproduction
- Automated test if possible
- MUST have before fixing
- Use the `test-driven-development` skill

### 2. Implement Single Fix

- Address the root cause identified
- ONE change at a time
- No "while I'm here" improvements
- No bundled refactoring

### 3. Verify Fix

```bash
# Run the specific regression test
pytest tests/test_module.py::test_regression -v

# Run full suite — no regressions
pytest tests/ -q
```

### 4. If Fix Doesn't Work — The Rule of Three

- **STOP.**
- Count: How many fixes have you tried?
- If < 3: Return to Phase 1, re-analyze with new information
- **If ≥ 3: STOP and question the architecture (step 5 below)**
- DON'T attempt Fix #4 without architectural discussion

### 5. If 3+ Fixes Failed: Question Architecture

**Pattern indicating an architectural problem:**
- Each fix reveals new shared state/coupling in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**STOP and question fundamentals:**
- Is this pattern fundamentally sound?
- Are we "sticking with it through sheer inertia"?
- Should we refactor the architecture vs. continue fixing symptoms?

**Discuss with the user before attempting more fixes.**

This is NOT a failed hypothesis — this is a wrong architecture.

---

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals a new problem in a different place**

**ALL of these mean: STOP. Return to Phase 1.**

## Common Pytest Collection Pitfall

When a helper class or dataclass is named with a `Test*` prefix, pytest may try to collect it as a test case even if it is not a test. This often shows up as a warning like:

- `PytestCollectionWarning: cannot collect test class 'X' because it has a __init__ constructor`

**Fix options:**
- Rename the class to avoid the `Test` prefix, or
- Add `__test__ = False` inside the class to prevent collection

This is especially useful for utility dataclasses such as `TestResult` inside a test harness module.

## Recurring Hermes Test-Environment Pitfalls

### 1) Shared mock-module contamination

In large test suites, multiple files may stub the same dependency through `sys.modules` (for example `discord`). If some files use `setdefault(...)` and others overwrite `sys.modules["discord"]`, import order can change the actual object seen by already-imported code.

**Symptoms:**
- A test passes when run alone but fails in the full suite
- Attributes unexpectedly become `MagicMock`
- One test file's mock setup appears to affect unrelated tests

**Debugging approach:**
- Identify every test file that stubs the shared module
- Check whether the production module imported the dependency before or after the stub was installed
- Prefer one shared mock/fixture per package so all tests see the same shape
- Avoid mixing `setdefault` and reassignment across files unless the behavior is deliberate

### 2) Fake process objects that do not behave like real pipes

Background cleanup or stream-draining code sometimes assumes `stdout`/`stderr` are real file descriptors. Test doubles often use iterators or `MagicMock`, which may not implement `fileno()` correctly.

**Symptoms:**
- `AttributeError: 'list_iterator' object has no attribute 'fileno'`
- `TypeError: fileno() returned a non-integer`
- Thread warnings from cleanup paths rather than the main assertion

**Debugging approach:**
- Inspect the fake `Popen`/process object used by the test
- Verify whether the code path needs a real file descriptor or should gracefully skip draining in test mode
- Add a guard around `fileno()` / `select.select()` usage
- If needed, adjust the test double to mimic the real API more closely

### 3) Host allowlist env leakage into e2e tests

In gateway e2e suites, a local `.env` can leak platform allowlist variables such as `TELEGRAM_ALLOWED_USERS` into the test process. This can silently flip unauthorized-DM behavior from pairing to ignore and make authorization tests pass alone but fail in the full suite.

**Symptoms:**
- Unauthorized DM tests unexpectedly do not send pairing messages
- Behavior differs between isolated test runs and the full suite
- The code path is correct, but the process environment changes the default policy

**Debugging approach:**
- Inspect the effective environment seen by the failing test process
- Clear allowlist variables in isolated e2e fixtures when the test is meant to exercise open-gateway behavior
- Prefer fixture-level cleanup over ad hoc per-test mutations when many tests share the same runner setup
- Re-run the smallest relevant gateway slice before moving on to the full suite

### 4) Tool availability checks coupled to backend env can hide unrelated tools

Some tool registrations share a `check_fn` that indirectly depends on terminal backend requirements (for example file tools reusing terminal requirements). If full-suite env leakage sets a strict backend mode (e.g. `TERMINAL_ENV=modal` + `TERMINAL_MODAL_MODE=direct` without credentials), `get_tool_definitions()` may silently filter out many tools and leave only `process`.

**Symptoms:**
- Tool-resolution tests pass alone but fail in full suite
- Expected set like `{terminal, process, read_file, write_file, search_files, patch}` becomes `{'process'}`
- Logs mention backend credential errors during schema resolution

**Debugging approach:**
- Capture the effective `TERMINAL_*` env in the failing worker
- Reproduce with explicit env overrides to confirm coupling
- In tests, isolate tool-resolution expectations from global backend env (`TERMINAL_ENV=local`, clear modal-only vars) unless the test is specifically about modal requirements
- Avoid asserting broad tool catalog behavior under inherited global env

### 5) Pairing/rate-limit state leakage via persistent PairingStore path

Gateway pairing tests can pass in isolation but fail in full suite when `PairingStore` reads/writes a persistent `PAIRING_DIR` from the real Hermes home. Prior tests may leave rate-limit or pending state that suppresses pairing replies.

**Symptoms:**
- Unauthorized DM pairing test intermittently sees `adapter.send.await_count == 0`
- Log still shows unauthorized user, but no pairing message emitted
- Isolated test passes; full suite fails after other gateway tests

**Debugging approach:**
- Treat pairing store as persistent state, not pure in-memory fixture state
- Patch both config home resolution and `gateway.pairing.PAIRING_DIR` to a per-test temp directory
- Keep pairing tests hermetic: no reads from shared `~/.hermes/platforms/pairing`
- Re-run the single failing test, then a nearby gateway slice, then full suite

### 4) Tool-resolution flakes from leaked TERMINAL_* environment

Some suites mutate `TERMINAL_ENV` / `TERMINAL_MODAL_MODE` / `TERMINAL_CWD`. If later tests call `get_tool_definitions(enabled_toolsets=["terminal", "file"])`, leaked modal/direct settings can make `check_terminal_requirements()` fail and silently filter out tools (`terminal`, `read_file`, `write_file`, `patch`, `search_files`), leaving only `process`.

**Symptoms:**
- Test passes in isolation but fails in full suite
- Expected tool set `{terminal, process, read_file, write_file, search_files, patch}` collapses to `{process}`
- Logs show modal/direct credential errors inside unrelated tool-resolution tests

**Debugging approach:**
- Inspect failing logs for `TERMINAL_MODAL_MODE=direct` and modal credential warnings
- Re-run failing tests with explicit env contamination to confirm hypothesis
- Isolate tests by setting `TERMINAL_ENV=local` and clearing modal/cwd env vars in-test
- Prefer per-test env normalization over global assumptions

### 5) Pairing-path contamination in gateway tests

`PairingStore` uses module-level `PAIRING_DIR` derived from Hermes home at import time. Patching only gateway runner home may not isolate pairing state/rate-limits; full-suite runs can read stale pairing files and skip expected pairing sends.

**Symptoms:**
- Unauthorized DM pairing test passes alone but fails in full suite
- Authorization path logs `Unauthorized user` but no pairing message sent (`adapter.send.await_count == 0`)
- Behavior flips based on prior tests touching pairing/rate-limit files

**Debugging approach:**
- Patch both config/home resolution and pairing storage path in the test (`gateway.config.get_hermes_home` + `gateway.pairing.PAIRING_DIR`)
- Keep pairing artifacts under per-test `tmp_path`
- Re-run targeted test, then full suite, to verify contamination is eliminated

**If 3+ fixes failed:** Question the architecture (Phase 4 step 5).

## Full-suite failure cluster triage

Use this when a single full-suite run surfaces many failures that appear unrelated at first glance.

### Pattern
- A few shared dependencies or fixtures contaminate many tests.
- Some failures disappear when a narrower slice is run.
- The first two fixes are often environment-hardening fixes, not feature changes.

### Workflow
1. Group failures by shared root cause, not by file order.
2. Reproduce each suspected cluster with the smallest relevant slice.
3. Apply a narrow fix that preserves legacy behavior and compatibility.
4. Verify the focused slice first, then an adjacent slice, then the full suite.
5. Record the cluster analysis in durable docs/changelog before moving on.

### Common examples
- Shared module mock contamination across tests (for example a dependency becoming `MagicMock` under full-suite import order).
- Cleanup code assuming real file descriptors when tests use iterators or mock streams.

### Guardrails
- Do not bundle multiple clusters into one change.
- Do not “fix” the symptoms by weakening assertions unless the compatibility boundary truly requires it.
- If the same cluster keeps reappearing after 2–3 attempts, stop and re-check architecture or shared test setup.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, don't fix again. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence, trace data flow | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare, identify differences | Know what's different |
| **3. Hypothesis** | Form theory, test minimally, one variable at a time | Confirmed or new hypothesis |
| **4. Implementation** | Create regression test, fix root cause, verify | Bug resolved, all tests pass |

## Hermes Agent Integration

### Investigation Tools

Use these Hermes tools during Phase 1:

- **`search_files`** — Find error strings, trace function calls, locate patterns
- **`read_file`** — Read source code with line numbers for precise analysis
- **`terminal`** — Run tests, check git history, reproduce bugs
- **`web_search`/`web_extract`** — Research error messages, library docs

### With delegate_task

For complex multi-component debugging, dispatch investigation subagents:

```python
delegate_task(
    goal="Investigate why [specific test/behavior] fails",
    context="""
    Follow systematic-debugging skill:
    1. Read the error message carefully
    2. Reproduce the issue
    3. Trace the data flow to find root cause
    4. Report findings — do NOT fix yet

    Error: [paste full error]
    File: [path to failing code]
    Test command: [exact command]
    """,
    toolsets=['terminal', 'file']
)
```

### With test-driven-development

When fixing bugs:
1. Write a test that reproduces the bug (RED)
2. Debug systematically to find root cause
3. Fix the root cause (GREEN)
4. The test proves the fix and prevents regression

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

**No shortcuts. No guessing. Systematic always wins.**
