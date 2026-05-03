---
name: context7-skill-binding-manifest
description: Classify Hermes OS skills by how they should use Context7 MCP as external documentation evidence.
category: hermes-os
author: hanuman3310
version: 1.0.0
requires_tools:
  - mcp_context7_resolve_library_id
  - mcp_context7_query_docs
---

# Context7 Skill Binding Manifest

This manifest binds Context7 to Hermes OS skills by role. Context7 is a docs
evidence layer for current external library/API documentation. It is not a
memory system, policy source, runtime truth source, or replacement for local
repository evidence.

## Audit Snapshot

Current scan target: `~/.hermes/skills`

| Mode | Count | Meaning |
| --- | ---: | --- |
| direct | 4 | Skill already carries Context7 doctrine or should load it explicitly |
| conditional | 64 | Use Context7 only when external library/API docs affect the task |
| local-first | 50 | Prefer local files/runtime evidence; Context7 is secondary or rare |
| not-needed | 69 | No useful Context7 binding for normal operation |

## Binding Modes

### direct

Always keep Context7 doctrine available, but still apply local-truth precedence.

- `hermes-os`
- `hermes-os-integration`
- `context7-docs-evidence-nerve`
- `software-development/spike`

### conditional

Use Context7 when the work depends on a fast-moving external API, SDK,
framework, config key, middleware/auth/cache pattern, CLI behavior, or provider
wire format.

Core conditional skills:

- `hermes-workspace-launcher` for Vite/React/FastAPI/Uvicorn/ngrok/cloudflared
  docs, while ports/processes/URLs remain local truth.
- `codex-gpts-realtime-session-debugging` for Codex/OpenAI docs only when
  changing integration code; session JSONL and cache freshness remain local
  truth.
- `model-config-evidence-gate` for SDK/provider docs; model availability and
  picker truth must come from official/current sources plus live runtime
  catalogs.
- `openai-compatible-endpoint-smoke-testing` for OpenAI-compatible streaming,
  SSE, and provider contract docs; smoke tests remain decisive.
- `gemini-cli-hermes-fallback` for external CLI/SDK docs; fallback behavior is
  proven locally.
- `slash-command-workflow-integration` when command behavior depends on an
  external platform's command syntax or SDK.
- `systematic-debugging` when the root cause may be stale external API usage.
- `test-driven-development` when tests encode behavior from external docs.

Category-level conditional binding:

- `software-development`, `devops`, `github`, `mcp`, `mlops`, and
  `autonomous-ai-agents` skills may use Context7 when docs freshness matters.
- Creative/web skills may use Context7 for framework/library APIs such as p5.js,
  React, Tailwind, shadcn/ui, or build tooling.

### local-first

Use local evidence first and only call Context7 if the local task turns into an
external docs question.

- Hermes OS status, dashboard, memory graph, policy, fact store, Obsidian,
  session/cache, launcher-path, and runtime-process skills.
- Productivity/media/apple/gaming skills unless the task is explicitly about
  an SDK/API integration.

### not-needed

Do not add Context7 calls. These skills do not normally benefit from external
docs and would gain only latency/noise.

## Operating Rule

When a skill is conditional:

1. Read local files, runtime status, lockfiles, config, and tests first.
2. If an external library/API decision remains, resolve the library with
   `mcp_context7_resolve_library_id`.
3. Query only the narrow topic with `mcp_context7_query_docs`.
4. Apply Hermes OS policy, Fact Store, local evidence, and smoke tests above
   retrieved docs.
5. Record that Context7 was used when the final behavior depends on it.

## Forbidden Uses

- Do not use Context7 to decide whether a local service is running.
- Do not use Context7 to decide whether `/gpts`, `/hermes_workspace`, or
  `hermes-os` is registered in the live command table.
- Do not let Context7 override `merged-hard-gate-policy.yaml`.
- Do not let Context7 override local source, tests, lockfiles, session JSONL,
  dashboard validators, or runtime smoke tests.
