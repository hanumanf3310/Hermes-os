
## Git worktree
Your working directory is a **git worktree** on branch `team/{agent_name}` (created under `.worktrees/{agent_name}/`). Edits here land on your branch and are merged into the main branch later — they are **not visible** to other teammates until merges happen.

- Edit source/tests/code in your worktree freely — it's your branch.
- Shared docs, API specs, schemas, and anything other teammates depend on **before their own merge** belong at the project root (see *Workspace boundaries* above), never only in your worktree.
- When you produce a shared artifact at the project root, SendMessage the dependent teammates with its absolute path so they can open it immediately.
