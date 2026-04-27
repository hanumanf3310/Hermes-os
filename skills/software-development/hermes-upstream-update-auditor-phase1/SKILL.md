---
name: hermes-upstream-update-auditor-phase1
description: Read-only upstream update audit workflow for Hermes Agent / Hermes OS. Compares local HEAD against origin/main and latest tag, classifies risk, generates Markdown + JSON reports, and syncs dashboard/route-map updates when workflow-impacting nodes change.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [audit, upstream, read-only, risk, report, dashboard, hermes-os]
---

# Hermes Upstream Update Auditor (Phase 1)

Use this skill when Boss wants to assess an upstream update **before** any live runtime mutation, merge, or `hermes update`.

## When to use

- Compare the current local Hermes Agent checkout against `origin/main`.
- Compare against the latest release tag.
- Classify update risk and backup requirements.
- Produce audit reports for protected behaviors such as `/gpts`, `/model`, provider auth/runtime, and Telegram routing.
- Update `dashboard.html` when the routing/workflow map changes.

## Non-negotiable safety rules

- Phase 1 is **read-only**.
- Do **not** run `hermes update`.
- Do **not** run `git pull`, `git merge`, or `git reset`.
- All terminal commands must be RTK-wrapped when RTK is available:

```bash
rtk run "<command>"
```

- Do not expose secrets, tokens, or credentials in the report.

## Recommended implementation artifact

Primary auditor script:

```text
/home/hanuman3310/hermes-os-mode/tools/hermes_upstream_audit.py
```

Typical outputs:

```text
/home/hanuman3310/hermes-os-mode/reports/upstream-audit/HERMES_UPSTREAM_AUDIT_<timestamp>.md
/home/hanuman3310/hermes-os-mode/reports/upstream-audit/hermes_upstream_audit_<timestamp>.json
```

### Local pre-update command surface

In practice, the reusable user-facing gate lives in `~/.local/bin`:

- `preupdate-hermes` → main gate, human-readable by default
- `preupdate-hermes-json` → same gate with `--json`
- `preupdate-hermes-summary` → thin alias to the main gate

Observed implementation pattern:

- the wrapper should call the fixed script path directly
- if the script is missing, fail fast with a clear stderr message
- the JSON wrapper should be a thin `exec ... --json "$@"` layer
- the summary wrapper should not re-implement any logic

When a caller wants machine parsing, prefer `preupdate-hermes-json`. When a caller wants the final go/no-go summary, prefer `preupdate-hermes` or `preupdate-hermes-summary`.

## Audit workflow

### 1) Establish repo and current state

Check:
- repo path
- current branch
- HEAD commit
- dirty files
- untracked files

Example:

```bash
rtk run "git -C /path/to/hermes-agent status --porcelain=v1"
rtk run "git -C /path/to/hermes-agent rev-parse --abbrev-ref HEAD"
rtk run "git -C /path/to/hermes-agent rev-parse HEAD"
```

### 2) Fetch upstream read-only

```bash
rtk run "git -C /path/to/hermes-agent fetch origin main --tags --prune"
```

### 3) Compare HEAD against origin/main and latest tag

Collect:
- ahead/behind counts
- diff file list
- merge-tree / dry conflict signal
- latest tag if available

Example:

```bash
rtk run "git -C /path/to/hermes-agent rev-list --left-right --count HEAD...origin/main"
rtk run "git -C /path/to/hermes-agent diff --name-status HEAD..origin/main"
rtk run "git -C /path/to/hermes-agent describe --tags --abbrev=0"
```

If using `git merge-tree`, prefer byte-safe handling in code because large diffs may contain non-UTF-8 bytes. Decode with replacement if needed.

### 4) Classify protected behavior impact

Always check these areas:

