---
name: omx-coding-agent
description: Install, verify, and operate oh-my-codex (OMX) as a Codex coding-team backend from Hermes, with safety gates for use inside Hermes OS and normal Hermes mode.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Coding-Agent, Codex, OMX, Multi-Agent, Worktree, HUD, Verification]
    related_skills: [opencode, hermes-os-integration, writing-plans, rtk-mes]
---

# OMX Coding Agent

Use oh-my-codex (`omx`) as an external Codex workflow/team runtime orchestrated by Hermes. Hermes remains the coordinator; OMX is a backend for Codex coding workflows, team/worktree execution, HUD/status, and plan-first coding flows.

## When to Use

- Boss asks to use oh-my-codex / OMX.
- A coding task is medium/large enough to benefit from Codex workflow routing.
- You need Codex team/worktree-oriented execution (`$team` / `omx team`).
- You want a reusable coding backend usable both inside Hermes OS and outside Hermes OS.
- You need to install/update/verify OMX readiness.

Prefer Hermes direct tools for tiny edits, simple file inspection, or low-risk one-file changes.

## Safety Model

- Never push, merge, or apply impactful/policy-sensitive changes without Boss approval.
- Do not treat `omx doctor` alone as full readiness; also verify Codex auth and a real `omx exec` smoke test.
- For parallel/team work, require worktree isolation or OMX-managed team runtime.
- Always report changed files, tests run, failures, and residual risks.
- If OMX is unavailable or auth fails, report degraded mode and fall back to Hermes direct/Fleet/OpenCode only if safe.

## Installation / Update Procedure

Use RTK wrapping when available:

```bash
rtk run "npm install -g @openai/codex oh-my-codex"
```

Then verify versions:

```bash
rtk run "bash -lc 'command -v omx; command -v codex; omx --version; codex --version; npm list -g --depth=0 @openai/codex oh-my-codex'"
```

Run setup/refresh:

```bash
rtk run "omx setup --scope user --force"
```

Run doctor:

```bash
rtk run "omx doctor"
```

Run team diagnostics when team mode may be used:

```bash
rtk run "omx doctor --team"
```

## Full Readiness Smoke Test

```bash
rtk run "bash -lc 'omx doctor; codex login status; omx exec --skip-git-repo-check -C /tmp \"Reply with exactly OMX-EXEC-OK\"'"
```

Success criteria:
- `omx doctor` has 0 failed checks.
- `codex login status` shows a valid login.
- `omx exec` prints `OMX-EXEC-OK`.
- `omx doctor --team` passes before using team mode.

Explore Harness status on Boss WSL:
- Initially `omx doctor` warned that Rust/Cargo or a compatible prebuilt was missing.
- Fixed by installing Rust/Cargo via rustup user-level and running `npm run build:explore:release` inside the oh-my-codex package.
- Built harness: `/home/hanuman3310/.hermes/node/lib/node_modules/oh-my-codex/bin/omx-explore-harness`.
- Current `omx doctor`: 14 passed, 0 warnings, 0 failed.
- Smoke check `omx explore --prompt "run ls ."` succeeded.

## Operating Modes

### Tiny task — Hermes direct
Use Hermes file/search/patch/terminal tools directly. Do not invoke OMX just to change a typo.

### Bounded coding — `omx exec`
Use for one-shot code changes or analysis in one workdir.

For correctness-critical implementation on Boss WSL, prefer an explicit model and writable sandbox inside a disposable/worktree workspace:

```bash
rtk run "omx exec --skip-git-repo-check --sandbox workspace-write --model gpt-5.4-mini -C /path/to/repo 'Implement X. Do not push. Run tests and summarize changes.' </dev/null"
```

Notes from benchmark practice:
- `--sandbox workspace-write` is required when the task needs file edits. Without it, Codex may report `Blocked by environment constraints: repository is mounted read-only` and fail without modifying files.
- Redirect stdin from `/dev/null` or pass a prompt argument explicitly; otherwise `omx exec`/Codex can stall at `Reading additional input from stdin...`.
- Use `gpt-5.4-mini` as the default implementation model when available.
- Use `gpt-5.3-codex` as the conservative fallback when the primary model is unavailable or unstable.
- When validating fallback behavior, intentionally set an invalid primary model once and confirm the retry path still returns `OMX-EXEC-OK`.
- Do not assume the model in the prompt/skill matches the model actually used by the runtime. If Boss asks what model was used, treat the exact `omx exec` output as source of truth.
- In this workspace, the successful smoke test output showed `gpt-5.5`, so capture the observed model when auditing or comparing runs.
- Always verify with targeted tests and hidden/regression tests; do not accept the agent self-report as proof.

