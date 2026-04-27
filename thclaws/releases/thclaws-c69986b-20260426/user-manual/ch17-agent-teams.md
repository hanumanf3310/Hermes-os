# Chapter 17 — Agent Teams

Agent Teams let you run **multiple thClaws agents in parallel**,
coordinating through a filesystem-based mailbox and task queue. Useful
when work genuinely fans out: backend + frontend at the same time,
one agent writing tests while another implements, etc.

Teams are **opt-in** — they spin up extra processes and burn tokens
fast.

**From the GUI.** Click the gear icon → the *Workspace* section has
an *Agent Teams* row with an on/off pill. Click to toggle. The change
writes `teamEnabled: true` to `.thclaws/settings.json` and you'll see
a yellow "Restart the app for this to take effect" notice — team
tools are registered at session spawn, so the running shared session
needs a respawn to pick them up.

**From the CLI or by hand:**

```json
// .thclaws/settings.json
{ "teamEnabled": true }
```

With `teamEnabled: false` (the default), no team tools are registered
and no inbox poller runs. The Team tab in the GUI stays visible either
way — it shows an empty-state pointer ("No team agents running — ask
the agent to create a team") so you can always see when a team starts
up. Sub-agents (Chapter 15) are unaffected by this flag.

> ⚠ **Provider constraint: `agent/*` models cannot use thClaws teams.**
> The `agent/*` provider ([Chapter 6](ch06-providers-models-api-keys.md))
> shells out to your local `claude` CLI as a subprocess. That subprocess
> uses Claude Code's own built-in toolset (`Agent`, `Bash`, `Edit`,
> `Read`, `ScheduleWakeup`, `Skill`, `ToolSearch`, `Write`) and does
> not see thClaws's tool registry — so even with `teamEnabled: true`,
> our `TeamCreate` / `SpawnTeammate` / etc. are unreachable from the
> model. To use thClaws teams, switch to any non-`agent/*` provider
> (`claude-sonnet-4-6`, `claude-opus-4-7`, `gpt-4o`, …) via
> `/model` or `/provider`. The system prompt grounds the model to
> tell you this explicitly if you ask for a team while on `agent/*` —
> rather than silently calling Claude Code's separate built-in
> TeamCreate that writes to `~/.claude/teams/` (invisible to thClaws).

With `agent/*` and `teamEnabled: false`, the same grounding tells the
model to NOT fall back to Claude Code's `TeamCreate` / `Agent` /
`TodoWrite` / `AskUserQuestion` / `ToolSearch` built-ins — otherwise
the model would happily fabricate a "team created" response with
nothing actually written to `.thclaws/team/`. See dev-log 078 for
the audit that motivated this.

## Anatomy

```
.thclaws/team/
├── config.json                  team config (members, lead)
├── inboxes/{agent}.json         per-agent inbox (JSON array)
├── tasks/{id}.json              task queue entries
├── tasks/_hwm                   high-water mark for task IDs
└── agents/{agent}/status.json   heartbeat + current task
```

Everything is a file — no DB, no broker. `fs2` advisory locking keeps
inbox writes atomic across processes.

## Team tools

All added to the agent's registry when `teamEnabled: true`:

| Tool | Purpose |
|---|---|
| `TeamCreate` | Create a team with named agents |
| `SpawnTeammate` | Launch a teammate process (tmux pane or background) |
| `SendMessage` | Write to a teammate's inbox |
| `CheckInbox` | Read unread messages, mark as read |
| `TeamStatus` | Agents + task queue summary |
| `TeamTaskCreate` | Add a task (with optional dependencies) |
| `TeamTaskList` | List tasks by status |
| `TeamTaskClaim` | Claim a pending unblocked task (teammate) |
| `TeamTaskComplete` | Mark done + notify lead |
| `TeamMerge` | Merge a teammate's worktree branch back into main |

## Spinning up a team

Typical lead prompt:

```
❯ Create a team with two members: "backend" (for the API) and
  "frontend" (for the React app). Use backend.md and frontend.md
  definitions under .thclaws/agents/. Spawn both now.
```

The lead calls `TeamCreate` then `SpawnTeammate` twice. Teammate
processes boot as `thclaws --team-agent backend` (and similar), each
with its own inbox and status file.

## Running style

Inside a tmux session, `SpawnTeammate` opens each teammate in a split
pane. Outside tmux, it launches a detached tmux session; attach with
`/team`:

```
❯ /team
(attaching to tmux session 'thclaws-team'…)
```

Each pane is a full teammate REPL. You can talk directly to one:

```
❯ (on lead) send to frontend: "the /users endpoint now returns a new
  `displayName` field — update the profile page"
```

That becomes a `SendMessage` into frontend's inbox. The frontend
teammate picks it up on its next poll (1s interval), works on it,
and reports back via `SendMessage` to the lead.

## Task queue

Instead of direct messaging, you can post tasks:

```
TeamTaskCreate(
  id: "t3",
  description: "Write integration tests for /orders endpoints",
  agent: "backend",
  depends_on: ["t1", "t2"]
)
```

