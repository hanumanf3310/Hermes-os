---
name: gemini-cli-hermes-fallback
description: Build a Hermes slash-command wrapper around an external CLI (for example Gemini CLI) that runs the external binary when available and falls back to Hermes OS when the binary is missing, times out, or exits non-zero.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [cli, fallback, external-binary, gateway, slash-command, tests, docs]
    related_skills: [test-driven-development, systematic-debugging, hermes-os-communication-protocol]
---

# Gemini CLI / External CLI Hermetic Fallback

Use this skill when you need a reusable pattern for a user-facing command like `/gemini-cli` (alias `/gemini_cli`) that:
- invokes an external CLI binary when present
- preserves a clean structured result
- falls back to Hermes OS native handling when the binary is missing or fails
- must work in both local CLI and gateway/Telegram entry points

## When to Use
- The command should prefer an external tool but not depend on it.
- The external binary may be missing on some hosts.
- You want a deterministic fallback path that keeps the Hermes UX usable.
- The command needs to exist in both local CLI dispatch and gateway dispatch.
- You need tests to prove happy path and fallback path separately.

## Core Pattern
1. **Create a dedicated helper module** for the external CLI.
   - Resolve the binary path from env first, then from `PATH`.
   - Parse the prompt and optional model override.
   - Return a structured result object with fields such as:
     - `available`
     - `binary`
     - `model`
     - `prompt`
     - `output`
     - `reason`
     - `exit_code`
2. **Keep the helper pure-ish and testable.**
   - Put subprocess invocation behind a single function.
   - Keep parsing and fallback messages separate from dispatch code.
3. **Local CLI handler**:
   - If the external CLI succeeds, print its output.
   - If it fails or is unavailable, print a concise fallback note and queue the prompt for Hermes OS handling.
4. **Gateway/Telegram handler**:
   - Mirror the local CLI behavior.
   - If the external CLI succeeds, return its output.
   - If it fails, return `None` or equivalent so the message falls through to Hermes OS native handling.
5. **Register the command and alias** in the command registry.
   - Example: canonical `gemini-cli`, alias `gemini_cli`.
6. **Update slash-command docs** so users know the command exists and what fallback behavior to expect.
7. **Add tests for both surfaces**:
   - command registry mapping
   - CLI happy path
   - CLI fallback path
   - gateway happy path
   - gateway fallback path
8. **Verify with real execution**:
   - `py_compile`
   - focused pytest slice
   - a real binary smoke test when available

## Recommended File Layout
- `hermes_cli/gemini_cli.py` — helper for binary resolution, parsing, subprocess execution, and fallback messaging
- `hermes_cli/commands.py` — registry entry for the slash command
- `cli.py` — local command handler
- `gateway/run.py` — Telegram/gateway handler
- `tests/cli/test_gemini_cli_command.py` — CLI tests
- `tests/gateway/test_gemini_cli_command.py` — gateway tests
- `tests/hermes_cli/test_commands.py` — registry tests
- `website/docs/reference/slash-commands.md` — slash-command docs
- `website/docs/user-guide/features/fallback-providers.md` — fallback behavior docs

## Testing Checklist
- [ ] `py_compile` passes for helper, CLI, gateway, and tests
- [ ] registry resolves both `gemini-cli` and `gemini_cli`
- [ ] CLI returns Gemini output when binary is available
- [ ] CLI queues prompt back to Hermes OS when unavailable
- [ ] gateway returns Gemini output when binary is available
- [ ] gateway falls through to Hermes OS when unavailable
- [ ] docs mention fallback behavior clearly
- [ ] real smoke test proves the external CLI path works
- [ ] research workflow tests cover summary prompt generation, verification prompt generation, and fallback prompt generation

## Pitfalls
- Don’t treat the external binary as mandatory if the UX must remain available.
- Don’t duplicate parsing logic in CLI and gateway; centralize it in the helper.
- Don’t silently swallow failures without queuing a Hermes fallback.
- Don’t let docs imply the external tool is always installed.
- Don’t skip the fallback-path test; that is the whole point of the pattern.
- If the external CLI times out, treat it as a fallback condition, not a hard crash.
- Keep the fallback note short so the user understands why Hermes took over.

## Reusable Implementation Notes
- Use a parser that accepts both `--model value` and `--model=value`.
- Allow unknown flags to stay part of the prompt when the parser is meant to be forgiving.
- Resolve the binary from an env override first for testability.
- Use a clear timeout env var so operators can tune behavior without code changes.
- Return a machine-readable result object from the helper so tests and logs can inspect it.
- Wire the command through the active registry/dispatch path, not just docs, so the alias is actually executable from CLI and gateway surfaces.
- Treat the external CLI as a summarizer/assistant, not a source of truth for realtime claims; keep Hermes verification in the loop.
- When adding a research workflow, split it into: evidence bundle → Gemini summary prompt → Hermes verification prompt → optional fallback prompt when the binary is unavailable.
- For structured research commands, keep the evidence bundle and the original user intent intact so fallback can continue without re-asking for context.
- If the command is available in a gateway/chat surface, prefer returning `None`/fallthrough on hard failure rather than inventing a partial answer.
- Verify with `py_compile`, focused pytest slices, and one real binary smoke test before calling the integration done.

## Verification Pattern
A good end-to-end check looks like:
1. unit test parsing
2. unit test registry entry
3. unit test CLI happy path with a mocked binary
4. unit test CLI fallback path with missing binary
5. unit test gateway happy path with a mocked binary
6. unit test gateway fallback path with missing binary
7. real smoke test using the actual binary if present

## Example Contract
- Command: `/gemini-cli <prompt>`
- Alias: `/gemini_cli`
- Success: print Gemini output
- Failure: explain that Gemini is unavailable and hand the prompt back to Hermes OS

## Why this skill exists
This pattern is reusable anywhere Hermes wants to prefer an external CLI tool without making it a hard dependency. It preserves UX, keeps behavior deterministic, and gives you a clean place to hang tests and docs.
