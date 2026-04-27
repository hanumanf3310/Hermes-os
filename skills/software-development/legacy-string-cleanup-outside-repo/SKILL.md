---
name: legacy-string-cleanup-outside-repo
description: Evidence-based workflow for removing legacy command/model strings from active repo files and nearby helper scripts while distinguishing runtime contract from historical logs/artifacts.
---

# Legacy String Cleanup Outside Repo

Use this skill when a user asks to remove an old command, backend name, model string, or other legacy token from files *outside* the main repo, especially when some matches may live in logs, session dumps, reference files, or helper scripts.

## When to use
- A legacy string still appears in helper scripts, policy files, PowerShell, or reference docs outside the primary repo.
- The user wants active guidance cleaned up, but historical logs should remain untouched.
- You hit a permission issue while editing a file outside the repo.
- You need to prove the cleanup with searches and syntax checks.

## Workflow
1. **Separate active files from artifacts**
   - Search the repo first.
   - Then search adjacent helper/script/doc paths.
   - Treat session logs, cache files, and historical traces as artifacts unless the user explicitly asks to rewrite history.

2. **Use targeted searches**
   - Search only the relevant trees first.
   - Re-run narrower searches after each edit.
   - Do not claim the whole home directory is clean if logs still contain historical matches.

3. **Patch active guidance, not logs**
   - Update helper scripts, policy wrappers, docs, and reference files that users may actually run or read.
   - Leave session logs and archived traces alone unless asked.

4. **Re-read full files before editing fragile formats**
   - Especially PowerShell, generated helper scripts, and files that can be partially overwritten.
   - If a file is long or has multiple sections, inspect it fully before patching.

5. **If patch fails due to permissions**
   - Fall back to `execute_code` with `hermes_tools.write_file()` for the specific file.
   - Re-run verification immediately after the write.

6. **Verify the result**
   - Search again for the legacy string in the active paths.
   - Run syntax/compile checks for files you touched.
   - Report remaining matches separately if they are only in logs or artifacts.

## Pitfalls
- Historical logs can still contain the legacy string after a successful cleanup; that does not mean runtime guidance is still stale.
- Partial file views can miss sections and cause accidental overwrite.
- A string may need to be replaced in comments/docs even after code changes, or readers will still see the old behavior.

## Good final reporting
- Say which active files changed.
- Say which checks passed.
- Separate active runtime cleanup from historical/log-only remnants.
- Avoid overclaiming that the entire home directory is clean unless you verified every relevant artifact tree.