Teammates auto-claim pending unblocked tasks when idle (no inbox
messages, no in-flight task). Dependencies: a task with `depends_on`
only becomes claimable once all dependencies are `completed`.

Workflow:

1. Lead posts `t1`, `t2`, `t3` (with `t3` depending on `t1`+`t2`).
2. `backend` and `frontend` each claim something claimable.
3. Done → `TeamTaskComplete` fires `idle_notification` to lead.
4. When `t1` + `t2` both complete, `t3` unblocks and whoever's idle
   picks it up.

## Worktree isolation

Agent defs can set `isolation: worktree`:

```markdown
---
name: backend
model: claude-sonnet-4-6
tools: Read, Write, Edit, Bash, Glob, Grep
isolation: worktree
---

You own the backend services. Work in your own git worktree so you
don't collide with the frontend teammate.
```

On spawn, thClaws creates `.thclaws/worktrees/backend` on branch
`team/backend` and runs the teammate there. Changes are isolated
until the lead calls `TeamMerge`:

```
TeamMerge(agent: "backend")
```

This runs `git merge team/backend` into the current branch, pushing
the teammate's work into the main line.

If the project dir isn't a git repo yet, thClaws auto-runs
`git init` + an initial empty commit so worktree creation works.

## Plan Approval (convention)

If your prompt to the lead mentions "Plan Approval", "with plan
approval", or similar wording, the system reads it as a
**lead↔teammate convention** — NOT a request to ask the human user:

1. Each teammate, before starting non-trivial work, sends a brief plan (1–3 lines: what they'll do, what they'll touch) to the lead via SendMessage.
2. Lead reviews and replies "approved, proceed" or "revise: …".
3. Teammate waits for the ack, then executes.

**The lead is the approver — never the user**, even when a human is watching. The mode only activates when the user prompt explicitly mentions it; otherwise teammates execute work directly so default behavior is preserved. Defined in `default_prompts/lead.md` and `default_prompts/agent_team.md`.

## Role guards (lead vs teammate)

To stop an LLM lead from accidentally wiping a teammate's files (e.g.
the actual `rm -rf tests/` we observed in a test run), BashTool /
Write / Edit have hard guards:

**Lead — refused regardless of `--accept-all`:**

| Command | Why blocked |
|---|---|
| `git reset --hard <ref>` | discards committed work |
| `git clean -f` / `-d` | deletes untracked files |
| `git push --force` / `git rebase` | rewrites shared history |
| `git worktree remove` / `prune` | kills teammate's process + worktree |
| `git checkout -- <path>` / `git restore --worktree` | discards teammate's uncommitted work |
| `git merge --abort` | tears down a merge instead of delegating |
| `rm -rf` / `-fr` / `-r` | destructive removal |
| `Write` / `Edit` (any path) | lead is a coordinator, not the author |

**Write/Edit exception:** when a git merge is in progress AND the target file currently contains `<<<<<<<` markers, the lead may write the resolved version. Once it commits the merge, `MERGE_HEAD` disappears and the block snaps back on automatically.

**Teammate — refused:**

| Command | Why blocked |
|---|---|
| `git reset --hard <branch-name>` (e.g. `main`, `origin/main`, `team/backend`) | resets your branch tip to a different branch — discards your own commits |

Still allowed (legitimate same-branch recovery): `HEAD~N`, `HEAD@{N}`, `HEAD^`, hex SHAs, `tags/...`.

When a guard fires, the tool returns an error explaining what's blocked and what to do instead (e.g. "delegate to a teammate via SendMessage" or "use HEAD~N rather than `main`"). Well-trained models redirect rather than retry.

### Editor stubs for teammates

SpawnTeammate sets `EDITOR=true VISUAL=true GIT_EDITOR=true GIT_SEQUENCE_EDITOR=true` on every teammate process.

So commands that would open an editor (`git commit -e`, `git commit` with no `-m`, `git rebase -i`) **don't hang** waiting for human input via `/dev/tty` — the `true` builtin exits 0 immediately, and git uses whatever message was already provided via `-F`/`-t` or commits empty per default. Prevents `vi` or `nano` from stalling the entire team mid-run.

## Protocol messages

Standard message types teammates and lead exchange:

| Type | From → To | Meaning |
|---|---|---|
| `idle_notification` | teammate → lead | "I just finished task X; what's next?" |
| `shutdown_request` | lead → teammate | "Stop and exit cleanly" |
| `user` | user → teammate | Free-form text (via `send to <agent>: …`) |

## Monitoring in the GUI

The Team tab shows one pane per teammate plus a `lead` pane mirroring
the main terminal. ANSI colours are translated to HTML: green for LLM
text, cyan for prompts and inbox messages, dim for tool starts and
token lines, yellow for errors or hit-max-iterations.

Status comes from each teammate's own `status.json` (`idle` /
`working` / `stopped`) — no false crash flagging based on missing
heartbeats.

## When not to use teams

Most tasks are fine with a single agent + sub-agents via `Task`
(Chapter 15). Reach for teams only when the parallelism is real and
the overhead pays for itself. A good litmus: if you could hand each
teammate's task to a different human contractor without coordination
headaches, it's a team shape.
