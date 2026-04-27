---
name: hermes-agent-upstream-update-impact-audit
description: Safely assess whether updating NousResearch/hermes-agent will impact a customized local Hermes runtime before pulling or merging.
version: 1.0.1
tags: [hermes-agent, git, update, impact-analysis, gateway, model-picker]
---

# Hermes Agent Upstream Update Impact Audit

Use this skill when Boss asks whether updating `https://github.com/NousResearch/hermes-agent` will affect the current local Hermes setup.

## Core Rule
Do **not** run `git pull`, `git merge`, `git reset`, or write to runtime files during the audit. Use fetch-only and dry-run comparisons. Boss requires explicit approval before impactful changes.

## Boss end-user update mode
Boss is an end-user of Hermes, not the upstream project owner. When Boss must run the official `hermes update`, treat `/gpts` and `/model` as protected local behavior that may need to be restored afterward. Trigger phrases such as `model gpts`, `restore model gpts`, `หลัง update แล้ว restore model gpts`, or `กัน /gpts /model พัง` mean:
1. Prepare/backup current local `/gpts` and `/model` state before update when possible.
2. Let Boss run the official `hermes update` flow if required; do not make Boss manage upstream branches unless necessary for recovery.
3. After update, audit what changed and restore only the missing local behavior on top of the updated code.
4. Do not copy old whole files (especially `gateway/run.py`) over updated upstream files; port the required command surface and parity logic carefully.
5. Run focused sentinel tests and Telegram smoke checks before claiming the update is safe.

Operational handoff for Boss:
- Before update: Boss can say `model gpts ก่อน hermes update`; capture backup/evidence, then tell Boss when it is safe to run `hermes update`.
- After update: Boss can say `restore model gpts`; verify command surfaces, reapply missing protected behavior, run tests, then ask Boss to try `/gpts` and `/model` in Telegram.
- If Boss already updated and something broke, start in restore mode immediately; do not lecture about pre-update branch discipline.

## Workflow

### 1) Inspect local repo state
```bash
cd ~/.hermes/hermes-agent
git status --short
git branch --show-current
git remote -v
git log --oneline --decorate -5
git rev-parse HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true
```

Pay special attention to uncommitted or untracked local custom files such as:
- `gateway/run.py`
- `gateway/platforms/telegram.py`
- `hermes_cli/model_switch.py`
- `hermes_cli/models.py`
- `hermes_cli/providers.py`
- `hermes_cli/codex_models.py`
- `gateway/codex_bridge.py`
- `gateway/codex_tracker.py`

### 2) Fetch only
```bash
git fetch origin main --tags --prune
git rev-list --left-right --count HEAD...origin/main
git log --oneline --decorate HEAD..origin/main --max-count=30
git log --oneline --decorate origin/main..HEAD --max-count=10
```

Interpretation:
- Left count = local commits ahead of upstream.
- Right count = upstream commits not in local.
- The `hermes --version` banner may show a release version such as `v0.11.0 (2026.4.23)` even when local `HEAD` is not exactly on that release tag. Verify with tag/HEAD/origin comparisons before telling Boss whether the installed runtime matches a release.
- The CLI "commits behind" number can differ after a fresh `git fetch`; report both the observed CLI warning and the fetched git count when they differ.

### 2b) Release tag relationship check
When Boss asks whether the installed Hermes is a specific release tag, compare `HEAD`, the release tag, and `origin/main` explicitly:
```bash
hermes --version || true
cd ~/.hermes/hermes-agent
git fetch origin main --tags --prune
TAG=v2026.4.23  # replace with Boss's target tag
printf 'HEAD='; git rev-parse HEAD
printf 'TAG='; git rev-parse "$TAG"
printf 'origin_main='; git rev-parse origin/main
printf 'is_tag_ancestor_of_HEAD='; git merge-base --is-ancestor "$TAG" HEAD && echo yes || echo no
printf 'is_HEAD_ancestor_of_origin_main='; git merge-base --is-ancestor HEAD origin/main && echo yes || echo no
printf 'nearest_tag='; git describe --tags --always --dirty 2>/dev/null || true
printf 'HEAD_vs_origin_main(left ahead/right behind)='; git rev-list --left-right --count HEAD...origin/main
printf 'tag_vs_HEAD(left tag-only/right HEAD-only)='; git rev-list --left-right --count "$TAG"...HEAD
printf 'tag_vs_origin_main(left tag-only/right main-only)='; git rev-list --left-right --count "$TAG"...origin/main
```

