#!/usr/bin/env bash
set -euo pipefail

printf 'OMX smoke check\n===============\n\n'

printf '## Paths\n'
command -v omx
command -v codex
command -v node
command -v npm
if command -v tmux >/dev/null 2>&1; then command -v tmux; else echo 'tmux: MISSING'; fi

printf '\n## Versions\n'
omx --version
codex --version
node --version
npm --version
if command -v tmux >/dev/null 2>&1; then tmux -V; fi

primary_model="${OMX_PRIMARY_MODEL:-gpt-5.4-mini}"
fallback_model="${OMX_FALLBACK_MODEL:-gpt-5.3-codex}"

printf '\n## OMX doctor\n'
omx doctor

printf '\n## Codex auth\n'
codex login status

printf '\n## OMX exec smoke\n'
if ! omx exec --skip-git-repo-check --sandbox workspace-write --model "$primary_model" -C /tmp "Reply with exactly OMX-EXEC-OK"; then
  printf '\n## Primary smoke failed; retrying with fallback model %s\n' "$fallback_model"
  omx exec --skip-git-repo-check --sandbox workspace-write --model "$fallback_model" -C /tmp "Reply with exactly OMX-EXEC-OK"
fi

printf '\n## Team diagnostics\n'
omx doctor --team

printf '\nOMX_SMOKE_DONE\n'
