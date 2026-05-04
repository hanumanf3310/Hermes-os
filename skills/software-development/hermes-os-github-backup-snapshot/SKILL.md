---
name: hermes-os-github-backup-snapshot
description: Build a single GitHub repo backup snapshot for Hermes-os, including only restoreable Hermes-related sources, wrappers, manifests, and docs while excluding secrets and runtime noise.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [backup, snapshot, github, restore, hermes-os, single-repo, secrets-safe]
---

# Hermes OS GitHub Backup Snapshot

Use this skill when Boss wants a **single-repo** GitHub backup of Hermes-os that can be downloaded and restored later with minimal manual reconstruction, *including a readiness audit before any push*.

## When to use

- Boss asks to back up Hermes-os into one GitHub repository.
- Boss wants the repo to be restoreable, not just a file dump.
- You need to select only Hermes-related assets from multiple local locations.
- You need to publish the snapshot safely without leaking secrets or runtime noise.
- You need to check whether a backup is actually push-ready before claiming it is complete.

## Core rules

- Keep the backup in **one repository**.
- Include only what is needed to restore or continue using Hermes-os.
- Exclude secrets, logs, caches, build artifacts, sessions, and runtime junk.
- Never print or commit raw credentials; replace them with `[REDACTED]` in any human-facing output.
- If a git remote or push command depends on `Repo.env`, use it as the input source but do not commit the file itself.
- Use `Repo.env.example` instead of the real `Repo.env`.
- Verify the repo after push; do not claim success from the commit alone.
- When the backup is a **checkpoint before a core update**, the restore target must be runnable like the system at backup time, not merely an archival file dump. Capture restore-critical command/gateway/helper files and verify them from a fresh clone.
- After push plus fresh-clone verification passes, the verified Git checkpoint branch is the **source of truth** for restore. `~/hermes-agent-backups` is only a temporary local fallback while remote push/verification is blocked.
- Do not let local bundle storage grow. After the Git checkpoint is verified, delete temporary bundles or keep at most one newest, explicitly justified emergency bundle.

## Typical source inventory

Common Hermes-related inputs may include:

- core repo(s): `hermes-agent`, `hermes-workspace`
- wrapper commands in `~/.local/bin`
- selected skill bundles in `~/.hermes/skills`
- Hermes-specific helper scripts or adapters
- restore docs and manifests
- thClaws or other backend material only if it is part of the Hermes restore path

Do not assume everything on disk belongs in the snapshot. Inventory first.

## Recommended repository layout

A practical layout for the backup repo:

```text
README.md
Repo.env.example
.gitignore
bin/
restore/
skills/
sources/
thclaws/
```

Optional additions if they are useful and safe:

- `restore/MANIFEST.json`
- `restore/BOOTSTRAP.md`
- `docs/` for restore notes or inventory summaries

## Workflow

### 0) Readiness audit before push

Before building or pushing the backup, verify the target is genuinely ready.

Check:
- the actual source directory is a git repository
- the repository is on the intended branch
- `git status` is understood before any add/commit
- the destination repo is reachable with `git ls-remote`
- GitHub auth exists for write access (`gh auth status`, `GITHUB_TOKEN`, credential helper, or SSH)
- the remote head is not being assumed to match local history
- a push target branch is chosen intentionally, especially if the remote `main` already exists

If auth is missing, the remote is read-only, or the source checkout is not the repo you meant, stop and fix that before doing any packaging work.

### 1) Establish scope

Before writing anything, identify:
- which repos or directories are Hermes-os relevant
- which wrappers are required for normal operation
- which skills are actually needed for restore/use
- which files must be excluded because they are runtime-only or secret-bearing

Prefer evidence from local files and command inventory over assumptions.

### 2) Build a restoreable snapshot

Create a clean backup repo and copy only the selected inputs into a stable layout.

Recommended steps:
- create `bin/` for command wrappers
- create `skills/` for selected reusable skills
- create `sources/` for imported repo material
- create `thclaws/` only if it is part of the supported restore path
- create `restore/BOOTSTRAP.md` with restore instructions
- create `restore/MANIFEST.json` with the inclusion scope
- add `Repo.env.example` showing required variable names but no secrets

### 3) Exclude unsafe or noisy content

Common exclusions:
- `.env`, `Repo.env`, token files
- `node_modules/`
- `__pycache__/`
- `.pytest_cache/`
- `dist/`, `build/`, `target/`
- logs, sessions, crash dumps
- browser caches, temp files, backups
- generated artifacts that can be rebuilt

If a file is borderline, ask whether it is required for restore; otherwise leave it out.

