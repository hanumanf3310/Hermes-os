# Chapter 15 — Subagents

The `Task` tool lets the main agent **delegate** to a sub-agent: a
fresh, isolated copy of the agent with its own tool scope and its own
goal. Useful for branching work (explore multiple approaches in
parallel), protecting the main context (run a noisy exploration in a
child), or specialisation (hand off to a "reviewer" agent with
read-only tools).

Subagents are part of the same process — they run in-memory, not as
separate OS processes. For true parallelism across processes, see
Agent Teams in Chapter 17.

## How it looks

```
❯ are the REST endpoints in this repo consistent with our naming
  convention in AGENTS.md?

[tool: Task: (agent=reviewer, prompt=Check every route under src/api …)] …
  [child:reviewer] Using Glob to find route files…
  [child:reviewer] Found 14 routes; 3 don't match the convention
[tool: Task] ✓

Looking at the sub-agent's findings:
- `src/api/v1/getUsers.ts` should be `get_users.ts` per convention.
- `src/api/v1/FetchOrders.ts` should be `fetch_orders.ts`.
- `src/api/v2/createPost.ts` should be `create_post.ts`.
```

The parent sees only the sub-agent's final text response, keeping the
intermediate tool chatter out of the main context.

## Agent definitions

Specific sub-agent behaviours are configured in
`.thclaws/agents/*.md` (project) or `~/.config/thclaws/agents/*.md`
(user):

```markdown
---
name: reviewer
description: Read-only code review with focus on conventions
model: claude-haiku-4-5
tools: Read, Glob, Grep, Ls
permissionMode: auto
maxTurns: 20
color: cyan
---

You are a code reviewer. Look at the code the parent points you at.
Flag:
- Naming inconsistencies with the project's `AGENTS.md` conventions.
- Missing tests alongside new code.
- Security-sensitive patterns (raw SQL, unsanitised input).

Return a concise bullet list. Don't propose fixes unless asked.
```

Frontmatter fields:

| Field | Purpose |
|---|---|
| `name` | Unique id (defaults to filename stem) |
| `description` | When-to-use text the parent sees |
| `model` | Model override for this agent |
| `tools` | Comma-separated tool allowlist |
| `disallowedTools` | Tool denylist |
| `permissionMode` | `auto` or `ask` (useful for "read-only" agents) |
| `maxTurns` | Max iterations (default 200) |
| `color` | Terminal colour for child output |
| `isolation` | `worktree` — give this agent its own git worktree (teams only) |

## Invoking

The parent agent invokes via `Task`:

```
Task(agent: "reviewer", prompt: "Check src/api for naming violations")
```

Typically you don't call this directly — you ask the parent a
question in English and it decides. The model sees the list of
available agents in its system prompt (rendered from the agent defs).

## Recursion

A sub-agent can spawn further sub-agents up to `max_depth = 3` by
default. Each level is more scoped:

```
parent (depth 0)
 ├─ reviewer (depth 1) — "look at auth routes"
 │   └─ specialist (depth 2) — "audit JWT signing"
 └─ tester (depth 1) — "write integration tests"
```

The Task tool at depth 3 disables recursion to prevent runaway chains.

## Load order

`~/.config/thclaws/agents.json` → `~/.claude/agents/*.md` →
`~/.config/thclaws/agents/*.md` → `.thclaws/agents/*.md`. Later wins
by name.

### Plugin-contributed agents

Plugins (Chapter 16) can ship agent defs via an `agents` entry in
their manifest. Those dirs are walked **after** the standard ones and
merged **additively** — a plugin agent cannot override a user's or
project's existing agent with the same name. That means:

- You can install a plugin that ships a `reviewer` + `tester` +
  `architect` and all three become available via `Task(agent: "…")`
  and team spawns.
- If you later add your own `.thclaws/agents/reviewer.md`, it wins —
  the plugin's is ignored until you remove yours.
- `/plugin show <name>` lists the `agent dirs` the plugin contributes.

## Subagents vs Teams

| | Subagents | Teams |
|---|---|---|
| **Process model** | In-process, one agent at a time | Multiple `thclaws --team-agent` processes, tmux-orchestrated |
| **Parallelism** | Serial (recursion depth, not concurrency) | Truly concurrent |
| **Isolation** | Shared sandbox | Optional git worktree per teammate |
| **Messaging** | None — child returns a string | Filesystem mailbox + task queue |
| **Overhead** | Negligible | High — spins up 1+ extra processes |
| **Use for** | Focus a sub-problem, reduce context | Parallel streams of work with coordination |

Rule of thumb: start with subagents. Reach for teams when the work
genuinely fans out (e.g. "build the backend while I build the
frontend").
