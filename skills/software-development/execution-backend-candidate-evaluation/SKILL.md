---
name: execution-backend-candidate-evaluation
description: Compare external execution backends (for example ThClaws, OMX, or legacy OpenCode paths) with real smoke tests and a correctness-first decision rule.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [evaluation, smoke-test, correctness-first, backend-selection, enterprise-agent-fleet]
    related_skills: [test-driven-development, systematic-debugging, omx-coding-agent, thclaws-reference-adapter, enterprise-agent-fleet-phased-integration]
---

# Execution Backend Candidate Evaluation

Use this skill when you need to decide whether an external execution backend is actually usable inside a system such as `enterprise_agent_fleet`, and which backend should be primary vs secondary.

## When to use

- Boss asks whether ThClaws, OMX, OpenCode, or another backend is really usable.
- You need to compare two or more execution backends and remove confusion from a system.
- You need a yes/no answer based on real behavior, not marketing, docs, or repo references alone.
- You want to decide which backend should be primary when correctness matters more than speed.

## Core rule

**Correctness first, speed second.**

If a faster backend is less reliable, it is not the primary backend for correctness-sensitive systems.

## Evaluation workflow

### 1) Define the candidates and the exact task

For each backend, write down:
- executable path
- command shape
- model/endpoint used
- expected exact output
- whether the command is allowed to mutate files

Use exact-response prompts for smoke tests.

### 2) Probe availability before running the smoke

Check:
- binary exists
- wrapper exists if you depend on one
- required flags are supported
- current config does not point to a missing or unsupported model

Do not stop at repository references or configuration assumptions.

### 3) Run a real smoke test for each candidate

Prefer a one-line exact-response prompt.
Examples:
- ThClaws: `Reply exactly: THCLAWS_REAL_SMOKE_OK`
- OMX: `Reply with exactly OMX-EXEC-OK`

Record:
- command used
- exit code
- stdout
- stderr
- duration

### 4) Classify results

Use this decision tree:
- **Both pass** → choose the backend with higher controllability and lower behavioral drift as primary.
- **Only one passes** → use that one as the only usable backend candidate.
- **Neither passes** → neither is ready; do not claim backend readiness.

### 5) Prefer controllability over speed for the primary

When both pass, choose the backend that offers:
- better model/endpoint pinning
- fewer hidden runtime assumptions
- more repeatable smoke results
- easier update gating

In the Boss environment, this often means:
- **ThClaws** as primary for correctness-first usage
- **OMX** as secondary / accelerator / parallel-work backend

### 6) Keep a short decision report

Report in this shape:

```text
Candidate A: PASS/FAIL, duration, exact output
Candidate B: PASS/FAIL, duration, exact output
Decision: primary / secondary / reject
Reason: correctness-first explanation
```

## Practical notes learned from use

- A backend can be available and still not be the right primary choice.
- The fastest backend is not automatically the safest backend.
- Real smoke tests matter more than code search.
- If a smoke test passes, record the exact binary, model, prompt, and output.
- If you need to prove fallback behavior, intentionally break the primary candidate and verify the retry path still succeeds.
- For OMX, a valid pattern is `gpt-5.4-mini` primary with `gpt-5.3-codex` fallback, then force an invalid primary once to confirm fallback to the conservative model.
- For ThClaws, use the known safe wrapper and a local exact-response prompt with `ollama/qwen3.5:cloud` when you need a no-key proof path.
- When comparing ThClaws and OMX fairly, use the same prompt text and the same requested model flag in both runs; then compare only backend behavior, not prompt or model drift.
- `thclaws-safe` can be made keyless-safe by auto-falling back to local Ollama when `OPENAI_API_KEY` is absent; keep `THCLAWS_AUTO_FALLBACK_LOCAL=1` and log the fallback reason so the comparison report shows which path actually ran.
- For local Ollama fallback tests, prefer a minimal mock server or a real local Ollama endpoint that returns exact-response output, and verify the wrapper log includes the fallback reason plus the final model used.

## Anti-patterns

- Declaring a backend ready because the repo contains references to it.
- Declaring a backend ready because docs say it supports a feature.
- Choosing the fastest candidate even though a slower one is more controllable.
- Mixing the comparison itself with system migration work.
- Accepting self-reported success without the exact stdout and exit code.

## Integration with enterprise_agent_fleet

When evaluating backends for fleet use:
- keep the comparison test isolated from production code paths
- store only the final decision in the fleet docs or tests
- make the decision explicit: one primary, one secondary, or none
- if the system only needs one backend, remove the unused candidate from the core path after the comparison passes

## Example acceptance criteria

- Both candidates have a real smoke probe.
- Both probes are executed locally and return exact expected outputs.
- The test suite produces a clear primary/secondary decision.
- The report clearly states which backend should be removed from the core path if it is not needed.
