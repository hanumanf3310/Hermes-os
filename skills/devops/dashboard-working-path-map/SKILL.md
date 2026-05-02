---
name: dashboard-working-path-map
description: Maintain /home/hanuman3310/hermes-workspace/memory-graph/dashboard.html as Boss's shared working-path map for main Hermes and Hermes OS; update and validate graph routes whenever system-impacting tools, skills, agents, or workflows change.
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [dashboard, memory-graph, hermes-os, workflow-map, validation]
---

# Dashboard Working-Path Map

Use this skill whenever a task changes or adds anything that affects Hermes, Hermes OS, routing, skills, external agents, admin helpers, default models, approval boundaries, or major workflow decisions.

Boss wants `dashboard.html` to be a shared working-path map and decision aid for both main Hermes and Hermes OS, not just a static visualization.

When the dashboard is moved into the workspace host, prefer mounting it as `public/dashboard.html` and verify the exact file path on the live tunnel. A root tunnel or shortcut route like `/chat` can still 404 even when `/dashboard.html` works.

## Canonical file

```text
/home/hanuman3310/hermes-workspace/memory-graph/dashboard.html
```

## Validator

Use the dashboard validator after every dashboard edit. Pass the dashboard path explicitly when validating a specific file:

```bash
rtk run "$HOME/.hermes/scripts/validate-dashboard-graph.py --json /home/hanuman3310/hermes-workspace/memory-graph/dashboard.html"
```

Validator path:

```text
~/.hermes/scripts/validate-dashboard-graph.py
```

It checks:
- duplicate node IDs
- duplicate exact links
- links referencing missing nodes
- connected components
- isolated nodes
- required Boss / Hermes OS / thClaws cross-links

A valid dashboard should report:

```json
{
  "duplicate_nodes": [],
  "duplicate_links": [],
  "missing_link_references": [],
  "connected_components": 1,
  "isolated_nodes": [],
  "missing_required_links": [],
  "ok": true
}
```

## When to update dashboard.html

Update the dashboard when any of these change:

1. New or changed skill/tool that affects workflows.
2. New external agent/harness, e.g. thClaws, OpenCode, OMX, Codex bridge.
3. Default model changes, e.g. thClaws native Ollama default `ollama/qwen3.5:cloud`.
4. New wrapper/gate script, e.g. `thclaws-safe`, `thclaws-update-gate`, dashboard validator.
5. Admin helper or sudo/package approval workflow changes, e.g. `hermes-admin`.
6. New Hermes OS route, policy gate, learning workflow, fact workflow, or approval boundary.
7. Anything that changes the intended path Boss/Hermes should use to decide or act.

## Required graph principles

Every system-impacting node must connect into the main working path. Do not leave islands.

Main spine should remain connected:

```text
Boss Profile
→ Hermes OS Core
→ Hermes Workspace / Enterprise Fleet
→ subsystem/project/tool
→ relevant skill/gate/model/report
```

For Boss-governed capabilities, include direct Boss cross-links where relevant:

```text
Boss Profile → selected default model
Boss Profile → approved plan/gate
Boss Profile → requested learning record
Boss Profile → owns governance/project
```

For Hermes OS capabilities, include:

```text
Hermes OS Core → Enterprise Fleet
Hermes OS Core → runtime/project
Hermes OS Core → external adapter/harness
Hermes OS Integration → Hermes OS Core
Hermes Workspace → runtime/project
Memory Graph → visualizes runtime/project
```

For implementation plans, connect the plan skill to the delivered system:

```text
Writing Plans → update-safe plan
Writing Plans → project/harness
Software → update gate/project
```

## Edit workflow

1. Read the dashboard before editing:

```text
read_file("/home/hanuman3310/hermes-workspace/memory-graph/dashboard.html")
```

2. Add nodes in the appropriate section:
- Memory Facts: user/Boss preferences, durable system facts, selected defaults.
- Categories: major capability groupings.
- Skills: reusable tools/procedures/wrappers.
- Projects: active systems or runtime harnesses.
- Orphans: only for explicit gaps or missing dependencies.

3. Add links that explain why the node exists and how it is used. Prefer meaningful `type` values such as:

```text
controls
selected
approved-plan
requested-learning
owns-governance
integrates
powers
orchestrates
external-adapter
protected-by
validates
visualizes
hosts
contains
```

4. Update visible stats in the header if node/skill/category counts changed enough to matter.

5. Run structural validation:

```bash
rtk run "$HOME/.hermes/scripts/validate-dashboard-graph.py --json"
```

6. Open/render-check the dashboard when available:

```text
browser_navigate("file:///home/hanuman3310/hermes-workspace/memory-graph/dashboard.html")
browser_console(expression="({circles: document.querySelectorAll('circle').length, lines: document.querySelectorAll('line.link').length})")
```

If the dashboard uses more than one <script> tag, inspect all script blocks when debugging data presence:

```text
browser_console(expression="([...document.querySelectorAll('script')].map(s => s.textContent).join('\n'))")
```

Expected rendered counts should match validator node/link counts.

7. Report to Boss with:
- nodes count
- links count
- validator `ok`
- key new nodes/links
- any caveats