### 4) Add a restore manifest and bootstrap guide

The backup is much more useful if it includes:
- a manifest of what was included
- a bootstrap guide describing restore order
- notes about what was intentionally excluded
- any manual steps required after cloning

The restore docs should make it possible to get back to a working Hermes-os state without guessing.

### 5) Commit and push safely

Before push:
- check `git status`
- confirm no secrets slipped in
- confirm the destination repo is the intended one
- confirm the branch name
- run `git diff --cached --check` and fix whitespace/errors before committing
- confirm forbidden paths are not staged (`.env`, `Repo.env`, `.hermes/`, `reports/`, `venv/`, `.venv/`, caches)
- confirm local git identity exists; if missing, prefer repo-local `git config user.name ...` and `git config user.email ...` over global changes unless Boss asked for global setup

If authentication requires a token from `Repo.env`, use it temporarily and keep the canonical remote clean afterward.

When Boss says the Git upload data is in Fact Store / `Repo.env`, search Fact Store before concluding auth is missing. Known Hermes OS upload facts may point to a Windows path such as `D:\Back up code\Exe Upload To Git\Repo.env`, which resolves in WSL as `/mnt/d/Back up code/Exe Upload To Git/Repo.env`. Read only key names and non-secret values in reports; redact token/key/secret/password values. Expected keys may include `GIT_NAME`, `GIT_EMAIL`, `GIT_TOKEN`, `GIT_REPO_URL`, `GIT_BRANCH_MODE`, and `GIT_BRANCH_NAME`.

For one-off authenticated pushes from `Repo.env`, prefer an ephemeral Git HTTP header or temporary remote over changing the canonical remote. Do not print the token. A safe Python pattern is: parse `Repo.env`, base64 encode `x-access-token:<GIT_TOKEN>`, run `git -c http.https://github.com/.extraheader="AUTHORIZATION: basic <encoded>" push ...`, redact both raw and encoded token from captured output, then verify with `git ls-remote --heads`.

If the intended remote branch already exists and is not a fast-forward target (`git merge-base --is-ancestor` fails, or ahead/behind shows divergence), do **not** force-push by default. Prefer a new uniquely named backup branch such as `<branch>-<shortsha>` unless Boss explicitly approves `--force-with-lease` or a merge/rebase strategy.

If a moving backup branch rejects as non-fast-forward during a checkpoint backup, treat the push as partially successful only if a new immutable checkpoint branch was created and verified. Make the immutable branch (for example `hermes-os-checkpoint-YYYYMMDD-HHMM-<shortsha>`) the canonical restore ref in the final report instead of pretending the moving branch is current. Then fetch/verify both refs and state clearly which one should be used for restore.

If the remote URL is malformed or credential handling fails, stop and fix the URL/credential flow rather than trying repeated blind pushes.

If commit succeeds but push is blocked by missing GitHub authentication, GitHub size limits, or push protection, create a verified local fallback bundle before stopping or while repairing the push:

```bash
mkdir -p ~/hermes-agent-backups
git bundle create ~/hermes-agent-backups/<branch>-<shortsha>.bundle <branch>
git bundle verify ~/hermes-agent-backups/<branch>-<shortsha>.bundle
```

Report the local commit SHA, bundle path/size, `git bundle verify` output, and the fact that `git ls-remote --heads origin <branch>` is still empty if remote push is not verified. This preserves a restore point without pretending the remote backup is complete.

Once remote push succeeds and a fresh clone verifies `restore/MANIFEST.json`, restore-critical files, and hashes, promote the Git checkpoint branch to the canonical restore source. Then clean local fallback bundles instead of keeping `~/hermes-agent-backups` as a parallel truth source. If Boss explicitly wants an offline fallback, keep only the newest verified emergency bundle and record why it remains.

If GitHub rejects the push for a file over 100MB, do not switch to Git LFS by default for checkpoint backups. Exclude generated archives and reports (for example `reports/`, `*.tar.gz`) unless Boss explicitly asks to preserve them, update `restore/MANIFEST.json` with the exclusion, amend the commit, and push again.

If GitHub push protection flags secrets inside a broad copied directory (for example an unrelated skill containing OAuth examples), narrow the backup scope instead of bypassing push protection. Prefer selected restore-critical skills over dumping all of `~/.hermes/skills`, and amend the commit so the flagged content is removed from the pushed history.

When auditing forbidden staged files, distinguish adding/modifying secrets from deleting stale secret-like files. Deleting a tracked `.envrc`/secret file from the backup may be allowed; adding or modifying it must remain blocked.

### 6) Verify the published repo