### Read-only repo lookup — `omx explore`
Use for architecture discovery when explore harness is ready:

```bash
rtk run "omx explore --prompt 'Find where team state is written'"
```

If explore harness warning exists, use Hermes search/read tools or install Rust/Cargo first.

### Plan-first workflow
Use for risky or multi-step coding:

```text
$deep-interview "clarify the change"
$ralplan "approve the safest implementation path"
$ralph "carry the approved plan to completion"
```

### Parallel/team workflow
Use when the task is big enough for multiple workers and file isolation matters:

```bash
rtk run "omx team 3:executor 'execute the approved plan in parallel; do not push; report changed files and tests'"
rtk run "omx team status <team-name>"
rtk run "omx team shutdown <team-name>"
```

## Helper Scripts Available Now

This skill ships executable helper scripts:

```bash
# full readiness check: versions, doctor, auth, exec smoke, team doctor
~/.hermes/skills/autonomous-ai-agents/omx-coding-agent/scripts/omx_smoke.sh

# bounded one-shot coding task with Boss safety constraints
~/.hermes/skills/autonomous-ai-agents/omx-coding-agent/scripts/omx_code.sh /path/to/repo "task prompt"

# read-only review of current git diff
~/.hermes/skills/autonomous-ai-agents/omx-coding-agent/scripts/omx_review.sh /path/to/repo "review focus"
```

The future chat/CLI command wrapper may expose aliases:

- `omx-smoke` → `scripts/omx_smoke.sh`
- `omx-code "<task>"` → `scripts/omx_code.sh <repo> "<task>"`
- `omx-explore "<question>"` → read-only repository lookup when Explore Harness is fixed/ready
- `omx-plan "<task>"` → plan-first flow, no writes unless approved
- `omx-team "<task>"` → parallel team/worktree workflow after preflight
- `omx-review` → `scripts/omx_review.sh <repo> "<focus>"`

Routing rule:
- small/simple → Hermes direct
- medium bounded → `omx exec`
- large/risky → plan first
- parallel/multi-file → `omx team` / `$team`

## Boss WSL Verified Baseline

Verified install state from 2026-04-26:

- `oh-my-codex v0.14.4` at `/home/hanuman3310/.hermes/node/bin/omx`
- `codex-cli 0.125.0` at `/home/hanuman3310/.hermes/node/bin/codex`
- Node.js `v22.22.2`, npm `10.9.7`, tmux `3.4`, RTK `0.37.1`
- `omx setup --scope user --force` completed
- `omx doctor`: 14 passed, 0 warning, 0 failed
- `omx explore --prompt "run ls ."`: succeeded
- Rust/Cargo installed user-level: `cargo 1.95.0`, `rustc 1.95.0`
- Explore harness built at `/home/hanuman3310/.hermes/node/lib/node_modules/oh-my-codex/bin/omx-explore-harness`
- `codex login status`: Logged in using ChatGPT
- `omx exec --skip-git-repo-check -C /tmp "Reply with exactly OMX-EXEC-OK"`: succeeded
- `omx doctor --team`: passed

## Pitfalls

- `omx doctor` can be green enough locally but still not prove model execution; always smoke with `omx exec`.
- `omx explore` now has a built harness on Boss WSL, but if future updates remove/rebuild package assets, rerun: `cd /home/hanuman3310/.hermes/node/lib/node_modules/oh-my-codex && npm run build:explore:release`.
- In Hermes terminal calls, use `bash -lc 'set -o pipefail ...'` if you need pipefail. Plain `sh` can fail with `set: Illegal option -o pipefail`.
- Shell loops embedded in quoted commands can lose `$c` expansion if quoting is wrong; prefer simple commands or `bash -lc` with carefully quoted script.
- `omx explore` may warn about missing Rust harness/prebuilt; do not assume explore works until specifically tested.
- Native Windows is not the recommended path for OMX team mode; WSL2/Linux with tmux is safer.
- Updating OMX can change defaults quickly. After `omx update` or npm update, rerun setup + doctor + auth + smoke.

## Reporting Template

```text
OMX status: ✅/⚠️/❌
Version: oh-my-codex X, codex-cli Y
Doctor: A passed, B warnings, C failed
Auth: logged in / not logged in
Smoke: OMX-EXEC-OK / failed reason
Team: passed / not checked / failed
Warnings: ...
Next action: ...
```
