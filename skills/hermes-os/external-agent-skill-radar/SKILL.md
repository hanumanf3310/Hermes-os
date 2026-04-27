---
name: external-agent-skill-radar
description: Build a governance-first external Agent Skills catalog for Hermes OS from curated repos such as VoltAgent/awesome-agent-skills; parse, analyze, report, ingest learning, and recommend Boss-approved imports without bulk auto-install.
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [hermes-os, skills, catalog, governance, skill-radar, awesome-agent-skills, external-skills]
    related_skills: [hermes-learning-manual-ingest-workflow, knowledge-skill-fact-memory-integration, omx-coding-agent]
---

# External Agent Skill Radar

Use this when Boss asks to study a large external Agent Skills repository, marketplace, or external agent harness/workspace and explain how to apply it to Hermes OS.

Primary examples validated:
- `VoltAgent/awesome-agent-skills`
- Source: `https://github.com/VoltAgent/awesome-agent-skills`
- Pattern: treat it as an external curated skill catalog / radar, not as a trusted package store.
- `thClaws/thClaws`
- Source: `https://github.com/thClaws/thClaws`
- Pattern: treat it as an external local-first agent harness reference first, not as an immediately trusted runtime backend.

## Core principle

Do **not** bulk import or execute external skills automatically.

Use this governance-first flow:

```text
External skills repo
  → read-only catalog ingestion
  → quality/security gate
  → skill gap analysis
  → Boss-approved import only
  → Hermes skill registry
  → Hermes OS router / Fleet / OMX / OpenCode backend
```

For external agent harness/workspace repos, use a similar but stricter flow:

```text
External harness repo
  → canonical URL + snapshot commit
  → read-only docs/source inspection
  → architecture + safety model analysis
  → Hermes OS adoption plan
  → Fact Store + Hermes Learning ingest
  → Boss-approved reference adapter
  → only later: sandboxed install/build/smoke gate
  → only later: optional execution/team backend with approval registry
```

Do not install, build, run, connect providers, pass secrets, or execute external harness/team features during the study phase unless Boss explicitly approves that scope.

## When to use

- Boss sends a repo/list of skills and says “เรียนรู้”, “ทำรายงาน”, “ปรับใช้กับ Hermes OS”.
- You need to evaluate 100+ skills without flooding context.
- You need a reusable adoption plan for official/community skills.
- You need to decide which external skills should become local Hermes skills.
- You need to enrich Hermes OS routing with stack-specific best-practice references.

## Procedure

### 1. Canonicalize and fetch

Remove tracking params from URLs where possible, but keep original source in the report if useful.

When `HERMES_RTK_WRAP=1`, every Hermes `terminal` command must be explicitly wrapped:

```bash
rtk run "<command>"
```

Do not call `git`, `python3`, `npm`, `cargo`, `codex`, `omx`, or other commands directly through the terminal tool unless RTK is unavailable/broken and Boss approves a temporary bypass.

For GitHub repos:

```bash
rtk run "rm -rf /tmp/<repo>-study; git clone --depth 1 https://github.com/<org>/<repo>.git /tmp/<repo>-study && cd /tmp/<repo>-study && git rev-parse HEAD"
```

Also fetch GitHub API metadata:

```python
import json, urllib.request
url = 'https://api.github.com/repos/<org>/<repo>'
repo = json.load(urllib.request.urlopen(url, timeout=30))
```

Record:
- full name
- description
- stars/forks/open issues
- license
- default branch
- created/pushed/updated timestamps
- snapshot commit

### 2. Inspect docs and quality standards

Read README in chunks, not all at once if it is large.

For `awesome-agent-skills`, important evidence was:
- README says it is “Hand-picked, not AI-slop generated”.
- README says it is compatible with Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot, OpenCode, Windsurf.
- README lists official/community skill providers such as Anthropic, Google Gemini, Stripe, Cloudflare, HashiCorp, Sentry, Vercel, Hugging Face, Figma, Microsoft, OpenAI, etc.
- README quality criteria include: clear description, progressive disclosure, no absolute paths, scoped tools.
- README disclaimer says listed skills are not security-audited/guaranteed by the curator and should be reviewed before production use.