After push, verify at least one of:
- `git ls-remote` against the target repo
- GitHub API check for branch/ref existence
- local `git status` shows clean tracking against origin

For checkpoint backups that must support restore-before-core-update, also do a fresh shallow clone of the pushed restore ref and verify restore-critical files exist. At minimum check the active entrypoint/CLI, gateway dispatch files, newly added helper modules, targeted tests, policy file, and policy validator. Run the narrow test set that covers the captured live behavior when feasible, and report any wrapper fallback caveat.

Do not stop at "commit succeeded"; verify the remote really contains the snapshot.

## Backup freshness gate for core/update safety

When the backup repo is used as a safety baseline before a Hermes Agent / Hermes OS core update, do a read-only freshness check before allowing update work to continue.

Recommended checks:
- `git ls-remote --heads <repo-url>` proves the backup repo and branch exist.
- shallow clone the backup repo into a temp directory.
- read `restore/MANIFEST.json` and confirm restore docs exist.
- verify current protected files exist in the snapshot, especially entrypoint, gateway, Hermes OS status/policy, and validator files.
- compare backup protected-file hashes against current dev checkout and live runtime where applicable.
- classify stale snapshots as blocking for core updates until refreshed and re-verified.

For Hermes-os, treat these files as mandatory when they exist locally because missing them can make rollback restore an outdated policy/status contract:

```text
sources/hermes-agent/hermes_cli/hermes_os_format.py
sources/hermes-agent/website/docs/reference/merged-hard-gate-policy.yaml
sources/hermes-agent/website/docs/reference/merged-hard-gate-policy.schema.json
sources/hermes-agent/tools/merged_policy_validator.py
```

If a verified backup snapshot is stale, update `restore/MANIFEST.json` and `restore/BOOTSTRAP.md` with the new policy/status/validator scope before pushing. After push, verify again with `git ls-remote` and a fresh shallow clone; do not claim the backup is current from a local commit alone.

## Practical patterns learned

- A backup repo is safer when it is intentionally narrow rather than a full filesystem dump.
- `Repo.env.example` is a good replacement for the real config file.
- A restore repo should be designed for download-and-rebuild, not just archival browsing.
- GitHub verification is worth doing even after a successful push.
- A temporary authenticated remote is useful for push operations, but the final repo should not expose credentials.
- `git ls-remote` is a simple, reliable post-push proof that the target branch exists remotely.
- A restore snapshot can be valid but stale; for core updates, backup freshness must be checked against current protected files before using it as a rollback baseline.
- Local bundles are a temporary safety net, not the permanent restore source. A verified Git checkpoint replaces them as canonical truth.

## Pitfalls

- Including too many unrelated skills or helper files makes restore harder, not easier.
- Committing `Repo.env`, logs, or caches can leak secrets or create noisy history.
- A malformed authenticated remote can look valid until push time.
- A repo can be pushed successfully while still missing restore instructions; include them early.
- A repo may be reachable for read access (`git ls-remote`) but still lack write auth; check both before assuming push will work.
- A remote branch may exist with unrelated history; if the local snapshot is meant to become a backup branch, choose a new branch or a deliberate update strategy instead of assuming `main` is safe to overwrite.
- Git may block the commit if `user.name` / `user.email` is unset; set identity repo-locally unless a global identity change is explicitly desired.
- `git diff --cached --check` can reveal whitespace errors in staged files; fix and restage before committing the backup snapshot.
- RTK/Hermes output redaction can obscure whether a token was present; verify auth through behavior and safe labels, never by printing secrets.
- If push fails for missing GitHub credentials, a local commit alone is not a remote backup; create and verify a git bundle fallback before stopping.
- Do not assume the backup is complete unless the scope was intentionally documented.

## Done criteria

A Hermes-os GitHub backup snapshot is complete when:

- the repo is a single cohesive backup target
- only Hermes-related and restore-required material is included
- secrets and runtime noise are excluded
- `Repo.env.example` and restore docs are present
- the snapshot is committed and pushed successfully
- remote verification confirms the branch exists on GitHub
- for core-update checkpoints, a fresh clone of the canonical restore ref contains the restore-critical files and the relevant smoke/targeted tests pass or a caveat is explicitly reported
- if a moving branch could not be updated safely, the final report names the immutable checkpoint branch as the restore source of truth
- temporary `~/hermes-agent-backups` bundles are deleted after verified push/clone, or retention is limited to one newest emergency bundle with a written reason

## Minimal report format

```text
Repo: <target>
Scope: <included sources>
Excluded: <secrets/logs/cache/build/runtime>
Push: success
Remote verification: success
Restore docs: present
```