| Behavior | Typical files |
|---|---|
| `/gpts` | `gateway/run.py`, `gateway/codex_bridge.py`, `gateway/codex_tracker.py` |
| `/model` | `hermes_cli/model_switch.py`, `hermes_cli/models.py`, `hermes_cli/codex_models.py` |
| Telegram routing | `gateway/run.py`, `gateway/platforms/telegram.py` |
| Provider auth/runtime | `hermes_cli/auth.py`, `hermes_cli/providers.py`, `hermes_cli/runtime_provider.py` |

Classify the update risk as one of:
- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

A dirty tree, critical overlap, or conflict signal usually raises the risk.

### 5) Generate Markdown + JSON reports

The report should include:
- repo, branch, HEAD, origin/main, latest tag
- dirty/untracked files
- compare summaries
- protected behavior impact matrix
- risk reasons
- backup requirement
- tool/skill usage summary

### 6) Validate and render-check dashboard if route-map changed

If the task changes decision paths, routing, benchmark roles, or major workflow nodes, update `dashboard.html` and validate it.

Validation steps:

```bash
rtk run "$HOME/.hermes/scripts/validate-dashboard-graph.py --json /home/hanuman3310/hermes-workspace/memory-graph/dashboard.html"
```

Then open the page and verify circles/links render:

```text
browser_navigate("file:///home/hanuman3310/hermes-workspace/memory-graph/dashboard.html")
browser_console(expression="({circles: document.querySelectorAll('circle').length, lines: document.querySelectorAll('line.link').length})")
```

## Pitfalls discovered in practice

- `git merge-tree` output may contain non-UTF-8 bytes; decode safely.
- Naive parsing of `git status --porcelain` can mis-handle paths if not trimmed carefully.
- Report generation should not depend on self-report from agents; use actual git/diff data.
- A HIGH risk result should trigger backup planning before any live update.
- If benchmark results changed agent routing, reflect that in both the plan and `dashboard.html`.
- The pre-update runner should remain read-only and be usable as a single-command gate.
- Use the correct auditor CLI flag: `--output-dir` (not `--out-dir`).
- A small wrapper command in `~/.local/bin` is practical for reuse, e.g. `preupdate-hermes`.

## Benchmark-derived routing lesson

When benchmark evidence exists, record the current recommendation in the audit/report rather than assuming the default model or tool is best.

Current pattern learned in this session:
- `OMX/Codex gpt-5.4-mini` was the fastest correct implementation path when run with `--sandbox workspace-write` and stdin closed.
- `OMX/Codex gpt-5.3-codex` was the fallback implementation path.
- `thClaws qwen3.5:cloud` was the safe verifier / second opinion.
- OpenCode Big Pickle needed retest or alternate invocation after a non-interactive stall.

Treat these as benchmark-derived recommendations, not permanent truth; refresh them when the benchmark changes.

## Operational checklist artifacts

For Boss-facing pre-update readiness, maintain two companion docs:

- `HERMES_PRE_UPDATE_CHECKLIST_WITH_COMMANDS.md` — the **primary** gate document; includes real commands, pass/fail criteria, backup verification, protected-behavior checks, and rollback readiness.
- `HERMES_PRE_UPDATE_QUICK_CHECKLIST.md` — the **secondary** 1-page fast-view checklist for a quick go/no-go glance.
- `HERMES_PRE_UPDATE_README.md` — short usage guide that states the command checklist is the source of truth and the quick checklist is the fast reference.

Recommended workflow:
1. Read the quick checklist for a rapid status glance.
2. Run the command checklist for actual verification.
3. Only consider update after both are satisfied and Boss approves.

## Done criteria

A Phase 1 audit task is done only when:

- local state is compared against upstream
- risk is classified
- report files are written
- backup requirement is clear
- checklist artifacts are created or updated when Boss wants a pre-update workflow
- dashboard is updated if workflow-routing changed
- dashboard validation passes if it was edited

## Minimal report template

```text
Status: HIGH / MEDIUM / LOW / CRITICAL
Backup required: yes/no
Repo: ...
Branch: ...
HEAD: ...
origin/main: ...
Latest tag: ...
Dirty files: ...
Untracked files: ...
Critical overlaps: ...
Next action: ...
```
