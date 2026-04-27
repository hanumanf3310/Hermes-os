# Chapter 11 — Built-in tools

thClaws ships with around twenty built-in tools. The agent picks them
autonomously; you see each call as a `[tool: Name: …]` line, then a
✓ (success) or ✗ (error). This chapter is the reference.

## File tools

| Tool | Approval | Summary |
|---|---|---|
| `Ls` | auto | Non-recursive directory listing |
| `Read` | auto | Read a file (whole or line-range slice) |
| `Glob` | auto | Shell-glob pattern matching; respects `.gitignore` |
| `Grep` | auto | Regex search across files; respects `.gitignore` |
| `Write` | prompt | Create or overwrite a file |
| `Edit` | prompt | Exact string replacement (fails if non-unique) |

All of them are scoped to the sandbox ([Chapter 5](ch05-permissions.md)).
For large files the agent is trained to use `Glob` + `Grep` first to
narrow down, then `Read` with a line range, rather than slurping the
whole file — but there is no hard size cap enforced by the tool, so
`Read` on a multi-gigabyte file will try to load it. If you need a
binding upper bound, run in `ask` mode and deny the call.

## Shell

| Tool | Approval | Summary |
|---|---|---|
| `Bash` | prompt | Run a shell command via `/bin/sh -c` |

Defaults:

- 2-minute timeout (override with `timeout_ms` up to 10 min).
- Output over 50 KB truncated; full text saved to `/tmp/thclaws-tool-output/<id>.txt`.
- Destructive patterns (`rm -rf`, `sudo`, `curl | sh`, `dd`, `mkfs`,
  `> /dev/sda`) flagged with `⚠` before the approval prompt.
- Long-running servers: the agent is trained to either run them in
  the background (`... &`) or wrap them in `timeout 10` so the turn
  can't hang.
- Python `venv` auto-activated if `./.venv/bin/activate` exists (the
  tool sources the `activate` script before running).

## Web

| Tool | Approval | Summary |
|---|---|---|
| `WebFetch` | prompt | HTTP GET (100 KB body cap) with Markdown conversion |
| `WebSearch` | prompt | Web search via Tavily / Brave / DuckDuckGo |

Search provider is picked via `TAVILY_API_KEY` or `BRAVE_SEARCH_API_KEY`
if set, else DuckDuckGo (no key, lower quality). Override with
`searchEngine: "tavily"` in settings.

## User interaction

| Tool | Approval | Summary |
|---|---|---|
| `AskUserQuestion` | auto | Pause the turn and ask you a typed question |
| `EnterPlanMode` | auto | Switch to planning mode (no mutations until ExitPlanMode) |
| `ExitPlanMode` | auto | Resume normal execution |

## Task tracking

| Tool | Approval | Summary |
|---|---|---|
| `TaskCreate` | auto | Add a task / todo |
| `TaskUpdate` | auto | Change status (pending / in_progress / completed / deleted) |
| `TaskGet` | auto | Look up a task by id |
| `TaskList` | auto | Show current tasks |
| `TodoWrite` | auto | Replace the whole todo list in one call (Claude Code–style) |

`TaskCreate`/`Update`/`Get`/`List` are the granular, per-item interface;
`TodoWrite` rewrites the whole list at once and is what the agent
reaches for during long planning turns. See them mid-turn with
`/tasks`.

## Spawning agents

| Tool | Approval | Summary |
|---|---|---|
| `Task` | prompt | Spawn a sub-agent for an isolated sub-problem |

Sub-agents get their own tool registry and can recurse up to depth 3.
Details in [Chapter 15](ch15-subagents.md).

## Knowledge base (KMS)

| Tool | Approval | Summary |
|---|---|---|
| `KmsRead` | auto | Read a single page from an attached knowledge base |
| `KmsSearch` | auto | Grep across all pages in one knowledge base |

These are **only registered when at least one KMS is attached** to the
current project (via `/kms use NAME` or the sidebar checkbox). The agent
sees each active KMS's `index.md` in the system prompt and calls these
tools to pull in specific pages on demand.

```
[tool: KmsSearch(kms: "notes", pattern: "bearer")]
```

Returns `page:line:text` lines. Full concept + workflow in
[Chapter 9](ch09-knowledge-bases-kms.md).

## MCP tools

Every MCP server's tools are discovered at startup and registered with
names qualified by server: `weather__get_forecast`,
`github__list_issues`, etc. All prompt for approval. Details in
[Chapter 14](ch14-mcp.md).

## Reading the tool stream

A normal turn looks like:

```
❯ check if there's a README and show me its first section

[tool: Glob: README*] ✓
[tool: Read: README.md] ✓
The README's first section is "Install" — it walks through…
[tokens: 2100in/145out · 1.8s]
```

- `[tool: Name: detail]` — tool being called with an abbreviated
  argument preview (first path, command, URL, etc.).
- Trailing `✓` — tool succeeded.
- Trailing `✗ <error>` — tool failed; the model gets the error back
  and may retry with a different approach.

## Tool output truncation

Shell commands and file reads that produce more than 50 KB of output
have the body truncated in the model's view. A small preview is kept
for the model; the full content is saved to
`/tmp/thclaws-tool-output/<tool-id>.txt` so you can inspect it. The
model is told about the truncation and the preview is usually enough
to proceed.

## Limiting which tools run

Three mechanisms:

1. **`allowedTools` / `disallowedTools`** in settings — removes tools
   from the registry so the model never sees them. Useful for
   "read-only review" workflows.
2. **Agent defs** ([Chapter 15](ch15-subagents.md)) — per-agent tool scopes override the
   global registry.
3. **Permissions** ([Chapter 5](ch05-permissions.md)) — tools stay in the registry but prompt
   you before running; `n` denies the call.

## Hooks on tool events

Shell commands can fire on `pre_tool_use` / `post_tool_use` /
`post_tool_use_failure` / `permission_denied` — see [Chapter 13](ch13-hooks.md).
