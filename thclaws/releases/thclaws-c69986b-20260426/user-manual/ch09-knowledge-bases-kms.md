# Chapter 9 — Knowledge bases (KMS)

A **knowledge base** (KMS — Knowledge Management System) is a folder of markdown pages you curate, plus an `index.md` table of contents the agent reads on every turn. Inspired by Andrej Karpathy's [LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), thClaws ships with KMS built in — no embeddings, no vector store, just grep + read.

Use cases:

- **Personal notes** — everything you've learned about an API, a library, a client's codebase
- **Project reference** — architectural decisions, design principles, common patterns for a specific repo
- **Team playbook** — standard operating procedures, onboarding checklists
- **Language-specific** — Thai-aware content (the default works out of the box for Thai thanks to the Grep-based retrieval)

## How it's different from memory or AGENTS.md

| | Scope | Size | Retrieval |
|---|---|---|---|
| **AGENTS.md** | Full text injected every turn | Small (<few KB) | No retrieval — always in prompt |
| **Memory** | Individual facts by type | Small (index + body refs) | Frontmatter indexed, body pulled on need |
| **KMS** | Entire wiki, lazy-loaded | Unbounded (thousands of pages fine) | Grep search + targeted page reads |

Rule of thumb: memory is for things about *you* and *how you work*. AGENTS.md is for project conventions. KMS is for *content* the agent looks things up in.

## Scopes

Two scopes, identical internal structure:

- **User** — `~/.config/thclaws/kms/<name>/` — available in every project
- **Project** — `.thclaws/kms/<name>/` — lives with the repo, follows it into git if tracked

When the same name exists in both scopes, the **project** version wins.

## Layout of a KMS directory

```
<kms_root>/
├── index.md      ← table of contents, one line per page. The agent reads this every turn.
├── log.md        ← append-only change log (humans + agent write here)
├── SCHEMA.md     ← optional: shape rules for pages
├── pages/        ← individual wiki pages, one per topic
│   ├── auth-flow.md
│   ├── api-conventions.md
│   └── troubleshooting.md
└── sources/      ← raw source material (URLs, PDFs, notes) — optional
```

`/kms new` seeds all of the above with minimal starter content so you can start writing immediately.

## Multi-KMS: attach any subset to a chat

A project's active KMS list lives in `.thclaws/settings.json`:

```json
{
  "kms": {
    "active": ["notes", "client-api", "team-playbook"]
  }
}
```

Every active KMS's `index.md` is concatenated into the system prompt under a `## KMS: <name>` heading, each with a pointer to the `KmsRead` / `KmsSearch` tools. The agent sees:

```
# Active knowledge bases

The following KMS are attached to this conversation. Their indices are below —
consult them before answering when the user's question overlaps.

## KMS: notes (user)

# notes
- [auth-flow](pages/auth-flow.md) — JWT refresh pattern we use
- [api-conventions](pages/api-conventions.md) — REST style guide

To read a specific page, call `KmsRead(kms: "notes", page: "<page>")`.
To grep all pages, call `KmsSearch(kms: "notes", pattern: "...")`.
```

And `KmsRead` / `KmsSearch` are registered in the tool list.

## Slash commands

### `/kms` (or `/kms list`)

List every discoverable KMS; `*` marks ones attached to the current project.

```
❯ /kms
* notes              (user)
  client-api         (project)
* team-playbook      (user)
  archived-docs      (user)
(* = attached to this project; toggle with /kms use | /kms off)
```

### `/kms new [--project] NAME`

Create a new KMS and seed starter files.

```
❯ /kms new meeting-notes
created KMS 'meeting-notes' (user) → /Users/you/.config/thclaws/kms/meeting-notes

❯ /kms new --project design-decisions
created KMS 'design-decisions' (project) → ./.thclaws/kms/design-decisions
```

- Default scope is **user** (available in every project)
- `--project` puts it in `.thclaws/kms/` (lives with the repo)

### `/kms use NAME`

Attach a KMS to the current project. The `KmsRead` / `KmsSearch` tools
are registered into the current session immediately and the
`index.md` is spliced into the system prompt — no restart, works in
the CLI REPL and either GUI tab.

```
❯ /kms use notes
KMS 'notes' attached (tools registered; available this turn)
```

### `/kms off NAME`

Detach a KMS. Also live — when the last KMS detaches, the `KmsRead` /
`KmsSearch` tools are dropped from the registry so the model stops
seeing them as options.

