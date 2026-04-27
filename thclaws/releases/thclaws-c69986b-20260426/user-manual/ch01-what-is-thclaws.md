# Chapter 1 — What is thClaws?

![logo](../user-manual-img/logo/thClaws-logo-line-art-banner.png)

thClaws is a **native-Rust AI agent workspace** that runs locally on
your machine. Not just coding — it edits code, automates workflows,
searches your knowledge bases, and coordinates teams of agents, all in
one binary. You tell it what you want in natural language; it reads
your files, runs commands, uses tools, and talks back to you while it
works.

Three interfaces ship as one binary:

- **Desktop GUI** (`thclaws` with no flags) — a native window with a
  Terminal tab running the same interactive REPL as `--cli` mode, a
  streaming Chat tab, a Files browser, and an optional Team tab.
- **CLI REPL** (`thclaws --cli`) — an interactive terminal prompt for
  SSH sessions, headless servers, or when you want zero GUI overhead.
- **Non-interactive mode** (`thclaws -p "prompt"`, long form `--print`)
  — runs a single turn and exits. Handy for scripts, CI pipelines, and
  shell one-liners.

## What makes it different

- **Multi-provider.** Anthropic, OpenAI, Gemini, Alibaba DashScope, OpenRouter, Ollama (local
  and Anthropic-compatible), and Agentic Press, 
  auto-detected by model name prefix. Switch models mid-session with
  `/model` (validated against the provider's catalogue) or swap the
  whole provider with `/provider`.
- **Any knowledge worker, not just engineers.** The Chat tab is a
  streaming conversation panel anyone can drive — researchers,
  analysts, PMs, ops, legal, marketing, finance. Ask in natural
  language; the agent reads your files, edits documents, searches
  your knowledge base, drafts outputs. Engineers prefer the Terminal
  tab's REPL. Both share the same sessions and config, so a mixed
  team can switch between interfaces freely without losing context.
- **File viewer & editor in the Files tab.** A working-directory file
  tree with a syntax-highlighted preview pane (CodeMirror 6, ~40
  languages) and server-rendered GFM markdown in a sandboxed iframe.
  Click the pencil icon to edit `.md` in a WYSIWYG editor (TipTap) or
  code in a highlighted editor (CodeMirror) — Cmd/Ctrl+S to save,
  native OS confirm dialog before discarding edits. Auto-refresh
  polling pauses while you're editing so concurrent `Write`/`Edit`
  tool calls from the agent can't clobber your in-progress buffer.
- **Open standards, not a walled garden.** thClaws is built on the
  conventions the agent-tooling industry is converging on, not on
  bespoke formats you have to learn only for us. The
  [Model Context Protocol](https://modelcontextprotocol.io/) for
  tool servers. [`AGENTS.md`](https://agents.md) for project
  instructions — the vendor-neutral standard stewarded by the Agentic
  AI Foundation and adopted by Google, OpenAI, Factory, Sourcegraph,
  and Cursor. `SKILL.md` with YAML frontmatter for packaged workflows.
  `.mcp.json` for MCP server configuration. Your configuration is
  portable — between thClaws, other agents that speak the same
  standards, and whatever comes next.
- **Skills.** Reusable expert workflows packaged as a directory with
  `SKILL.md` (YAML frontmatter + Markdown instructions the model
  follows) and optional scripts. The agent picks the right skill
  automatically when a user request matches the `whenToUse` trigger,
  or you can invoke one explicitly as `/<skill-name>`. Install with
  `/skill install` from a git URL or `.zip` archive. Discovery looks
  in `.thclaws/skills/`, `~/.config/thclaws/skills/`, plus
  `.claude/skills/` as a fallback location.
- **MCP servers.** The Model Context Protocol lets you plug in tools
  built by third parties — GitHub, filesystems, databases, browsers,
  Slack, and more. Both stdio (spawned subprocess) and HTTP Streamable
  transports are supported, with OAuth 2.1 + PKCE for protected
  servers. Add one with `/mcp add` or ship a `.mcp.json` in your
  project; discovered tools are namespaced by server name and the
  agent can call them like any built-in.
- **Plugin system.** Skills + commands + agent definitions + MCP
  servers bundled under a single manifest (`.thclaws-plugin/plugin.json`
  or `.claude-plugin/plugin.json`), installable from a git URL or a
  `.zip` archive. One install, one uninstall, one version to pin —
  ideal for sharing a team's extensions.
- **Memory & project instructions.** Drop an `AGENTS.md` (or
  `CLAUDE.md`) in your repo — thClaws walks up from cwd and injects
  every match into the system prompt, the same way git resolves
  `.gitignore`. A
  separate persistent memory store at `~/.config/thclaws/memory/`
  holds longer-lived facts the agent has learned about you, your
  preferences, and each project, classified as `user` / `feedback` /
  `project` / `reference` and indexed as markdown files you can read,
  edit, or commit. Both survive restart.
- **Knowledge bases (KMS).** Per-project and per-user wikis the agent
  can search and read on demand. Drop markdown pages under
  `.thclaws/kms/<name>/pages/`, give each a one-line entry in
  `index.md`, tick the box in the sidebar, and the agent gets a
  table of contents every turn plus `KmsRead` / `KmsSearch` tools to
  pull in specific pages. No embeddings — grep + read, following
  Andrej Karpathy's LLM-wiki pattern.
- **Agent orchestration.** Two levels. For narrow subtasks, delegate
  to an isolated sub-agent via the `Task` tool — each gets its own
  tool registry and can recurse up to 3 levels deep. For real
  parallelism, spin up an **Agent Team**: multiple thClaws processes
  coordinating through a shared mailbox and task queue, each
  teammate in its own tmux pane and optional git worktree so
  backend + frontend work doesn't collide. The lead calls
  `TeamMerge` when everyone's done.
- **Settings.** Every runtime knob — permission mode, thinking budget,
  allowed/disallowed tools, provider endpoints, KMS attachments — is
  one JSON file: `.thclaws/settings.json` (project, commit it with
  the repo) or `~/.config/thclaws/settings.json` (user-global).
  `~/.claude/settings.json` is read as a fallback location. API
  keys go in the OS keychain by default (Windows Credential Manager
  / macOS Keychain / Linux Secret Service) with `.env` fallback for
  CI and headless servers. The gear icon in the desktop GUI is a
  visual editor for keys, global/folder `AGENTS.md`, and the secrets
  backend choice.
- **Safety first.** A filesystem sandbox scopes file tools to the
  working directory. Destructive shell commands are flagged before
  execution. You approve every mutating tool call unless you've opted
  into auto-approve.
- **Offline-capable.** Ollama (native and Anthropic-compat) lets you run
  entirely against a local model.
- **Deploy what you build.** thClaws doesn't stop at authoring —
  ship the landing pages, web apps, APIs, and AI agents you create
  through [Agentic Press Hosting](https://agentic-press.com)
  (partnered with SIS Cloud Service and Artech.Cloud) or any other
  host you prefer. Schedule agents on cron, respond to webhooks,
  stream from public URLs. The deploy flow ships as a plugin
  (`/plugin install …-deploy`) so hosts are swappable — the client
  never locks you in.
- **Shell escape.** Prefix any REPL line with `!` to run the rest as a
  shell command directly in your terminal — no tokens, no approval
  prompt, no agent round-trip (e.g. `! git status`).

## What you need

- A supported OS: macOS (arm64 or x86_64), Linux (arm64 or x86_64), or
  Windows (arm64 or x86_64).
- At least one LLM API key — Anthropic, OpenAI, Gemini, Agentic Press,
  OpenRouter, or DashScope. (Or a local Ollama install if you'd rather
  stay offline.)

[Chapter 2](ch02-installation.md) walks through installation and first
launch. [Chapter 6](ch06-providers-models-api-keys.md) covers where
and how to paste keys.

## How this manual is organised

**Part I** (chapters 2–14) is reference material: how to install it,
and then every user-facing feature explained once with the commands
and configuration you need.

**Part II** (chapters 15–21) is walkthroughs: real projects from
scratch — a static landing page, a reservation site, a news agent —
ending in deployments to Agentic Press Hosting. Each is independent.

If you're new, read chapter 2 next. If you're migrating from Claude
Code, skip to chapters 6, 7, 11, and 13.
