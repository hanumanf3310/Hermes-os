---
name: slash-command-workflow-integration
description: Add a new Hermes slash command that wraps a reusable helper workflow, wires it through CLI and gateway dispatch, and verifies fallback behavior with tests and docs.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [slash-command, workflow, cli, gateway, tests, docs, fallback]
    related_skills: [test-driven-development, systematic-debugging, standalone-command-mode-surface]
---

# Slash Command Workflow Integration

Use this skill when introducing a new Hermes command that is more than a simple one-line action: it parses user input, calls a helper workflow, and must work in both the local CLI and the messaging gateway.

Typical examples:
- `/gemini-cli <prompt>` with fallback to Hermes OS
- `/gemini-research --question ... --evidence ...` that runs evidence → summary → verification
- Any command that needs a structured helper, a registry entry, and consistent fallback behavior

## When to Use
- The command has a reusable helper module behind it.
- The command must be available in both CLI and gateway/Telegram paths.
- The command needs a fallback path when an external tool or binary is unavailable.
- You need tests before/after implementation to prove behavior.
- Documentation and slash-command registry must stay in sync.

## Core Pattern
1. Create a small helper module for the workflow.
   - Keep parsing, prompt building, and result formatting out of dispatch code.
   - Return structured dataclasses or plain dicts for easy testing.
2. Add a command registry entry in one place.
   - Include aliases, args hints, and a clear description.
3. Wire CLI dispatch to the helper.
   - If the helper succeeds, print/queue the result.
   - If it fails or is unavailable, route to the Hermes fallback path.
4. Wire gateway dispatch separately.
   - Return a text response for the chat platform.
   - Preserve the original prompt/evidence for fallback routing.
5. Add docs to the slash-command reference and any fallback-providers page.
6. Add tests for:
   - command registry presence
   - CLI happy path
   - CLI fallback path
   - gateway happy path
   - gateway fallback path
   - helper parsing/formatting
   - docs consistency when relevant
7. Run syntax checks and the focused test set first, then broaden to the nearby registry suite.

## Recommended Helper Design
Prefer helper functions like:
- `parse_<command>_request(text)`
- `run_<workflow>(...)`
- `format_<workflow>_result(result)`
- `build_<workflow>_prompt(...)`

Use structured results with fields such as:
- `available`
- `reason`
- `output` / `summary`
- `verification_prompt`
- `fallback_prompt`
- `model` / `binary`
- `exit_code`

For evidence-backed research workflows, split the helper into three explicit prompt builders:
- summary prompt for the external model
- verification prompt for Hermes OS
- fallback prompt when the external tool is unavailable

This keeps the command’s contract testable and makes it obvious that the external model is a summarizer, not the source of truth.
## Fallback Rules
- If the external tool is missing, fail closed into Hermes OS.
- Do not silently swallow failures.
- Preserve the user’s original intent so Hermes can continue the task.
- For evidence-backed workflows, Hermes verification should remain the final gate.

## TDD Workflow
1. Write tests for the new helper and command registration.
2. Run the tests and confirm they fail for the missing behavior.
3. Implement the helper first.
4. Wire CLI dispatch.
5. Wire gateway dispatch.
6. Add docs.
7. Re-run the focused tests, then the registry test suite.

## Verification Checklist
- [ ] Registry entry added once and resolved via alias/canonical name
- [ ] CLI command works on the happy path
- [ ] CLI command falls back cleanly when unavailable
- [ ] Gateway command works on the happy path
- [ ] Gateway command falls back cleanly when unavailable
- [ ] Helper parsing/formatting is tested directly
- [ ] Slash-command docs match the real behavior
- [ ] Syntax checks and pytest pass
- [ ] If the command uses an external summarizer, Hermes verification still runs last
- [ ] Focused tests cover helper, CLI, gateway, and registry before broader suites
- [ ] A real smoke test proves the external binary path before declaring the command ready

## Common Pitfalls
- Putting workflow logic directly inside dispatch code
- Updating CLI but forgetting gateway, or vice versa
- Forgetting to preserve the original prompt for fallback
- Adding docs before the command actually works
- Hardcoding model/tool choices in multiple places instead of using the helper
- Skipping registry tests, which causes help/autocomplete drift

## Example Outcome
A good implementation adds a command that feels native to Hermes but still uses a dedicated helper behind the scenes:
- the command accepts structured arguments
- the helper produces a summarized or formatted result
- the fallback path returns control to Hermes OS without losing the user’s request
- CLI, gateway, and docs all agree on the command behavior

This skill is reusable for future commands that orchestrate an external CLI, summarizer, verifier, or other workflow component.
