#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  cat >&2 <<'USAGE'
Usage: omx_review.sh /path/to/repo "review focus"

Reviews the current git diff with OMX/Codex. Does not push/merge.
USAGE
  exit 2
fi

repo="$1"
shift
focus="$*"
primary_model="${OMX_PRIMARY_MODEL:-gpt-5.4-mini}"
fallback_model="${OMX_FALLBACK_MODEL:-gpt-5.3-codex}"

if [[ ! -d "$repo" ]]; then
  echo "ERROR: repo/workdir does not exist: $repo" >&2
  exit 2
fi

if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: review helper requires a git repository: $repo" >&2
  exit 2
fi

printf 'OMX diff review\n===============\nWorkdir: %s\n\n' "$repo"
printf '## Git status\n'
git -C "$repo" status --short
printf '\n'

review_prompt=$(cat <<EOF
Review the current uncommitted changes in this repository.
Focus: $focus

Rules:
- Read-only review only. Do not modify files.
- Do not push, merge, deploy, or edit anything.
- Report bugs, safety/security risks, test gaps, and unclear assumptions.
- Include concrete file/path references where possible.
EOF
)

if ! omx exec --skip-git-repo-check --sandbox workspace-write --model "$primary_model" -C "$repo" "$review_prompt"; then
  printf '\n## Primary review failed; retrying with fallback model %s\n' "$fallback_model"
  omx exec --skip-git-repo-check --sandbox workspace-write --model "$fallback_model" -C "$repo" "$review_prompt"
fi