Interpretation example:
- `is_tag_ancestor_of_HEAD=yes` means the installed source includes that release lineage even if it is not exactly on the tag.
- `nearest_tag=v2026.4.23-N-gHASH-dirty` means local HEAD is N commits after the release tag and has local modifications.
- If `HEAD...origin/main` shows `0 117`, local has no commits ahead of upstream but is 117 commits behind after fetch.

### 3) Measure update size and overlap
```bash
git diff --name-status HEAD..origin/main
git diff --stat HEAD..origin/main | tail -20
git status --short
```

Compute overlap between upstream-changed files and local modified/untracked files. High-risk overlap usually includes gateway/model/config files.

### 4) Dry-run conflict check
Prefer dry-run merge-tree rather than an actual merge:
```bash
git merge-tree --write-tree HEAD origin/main 2>&1 | head -120
```

If this reports `CONFLICT`, list the exact files and treat the update as requiring a controlled branch, not direct pull.

For very large output, grep only conflict markers:
```bash
git merge-tree $(git merge-base HEAD origin/main) HEAD origin/main \
  | grep -E '^(changed in both|removed in|CONFLICT)' | head -200
```

### 5) Identify critical upstream changes
Look for commits/files that affect Boss-critical paths:
- `/model`, `hermes_cli/model_switch.py`, `hermes_cli/models.py`, `gateway/platforms/telegram.py`
- `/gpts`, `gateway/run.py`, `gateway/codex_bridge.py`, `gateway/codex_tracker.py`
- provider auth/runtime: `hermes_cli/auth.py`, `hermes_cli/runtime_provider.py`, `hermes_cli/providers.py`
- core runtime: `run_agent.py`, `agent/auxiliary_client.py`, `agent/model_metadata.py`
- tools/skills: `tools/skills_tool.py`, `hermes_cli/commands.py`

Useful targeted stats:
```bash
git diff --shortstat HEAD..origin/main -- gateway/run.py gateway/platforms/telegram.py hermes_cli/model_switch.py hermes_cli/models.py run_agent.py agent/auxiliary_client.py
```

### 6) Report verdict
Classify the update:
- **Low risk**: clean tree, small behind count, no critical overlap, no conflicts.
- **Medium risk**: clean tree but critical upstream changes or many files changed.
- **High risk**: uncommitted local custom changes, local commits ahead, conflicts, or large gateway/model/runtime changes.

For high risk, recommend:
1. Commit or stash local changes.
2. Back up untracked local custom files.
3. Create a staging branch.
4. Merge `origin/main` there.
5. Resolve conflicts.
6. Re-apply local custom patches.
7. Run targeted tests.
8. Test Telegram commands manually before touching live runtime.

## Targeted Tests After Merge
Run only relevant tests first:
```bash
pytest tests/hermes_cli/test_model_switch*.py tests/hermes_cli/test_codex_cli_model_picker.py tests/gateway/test_model_command_custom_providers.py -q
pytest tests/gateway/test_gpts_pretty_card.py tests/gateway/test_codex_status_regressions.py -q
pytest tests/gateway/test_telegram_network.py tests/gateway/test_telegram_group_gating.py -q
```

Then manually verify in Telegram:
- `/model` picker opens.
- OpenAI Codex model list includes expected live models (e.g. `gpt-5.5` if provider reports it).
- Ollama Launch picker preserves recommended models.
- `/gpts` active probe works and reset time is shown as Bangkok AM/PM time.

## Pitfalls
- Saying “safe to update” after only checking GitHub release notes.
- Running `git pull` while local working tree has uncommitted custom patches.
- Ignoring untracked files; local features such as `/gpts` may live in untracked files.
- Treating docs/test churn as harmless when core files also changed.
- Forgetting that Boss’s personal Google ME/TTB files under `~/.hermes/google_me` are outside the `hermes-agent` repo and usually unaffected by a repo update.