### 3. Parse catalog metadata

For Markdown lists like `awesome-agent-skills`, parse linked bullets:

```python
from pathlib import Path
import re, collections
from urllib.parse import urlparse

text = Path('/tmp/awesome-agent-skills-study/README.md').read_text()
skills = []
current = None
for i, line in enumerate(text.splitlines(), 1):
    stripped = line.strip()
    mhead = re.match(r'^(?:###\\s+|<summary><h3[^>]*>)(.*?)(?:</h3></summary>)?$', stripped)
    if mhead:
        title = re.sub('<[^>]+>', '', mhead.group(1)).strip()
        if title and not title.startswith('|'):
            current = title
    m = re.match(r'^- \\*\\*\\[([^\\]]+)\\]\\(([^)]+)\\)\\*\\*\\s*-\\s*(.*)$', line)
    if m:
        skills.append({
            'line': i,
            'name': m.group(1),
            'url': m.group(2),
            'desc': m.group(3),
            'section': current or '',
            'host': urlparse(m.group(2)).netloc,
        })

print('skills_count', len(skills))
print('sections_count', len(set(s['section'] for s in skills)))
print(collections.Counter(s['host'] for s in skills).most_common(10))
print(collections.Counter(s['section'] for s in skills).most_common(20))
```

Pitfall: README badges may claim 1000+/1100+ while Markdown parsing may find fewer entries due to formatting. Report both values honestly:
- claimed/positioned count from README
- parsed count from snapshot

### 3B. Inspect external agent harness/workspace repos

For a repo that is a runnable agent harness rather than a skill catalog, inspect these evidence points before recommending adoption:

- Current version from package manifests and changelog; compare with social-post claims and report drift honestly.
- Core architecture: harness loop, provider layer, tool routing, permissions, context compaction, memory/KMS, sessions, subagents, team orchestration, sandboxing, UI surfaces.
- Execution surfaces: GUI, CLI REPL, one-shot, daemon/server, team mode.
- Provider/secret handling: supported providers, where credentials are stored, whether secrets could be passed to child agents/processes.
- Standards and interop: `SKILL.md`, MCP, `AGENTS.md`, `CLAUDE.md`, plugin manifests, worktree conventions.
- Safety gates: permission modes, filesystem sandbox, destructive command warnings, MCP/process allowlists, role guards, audit logs.
- Supply-chain risk: external skill/plugin install, git/zip installs, dependency churn, repo age, release cadence, licenses.

For thClaws specifically, the validated study pattern was:

```text
Canonical repo: https://github.com/thClaws/thClaws
Studied snapshot: c69986b4f172879f9a926f6a7f0c43c4e5ec3af7
Finding: social post discussed v0.3.1, but repo snapshot was v0.3.3
Positioning: Rust local-first agent harness/workspace with GUI/CLI/one-shot, multi-provider, SKILL.md, MCP, KMS, subagents, and worktree-based Agent Teams
Recommended Hermes OS stance: reference-only first; possible local workspace/team backend only after Boss-approved install/build/smoke gates
```

Recommended Hermes OS adoption phases for harness repos:

1. Reference-only study/report.
2. Create a read-only `<harness>-reference-adapter` skill with provenance and risk notes.
3. Boss-approved sandboxed install/build/smoke test.
4. Harness interoperability map: Hermes skill lifecycle ↔ external `SKILL.md`/MCP/permission/team semantics.
5. Controlled backend option with command allowlist, worktree isolation, audit logs, and no automatic secret pass-through.
6. UI/surface learning without coupling Hermes OS to the external runtime.

### 4. Analyze for Hermes OS adoption

Classify candidate skills by:
- source trust tier
- domain
- risk level
- local Hermes overlap
- likely backend: Hermes direct, Fleet, OMX, OpenCode, browser, terminal, web

