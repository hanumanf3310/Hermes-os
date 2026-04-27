---
name: standalone-command-mode-surface
description: Build a standalone external command-mode layer (for example `hermes-os` / `hermes-off`) as its own project, with docs, parser, tests, and a clean boundary away from the main fleet codebase.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [standalone, command-mode, parser, docs, tests, boundary]
    related_skills: [writing-plans, test-driven-development, systematic-debugging]
---

# Standalone Command-Mode Surface

Use this skill when the user wants a small command layer that turns a mode on or off via explicit commands, but the **mode it controls** decides whether Hermes operates inside a larger existing system (for example, `enterprise_agent_fleet`).

Typical commands:
- `hermes-os` → enable operating in the fleet
- `hermes-off` → disable that operating mode

## When to Use
- The command surface is conceptually separate from the main product.
- The user explicitly says not to merge the feature into the main system.
- You need a minimal, reusable mode switch with deterministic behavior.
- You want the spec, implementation plan, and tests to live in a standalone sandbox.

## Core Approach
1. Create a **separate project directory** rather than modifying the main fleet repo.
2. Write a short **spec** first, defining:
   - command names
   - default mode
   - transition behavior
   - non-goals / out-of-scope rules
3. Write a compact **implementation plan** with bite-sized tasks.
4. Implement a **pure core library** that owns mode semantics and returns JSON-friendly transition payloads.
5. Add a **small persistence layer** if the command surface needs to remember state across invocations (for example to support `hermes-status`). Keep persistence outside the core so the core stays deterministic.
6. If a status command is required, make it read persisted state and report both machine-friendly and human-friendly forms, but keep **JSON as the default output**. Add an opt-in text format like `--format text` for readable summaries.
7. Add a **thin CLI wrapper** on top of the core library; the CLI should delegate to the library instead of re-implementing logic.
8. If the user wants real shell commands, add **thin shell shims** that call the CLI wrapper instead of duplicating logic in the shell scripts.
9. Add tests for:
   - enable
   - disable
   - status / active-state reporting
   - case/whitespace normalization
   - no-op behavior for non-commands
   - idempotency of repeated commands
   - persistence across invocations
   - JSON-default vs opt-in text formatting
   - CLI/library integration
10. Add a README or usage examples so a parent app can embed the mode layer later.
11. Verify with the full test suite, not just the unit tests for the core module.


## Recommended Structure
- `README.md` — human-friendly overview and usage examples
- `SPEC.md` — canonical behavior contract
- `IMPLEMENTATION_PLAN.md` — task-by-task execution plan
- `TASK_LIST.md` — current task status
- `src/<module>.py` — parser/state logic
- `src/<store>.py` — optional persistence helpers when status must survive separate invocations
- `tests/test_<module>.py` — deterministic behavior tests

## Persistence and Status Commands
If the user wants a command like `hermes-status` that reports whether the system is active:
- add a **small persistence layer** (JSON file is usually enough)
- keep the **core library pure**; persistence should live in a separate store/helper module
- use an environment variable override for the state file path so tests and callers can isolate state (for example `HERMES_OS_STATE_PATH`)
- make `hermes-status` read persisted state and return structured data such as:
  - `active: true/false`
  - `status: ใช้งานระบบ / ไม่ใช้งาน`
  - `display_status: ✅ ใช้งานระบบ / ⛔ ไม่ใช้งาน`

## Output Formatting Rule
For safety and compatibility:
- keep **JSON as the default output** for commands that may be consumed by scripts or agents
- add human-readable output as an **opt-in format** (for example `--format text`)
- make text mode a presentation layer only; do not move business logic into formatting code
- if a shell command must stay stable for automation, never replace JSON with text-only output

## Implementation Pattern
Prefer a tiny API like:
- `ModeState`
- `ModeTransition`
- `apply_command(text, state)`
- `handle_message(text, mode)`

Return structured data such as:
- current mode
- previous mode
- recognized command
- changed flag

Keep the logic pure and deterministic so it can be reused in CLI, chat, or service wrappers later.

## Scope Boundary Rules
- Do **not** couple the standalone command-mode layer to the main enterprise fleet internals by default.
- If the user wants the feature kept as a separate project, use a **separate workspace/project**.
- Avoid adding registry, routing, or agent hierarchy dependencies unless explicitly requested.
- Treat the mode layer as a control surface, not as a full orchestration stack.

## TDD Workflow
1. Write tests for the mode transitions.
2. Run tests and confirm failure if the code is missing.
3. Implement the smallest parser/state logic to pass.
4. Add usage docs.
5. Re-run tests and verify deterministic results.

## Common Pitfalls
- Accidentally merging the command surface into the main fleet repo when the user asked for separation.
- Making mode state implicit or hidden instead of explicit.
- Over-engineering the feature with orchestration, registry, or execution layers.
- Forgetting to document that `hermes-os` / `hermes-off` are control commands, not runtime actions by themselves.
- Forgetting that standalone tests may need an explicit `src/` import path (or editable install) for the CLI/integration layer to import the core module reliably.
- Conflating the *command-mode* project with environment-level wrappers such as RTK; `hermes-os-mode` decides operating mode, while RTK is a separate terminal/session concern.

## Operational Lessons from Real Usage
- `hermes-os-mode` should remain a **standalone project** separate from `enterprise_agent_fleet`.
- The controlling commands are `hermes-os`, `hermes-off`, and `hermes-status`.
- `hermes-status` should default to JSON, with human-readable text only as an opt-in presentation mode.
- State persistence belongs in a small JSON file, and `HERMES_OS_STATE_PATH` should override the default path for testing or isolation.
- Do **not** assume RTK is active just because `hermes-os` is being used; verify RTK separately with environment checks and `rtk --version` / `rtk run "..."` when needed.
- If `HERMES_RTK_WRAP` is enabled in the environment, treat RTK as a terminal wrapper concern, not as part of the hermes-os mode semantics.

## Verification Checklist
- [ ] Spec exists and clearly states non-goals
- [ ] Implementation plan is separate and bite-sized
- [ ] Parser/state module is pure and deterministic
- [ ] Tests cover enable/disable/no-op/idempotency
- [ ] Usage examples show how a parent app can embed the layer
- [ ] The feature remains outside the main fleet scope
- [ ] CLI wrapper prints structured JSON transition payloads
- [ ] Full test suite passes, including CLI/integration coverage

## Example Outcome
A successful implementation gives you a small control layer that can be embedded later, but is already useful on its own:
- `hermes-os` switches the system into the Hermes operating mode for `enterprise_agent_fleet`
- `hermes-off` returns it to normal mode
- `hermes-status` reports whether that mode is active
- unrecognized text leaves the mode unchanged

This skill is reusable whenever a user wants a command-driven mode switch with a strict boundary from the main project.