```
❯ /kms off archived-docs
KMS 'archived-docs' detached (system prompt updated)
```

### `/kms show NAME`

Print the KMS's `index.md` to inspect what's there.

```
❯ /kms show notes
# notes
- [auth-flow](pages/auth-flow.md) — JWT refresh pattern we use
- [api-conventions](pages/api-conventions.md) — REST style guide
...
```

## Sidebar (GUI)

The sidebar's **Knowledge** section lists every discoverable KMS with a checkbox per entry. Tick to attach, untick to detach — the same underlying toggle as `/kms use` / `/kms off`.

The `+` button prompts for a name, then asks for scope (OK = user, Cancel = project). A new KMS is created with starter files ready to edit.

## Tools the agent calls

### `KmsRead(kms: "name", page: "slug")`

Reads `<kms_root>/pages/<slug>.md`. The `.md` extension is added if missing. Path traversal is rejected (`..`, absolute paths, anything outside `pages/`).

The agent calls this after spotting a relevant entry in `index.md`:

```
[assistant] I'll check the auth-flow page first…
[tool: KmsRead(kms: "notes", page: "auth-flow")]
[result] (page content)
```

### `KmsSearch(kms: "name", pattern: "regex")`

Grep-style scan across `<kms_root>/pages/*.md`. Returns matching lines as `page:line:text`, one per line.

```
[assistant] Let me search for "bearer" across my notes…
[tool: KmsSearch(kms: "notes", pattern: "bearer")]
[result]
auth-flow:12:Bearer tokens expire after 15 minutes
api-conventions:34:Always include "Authorization: Bearer <token>"
```

## Writing pages: the ingest workflow

You don't need a special tool to add content — the agent writes markdown like it writes any other file. A typical ingest turn looks like:

```
❯ I just read https://example.com/oauth-guide. Ingest the key points into 'notes'.

[assistant] Reading the page…
[tool: WebFetch(url: "https://example.com/oauth-guide")]
[tool: Write(path: "~/.config/thclaws/kms/notes/pages/oauth-client-credentials.md", ...)]
[tool: Edit(path: "~/.config/thclaws/kms/notes/index.md", ...)]
[tool: Edit(path: "~/.config/thclaws/kms/notes/log.md", ...)]
Wrote pages/oauth-client-credentials.md, added entry to index.md, appended to log.md.
```

Karpathy's gist describes the workflow as three operations:

1. **Ingest** — read a source, extract distinct facts, write a page, update the index, append to the log
2. **Query** — answer a question from the wiki (the agent does this naturally when the KMS is attached)
3. **Lint** — periodically read all pages and suggest merges, splits, or orphans to fix

You run these via natural language; no special slash commands needed.

## Scaling limits and future direction

v0.2.x is intentionally embedding-free:

- Grep is fast enough up to a few hundred pages
- The `index.md`-first pattern means the agent can usually find relevant pages without searching
- Pages are markdown and human-readable — you can browse them without any tooling

When a KMS grows past ~200 pages or includes non-English content that grep won't cross-match cleanly, you can upgrade to hybrid RAG (hosted OpenAI embeddings) — planned for a future release. The client API stays the same.

## Thai-language notes

Grep over Thai works out of the box because the retrieval is substring-based, not tokenized. Your agent can search `"การยืนยันตัวตน"` across Thai notes and get results without any setup.

For mixed Thai/English technical content, stick with English tech terms and Thai prose in the same page — both will hit on relevant searches.

## Troubleshooting

- **KMS not visible in sidebar** — make sure the folder has a valid `index.md` (create one manually if you've built the KMS by hand) and that it lives in `~/.config/thclaws/kms/` or `.thclaws/kms/`.
- **Changes not reflected in agent responses** — the `index.md` is read on turn start; a running turn uses the snapshot taken before it began. Start a new turn.
- **"no KMS named 'X'"** error from a tool call — the name is case-sensitive and must match the directory name exactly. Check with `/kms list`.
- **Stale active list** — `.thclaws/settings.json` is the source of truth. Edit by hand if the sidebar checkboxes ever disagree with reality.

## Where to go next

- [Chapter 8](ch08-memory-and-agents-md.md) — memory and project instructions (the other two context mechanisms)
- [Chapter 10](ch10-slash-commands.md) — slash command reference including `/kms` family
- [Chapter 11](ch11-built-in-tools.md) — tool reference including `KmsRead` and `KmsSearch`