Recommended trust tiers:

| Tier | Source | Default action |
|---|---|---|
| T1 | Official team skill from known vendor | Candidate for import after review |
| T2 | Well-known community skill with adoption | Reference first, import after manual review |
| T3 | Unknown community skill | Inspect only |
| T4 | Credentials/deploy/payment/security | Import only with explicit Boss approval and sandboxed tests |

High-value domains to check first for Hermes OS:
- Cloudflare Workers/Wrangler/Durable Objects
- Stripe best practices
- Trail of Bits/security
- Playwright/webapp-testing
- HashiCorp Terraform
- Sentry/Datadog observability
- Vercel/Next.js/React
- OpenAI/Gemini/Hugging Face

### 5. Recommend architecture

For Hermes OS, propose these components:

1. `external_skill_catalog_ingestor`
   - Fetch/parse external repo.
   - Write normalized JSONL catalog.

2. `skill_quality_gate`
   - Check provenance, license, archived/stale status, risky commands, absolute paths, broad tool use.

3. `skill_gap_analyzer`
   - Compare external catalog with local `~/.hermes/skills`.
   - Rank missing high-value skills.

4. `skill_adapter_generator`
   - Generate Hermes SKILL.md adapter only after Boss approval.
   - Preserve source URL/commit/provenance.
   - Keep large docs as linked references, not inline.

5. `skill_runtime_resolver`
   - During routing, suggest relevant local/external skills.
   - External-only skills enrich context; they do not execute unless imported/approved.

6. `skill_audit_ledger`
   - Track import/review/update decisions and source commit/checksum.

### 6. Write a report

Save a source-backed report to `/tmp/<topic>_hermes_os_report.md`.

Include:
- source URL and snapshot commit
- repo metadata
- parsed counts and caveats
- notable sections/providers
- quality standards
- Hermes OS adoption architecture
- security/governance risks
- recommended phases
- priority shortlist
- next action / POC proposal

### 7. Ingest into Hermes Learning

Use the manual learning workflow:

```bash
python3 - <<'PY'
import importlib.util, shlex
from pathlib import Path
skill_path = Path.home() / '.hermes/skills/hermes-os-integration/skill.py'
spec = importlib.util.spec_from_file_location('hermes_os_integration_skill', skill_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
skill = mod.HermesOSSkill()
assert skill.initialize() and skill.is_active()
cmd = 'ingest note ' + shlex.quote('<summary>') + ' --link <canonical-url> --file <report-path> --title ' + shlex.quote('<title>') + ' --tags external-skills,skill-radar,hermes-os --quality-gate 0.7'
print(skill.handle_command('hermes-learning', cmd))
PY
```

Verify the returned policy id and search the ledger.

### 8. Add durable fact

Use `fact_store.add` with a compact summary:
- source repo
- snapshot commit
- key counts
- recommendation: catalog/radar + quality gate + Boss-approved import, not bulk auto-import

## Acceptance criteria

- Source metadata and snapshot commit recorded.
- README/docs inspected directly.
- Parsed catalog count reported with caveats.
- Hermes OS adoption plan includes governance/security, not just “install all”.
- Report saved to `/tmp`.
- Hermes Learning ingest returns a policy candidate with `Sources read` and `Avg quality`.
- Fact store entry added.

## Pitfalls

- Do not trust social-post claims without checking repo/API.
- Do not treat a curated list as security-audited packages.
- Do not bulk import external skills into `~/.hermes/skills`.
- Do not grant broad tools to imported skills by default.
- Do not hide mismatch between claimed skill count and parsed snapshot count.
- Do not let product/marketing skills pollute coding-route resolution unless task intent matches.

## Recommended final stance

For Hermes OS, external Agent Skill repositories should become **read-only skill intelligence catalogs** first. Import only selected skills after quality/security review and explicit Boss approval. Use the catalog to improve routing, gap analysis, and stack-specific context for Fleet/OMX/OpenCode workflows.