## Current known baseline after Context Mode / RAG index update

As of the validated Context Mode / RAG index dashboard update:

```text
nodes: 82
links: 139
ok: true
```

Important connected nodes include:
- Boss Profile
- Hermes OS Core
- Enterprise Fleet
- Hermes OS Runtime
- Hermes Workspace
- Memory Graph
- thClaws Harness
- thClaws qwen3.5
- thClaws Update-safe
- thClaws Update Gate
- Dashboard Validator
- hermes-admin
- Context Mode RAG Index
- Context Mode
- Core Docs Index

When adding RAG / Context Mode work to the graph, prefer three connected artifacts:
- memory node for the verified indexing event / retrieval capability (for example `context_mode_rag_index`)
- skill node for the Context Mode retrieval tool/layer
- project node for the indexed corpus (for example `proj_core_docs_index`)

Connect them back to Boss Profile, Hermes OS Core, Fact Store, Memory Graph, and the indexed policy/skill docs so the graph shows Context Mode as a working-memory/RAG layer that complements Fact Store rather than replacing canonical facts.

## Dynamic Fact Store mode

When the dashboard should reflect the live Fact Store instead of static sample data, use a tiny local HTTP backend that serves graph JSON from the shared SQLite DB.

Recommended pattern:

1. Build a small local HTTP backend near the dashboard workspace.
2. Read facts from the shared Fact Store DB through the existing memory store layer.
3. Expose `GET /api/fact-graph` and `GET /health`.
4. Keep `dashboard.html` able to fall back to file-local or static data when the backend is unavailable.
5. Make `Fact*` a first-class filter in the payload so the dashboard can render governance nodes distinctly.

Example backend shape:

```text
/home/hanuman3310/hermes-workspace/memory-graph/fact_graph_backend.py
```

Payload fields that should survive the round-trip:
- `fact_id`
- `fact_type`
- `fact_star`
- `fact_plus`
- `verify_before_use`
- `importance_level`
- `star_reason`
- `verification_status`
- `impact_scope`
- `related_entities`

For file:// dashboards, using a hardcoded local URL like `http://127.0.0.1:9120/api/fact-graph` is acceptable if the backend is launched locally and validated.

## Mobile / external access pattern

6. If Boss wants a mobile link to the dashboard, include the exact dashboard path as well as the root URL. Do not assume shortcut routes like `/chat` exist unless they are explicitly routed; those can 404 even when `/dashboard.html` works.
7. If the same workspace host already serves UI + API, prefer mounting `dashboard.html` inside that host instead of exposing a separate static tunnel. A single HTML file is only enough for the page shell; live graph data still needs the matching backend endpoint on the same host or an explicitly wired fallback.
8. If the tunnel provider shows an interstitial/warning page on first visit, click through it and verify the real page behind it before claiming success.
9. If Boss asks to "check dashboard first" or "report before doing A" for a governance-sensitive action such as RAG / Context Mode integration, do a read-only live preflight and stop with a report before editing or indexing:

   - Load the exact public `/dashboard.html` URL and click through any tunnel interstitial.
   - Verify rendered counts from the page runtime (`data.nodes`, `data.links`, SVG circles/lines) and check missing link references in the browser console.
   - Check read-only status: visible controls should be inspection/export/navigation only, not create/update/delete controls.
   - Search the live page text/runtime for the target capability keywords, e.g. `RAG`, `Context Mode`, `Vector`, `Index`, before claiming the dashboard already covers that work.
   - Probe expected backend endpoints such as `/health` and `/api/fact-graph`; if they return the workspace SPA HTML instead of JSON, report this as a backend/API caveat rather than treating HTTP 200 as proof of live graph data.
   - State explicitly whether you have modified anything. If Boss requested report-first, do not modify files until Boss gives the follow-up go-ahead.

10. If a previously shared tunnel URL stops resolving, treat it as expired and refresh the launcher/status before re-reporting.
11. Keep the local URLs explicit for debugging:

   - `http://127.0.0.1:9130/api/fact-graph`
   - `http://127.0.0.1:9130/health`

Example launcher shape:

```text
~/.local/bin/hermes-memory-graph
```

Success criteria for the mobile-access flow:

- dashboard loads in a browser
- `/health` returns ok
- `/api/fact-graph` returns live data
- public tunnel URL opens the dashboard on a phone
- exact dashboard path is verified, not just the tunnel root

## Pitfalls

- Adding nodes without cross-links creates graph islands even if the page renders.
- Connecting only category → skill can leave the new capability disconnected from Boss/Hermes OS decision paths.
- Browser render success does not prove semantic correctness; always run the validator.
- Do not assume dashboard.html can fetch live data without a backend. If dynamic facts are needed, add a small local API and verify it with `/health` and `/api/fact-graph` before wiring the page.
- Do not replace Fact Store or Hermes Learning with dashboard edits. Use all three: Fact/Learning for durable recall, dashboard for route visibility and decision paths.

## Done criteria

A dashboard-impacting task is not complete until:

- `dashboard.html` includes the new/changed nodes and links.
- The graph validates with `ok: true`.
- Rendered circle/link counts are checked when browser tools are available.
- Boss receives a concise summary of what was connected.
