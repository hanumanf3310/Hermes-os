#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  cat >&2 <<'USAGE'
Usage: omx_code.sh /path/to/repo "task prompt"

Runs a bounded one-shot OMX/Codex coding task with Boss safety constraints.
USAGE
  exit 2
fi

repo="$1"
shift
prompt="$*"
primary_model="${OMX_PRIMARY_MODEL:-gpt-5.4-mini}"
fallback_model="${OMX_FALLBACK_MODEL:-gpt-5.3-codex}"

if [[ ! -d "$repo" ]]; then
  echo "ERROR: repo/workdir does not exist: $repo" >&2
  exit 2
fi

printf 'OMX one-shot code task\n======================\n'
printf 'Workdir: %s\n\n' "$repo"

if git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf '## Git state before\n'
  git -C "$repo" status --short
  printf '\n'
else
  printf '## Git state before\nNot a git repository; proceeding only because omx exec supports arbitrary workdirs.\n\n'
fi

safe_prompt=$(cat <<EOF
Task: $prompt

Safety constraints:
- Stay inside this repository/workdir.
- Do not push, merge, deploy, or edit secrets/credentials.
- Preserve existing behavior unless explicitly requested.
- Prefer minimal, reviewable changes.
- Run the narrowest relevant tests/checks that are available.

Required final report:
- Files changed
- Tests/commands run and results
- Any failures or unverified assumptions
- Remaining risks / follow-up required
EOF
)

printf '## Running omx exec\n'
if ! omx exec --skip-git-repo-check --sandbox workspace-write --model "$primary_model" -C "$repo" "$safe_prompt"; then
  printf '\n## Primary model failed; retrying with fallback model %s\n' "$fallback_model"
  omx exec --skip-git-repo-check --sandbox workspace-write --model "$fallback_model" -C "$repo" "$safe_prompt"
fi

printf '\n## Git state after\n'
if git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$repo" status --short
else
  echo 'Not a git repository.'
fi
