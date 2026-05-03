---
name: context7-docs-evidence-nerve
description: Hermes OS doctrine for using Context7 MCP as an external docs evidence source without replacing local policy, RAG, or repository truth.
category: hermes-os
author: hanuman3310
version: 1.0.0
requires_tools:
  - mcp_context7_resolve_library_id
  - mcp_context7_query_docs
---

# Context7 Docs Evidence Nerve

Context7 is installed in Hermes Agent as `mcp_servers.context7`.

It is an evidence nerve for current external library/API documentation. It helps
Hermes OS avoid stale examples, removed APIs, old framework patterns, and
hallucinated methods when doing coding work.

## Role

- Use Context7 for fast-moving external docs: Next.js, React, Supabase,
  Tailwind, shadcn/ui, React Query, Cloudflare Workers, Prisma, Drizzle,
  Vercel, Netlify, and similar SDK/framework work.
- Use Context7 when Boss says `use context7`.
- Use Context7 when code generation depends on a library API, config key,
  middleware/auth/cache pattern, or version-specific behavior.
- Use the `context7-skill-binding-manifest` to decide whether a skill is
  direct, conditional, local-first, or not-needed for Context7.

## Binding Modes

- `direct`: Context7 doctrine is part of the skill's normal operating context.
- `conditional`: call Context7 only after local evidence shows an external docs
  question remains.
- `local-first`: local files/runtime evidence are the answer unless the task
  becomes an external docs question.
- `not-needed`: do not call Context7 for normal operation.

## Boundaries

- Context7 is not Hermes OS memory.
- Context7 is not Context Mode/RAG.
- Context7 is not a policy source.
- Context7 must never override `merged-hard-gate-policy.yaml`, system
  instructions, local repository files, lockfiles, tests, or direct runtime
  evidence.

## Operating Order

1. Read local project evidence first when a repository is in scope.
2. Resolve the external library with `mcp_context7_resolve_library_id` unless
   the Context7 library ID is already known.
3. Query docs with `mcp_context7_query_docs` for the narrow coding question.
4. Apply Hermes OS policy, local repo constraints, and tests above retrieved
   docs.
5. Mention the relevant docs/version assumption when it materially affects the
   answer or code.

## Source

- MCP server: `https://mcp.context7.com/mcp`
- Tool prefix inside Hermes: `mcp_context7_*`
- Purpose: external docs evidence for coding tasks
