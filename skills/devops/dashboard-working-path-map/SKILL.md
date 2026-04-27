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

## Current known baseline after dashboard validator addition

As of the validated dashboard update:

```text
nodes: 59
links: 84
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

If Boss wants `/memory-graph/dashboard.html` accessible from a phone or outside the machine, do **not** use `file://`. Serve the page over HTTP(S) and tunnel it.

Working pattern learned from the real setup:

1. Run one local server that serves both the dashboard and the API from the same origin.
2. Add a one-command launcher with `up / down / status / restart`.
3. Use a free public tunnel such as `cloudflared` quick tunnel for mobile access.
4. Print the public URL after startup and verify it before reporting success.
5. Keep the local URLs explicit for debugging:
   - `http://127.0.0.1:9130/dashboard.html`
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
