---
name: obsidian-kb-layer-integration
description: |
  Integrate an external markdown-based knowledge base (Obsidian, Notion export,
  or any Markdown vault) with Hermes OS as a Layer 2 knowledge base. Provides
  automated one-way sync from the canonical Fact Store, delta tracking,
  provenance tagging (extracted/inferred/conflicting), and policy boundaries
  to prevent truth drift.

  Follows the Layered Context Architecture: Layer 3 (Fact Store / canonical)
  → Layer 2 (Knowledge Base / compound) → Layer 1 (Working Memory / session).
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [hermes-os, context, memory, obsidian, knowledge-base, sync, fact-store, integration]
---

# Obsidian KB Layer Integration

## When to Use

Use this skill when:
- Boss wants to add a Layer 2 knowledge base to complement Hermes OS
- A new external system stores compound/cross-linked knowledge (Obsidian, Notion, GitBook, etc.)
- You need automated sync from Fact Store to a human-readable format
- Boss asks about "LLM Wiki Pattern", "Karpathy compound knowledge", or "markdown knowledge base"
- There is concern about RAG re-processing the same raw documents every time
- Boss wants human-in-the-loop editing of knowledge without breaking AI pipelines

## Architecture Overview

```
Layer 3 (Canonical Truth)       Layer 2 (Knowledge Base)       Layer 1 (Working Memory)
├─ Fact Store                   ├─ Obsidian Vault               ├─ Context Mode
├─ Policy Gateway               │   ├─ facts/canonical/        ├─ Session hints
└─ Hermes Learning              │   ├─ facts/inferred/          └─ RAG raw retrieval
                                │   ├─ policies/
                                │   ├─ systems/
                                │   ├─ runbooks/
                                │   ├─ incidents/
                                │   └─ learning/
                                └─ .sync_state.json
```

## Policy Boundaries (CRITICAL)

| Rule | Enforcement |
|------|------------|
| **Canonical Truth** | Fact Store wins over Obsidian on policy/system state conflicts |
| **One-way Sync** | Default is Fact Store → Obsidian only. Reverse sync needs explicit approval |
| **Verify Flag** | YAML frontmatter `verify_before_use: true` for inferred content |
| **Provenance** | Every fact tagged: `extracted`, `inferred`, or `conflicting` |
| **Delta Tracking** | Only sync facts newer than `last_sync` timestamp |

## Setup Workflow

### Step 1: Vault Structure

```bash
mkdir -p ~/.hermes/obsidian-vault/.obsidian
mkdir -p ~/.hermes/obsidian-vault/{facts/{canonical,inferred},policies,systems,incidents,runbooks,learning,projects,skills}
```

### Step 2: Sync Script

Python script `~/.hermes/scripts/sync-facts-to-obsidian.py`:
- Reads `~/.hermes/fact_store.jsonl`
- Classifies each fact into vault folder
- Generates YAML frontmatter with provenance
- Creates `[[wikilinks]]` from `related_entities`
- Writes `.md` files

### Step 3: Cron Schedule

```
# Sync every 12 hours, 30 min after auto-run cycle
30 7,19 * * * python3 ~/.hermes/scripts/sync-facts-to-obsidian.py >> ~/.hermes/logs/obsidian_sync.log 2>&1
```

### Step 4: YAML Frontmatter Schema

```yaml
---
fact_id: <id>
source_system: fact_store
verify_before_use: true|false
last_sync: "2026-05-03T02:15:13"
fact_type: fact|policy|incident|runbook
importance: 0-5
provenance: extracted|inferred|conflicting
---
```

### Step 5: Dashboard Integration

Add to `dashboard.html`:
- Node: `obsidian_kb`
- Links: `obsidian_kb → hermes_os_core` (extends), `obsidian_kb → fact_store` (syncs from), `obsidian_kb → memory_graph` (visualizes)

## Classification Rules

| Fact Tags | Vault Folder | Reason |
|-----------|-------------|--------|
| `policy`, `gate` | `policies/` | Governance layer |
| `incident`, `bug` | `incidents/` | Post-mortem |
| `runbook`, `sop` | `runbooks/` | Operational procedures |
| `system`, `infrastructure` | `systems/` | Architecture docs |
| `learning`, `manual` | `learning/` | Knowledge accumulation |
| High importance + verify | `facts/canonical/` | Verified truth |
| Low importance / inferred | `facts/inferred/` | Needs review |

## Phase 2: Wikilink Auto-Generation (Post-Sync)

After the initial sync populates `facts/canonical/` and `facts/inferred/`, run a **wikilink enrichment pass** so Obsidian Graph View shows a connected network instead of orphan dots.

### Fact-to-Fact Wikilinks

```python
#!/usr/bin/env python3
"""Add wikilinks between related facts based on shared tags/keywords."""
import os, glob, re
from pathlib import Path

VAULT = Path.home() / ".hermes/obsidian-vault"

facts = {}
for folder in ["facts/canonical", "facts/inferred"]:
    for fpath in glob.glob(str(VAULT / folder / "*.md")):
        with open(fpath) as f:
            content = f.read()
        tags = re.findall(r'#(\w+)', content)
        fname = os.path.splitext(os.path.basename(fpath))[0]
        rel_path = f"facts/{os.path.basename(folder)}/{fname}"
        facts[fname] = {'path': rel_path, 'tags': tags}

# Build links based on shared tags
for fname, data in facts.items():
    related = []
    for other_name, other_data in facts.items():
        if other_name == fname:
            continue
        shared = set(data['tags']) & set(other_data['tags'])
        if shared:
            related.append((other_name, len(shared)))
    related.sort(key=lambda x: x[1], reverse=True)

    if related:
        wikilinks = "\n\n## 🔗 Related Facts\n\n"
        for rname, count in related[:5]:
            wikilinks += f"- [[{facts[rname]['path']}|{rname}]]\n"
        fpath = VAULT / f"{data['path']}.md"
        with open(fpath, 'a') as f:
            f.write(wikilinks)
```

**Expected result:** ~4.5 wikilinks per fact → Obsidian Graph View shows clusters instead of isolate dots.

### Section Index Cross-Linking

Every `index.md` in section folders must link to **all other section indexes** + `index.md` (home):

```markdown
## 🔗 Related

- [[systems/index|Systems]]
- [[facts/canonical/index|Facts Canonical]]
- [[facts/inferred/index|Facts Inferred]]
- [[projects/index|Projects]]
- [[skills/index|Skills]]
- [[runbooks/index|Runbooks]]
- [[Hermes-os/index|Hermes OS]]
```

**Pattern:** create a fully-connected mesh of section MOCs (Map of Content) so no section is an orphan in Graph View.

## Safety Checklist

- [ ] Vault path set and accessible
- [ ] Sync script tested with dry-run
- [ ] Cron job added and validated
- [ ] `.sync_state.json` tracks last sync
- [ ] Git initialized in vault for Archive & Rebuild
- [ ] Dashboard updated with `obsidian_kb` node
- [ ] Validator run: `validate-dashboard-graph.py --json`
- [ ] **Wikilinks generated** (facts + section indexes)
- [ ] **Section cross-links verified** (no orphan index pages)
- [ ] Boss informed of canonical truth boundary

## Post-Sync Verification Commands (RTK Enforced)

After every sync or cleanup, run these via `rtk run`:

```bash
rtk run 'bash -lc "
echo \"=== Vault Structure ===\"
find ~/.hermes/obsidian-vault/ -maxdepth 2 -type d | sort

echo \"=== Duplicate Check ===\"
ls ~/.hermes/obsidian-vault/ | grep -E \"^Hermes-KB$|^็Hermes-os$\" || echo \"No duplicates\"

echo \"=== Facts Location ===\"
echo \"facts/canonical: $(ls ~/.hermes/obsidian-vault/facts/canonical/ | wc -l) files\"
echo \"facts/inferred: $(ls ~/.hermes/obsidian-vault/facts/inferred/ | wc -l) files\"
echo \"systems/ facts remaining: $(ls ~/.hermes/obsidian-vault/systems/ 2>/dev/null | grep ^fact- | wc -l)\"

echo \"=== RTK COMPLIANT ===\"
"'
```

**Policy:** All verification commands must use `rtk run`. No exceptions. A past incident showed RTK enforcement lapsed during cleanup, producing unverified state.

## Incident Reference
- **2026-05-03**: Nested `Hermes-KB/Hermes-KB/`, misspelled `็Hermes-os`, and facts leaked into `systems/` during WSL→Windows rsync. All fixed via RTK-enforced cleanup.

## Pitfalls

1. **Two Sources of Truth**: If Boss edits `.md` directly and sync overwrites it → confusion. Solution: separate `facts/` (auto-sync) from `manual/` (human-only).
2. **Propagation of Errors**: AI-inferred facts in Obsidian can drift. Solution: `verify_before_use` flag + periodic validator.
3. **Windows/WSL Path Gap**: Windows Obsidian can't see WSL paths directly. **Primary solution**: rsync to Windows-side vault at `C:\Users\<user>\Documents\Obsidian Vault\Hermes-KB\`. Do NOT use `\\wsl.localhost\...` — Node.js `fs.watch` crashes with `EISDIR` on UNC paths, rendering Obsidian unusable.
4. **Nested Folder Duplication (rsync pitfall)**: If sync source already contains a vault root name inside itself, rsync creates `Hermes-KB/Hermes-KB/` nesting. Always verify with `find <vault> -maxdepth 2 -type d | sort` before claiming clean. Remove nested duplicates before opening in Obsidian.
5. **UTF-8 Folder Name Corruption**: Thai vowel characters (e.g., `็`) or combining marks can prefix folder names during encoding mishaps, producing `็Hermes-os` alongside the real `Hermes-os`. Detection: `find` shows both; fix: `rm -rf` the corrupted one immediately. Verify WSL source first, then sync clean state to Windows.
6. **Fact Leakage into Wrong Folders**: Facts may end up in `systems/` instead of `facts/canonical/` if classification rules miss edge cases or if pre-sync files exist in wrong locations. Fix: scan `systems/` for `fact-*.md` → move to `facts/canonical/` or `facts/inferred/` based on frontmatter `category` or `verify_before_use` flag. Re-sync after cleanup.
7. **Missing Provenance**: If frontmatter is missing, treat as `inferred` by default.
8. **Sync Overlap**: Cron must not run during Fact Store heavy writes. Solution: stagger with auto-run cycle.
9. **RTK Enforcement Lapse During Cleanup (2026-05-03 incident)**: During folder cleanup (removing duplicates, fixing misspelled names, moving leaked facts), the agent forgot to wrap `rm -rf`/`rsync`/`mv` commands with `rtk run`. This violates Hermes OS Policy Gateway. **Rule**: EVERY terminal command must use `rtk run`. No exceptions for "quick cleanup" or "small fixes". After discovering the lapse, re-run ALL cleanup commands under `rtk run` and verify state before proceeding.

## Post-Sync Verification Commands (RTK Enforced)

After every sync or cleanup, run these via `rtk run`:

```bash
rtk run 'bash -lc "
echo \"=== Vault Structure ===\"
find ~/.hermes/obsidian-vault/ -maxdepth 2 -type d | sort

echo \"=== Duplicate Check ===\"
ls ~/.hermes/obsidian-vault/ | grep -E \"^Hermes-KB$|^็Hermes-os$\" || echo \"No duplicates\"

echo \"=== Facts Location ===\"
echo \"facts/canonical: $(ls ~/.hermes/obsidian-vault/facts/canonical/ | wc -l) files\"
echo \"facts/inferred: $(ls ~/.hermes/obsidian-vault/facts/inferred/ | wc -l) files\"
echo \"systems/ facts remaining: $(ls ~/.hermes/obsidian-vault/systems/ 2>/dev/null | grep ^fact- | wc -l)\"

echo \"=== RTK COMPLIANT ===\"
"'
```

**Policy:** All verification commands must use `rtk run`. No exceptions. A past incident showed RTK enforcement lapsed during cleanup, producing unverified state.

## Incident Reference
- **2026-05-03**: Nested `Hermes-KB/Hermes-KB/`, misspelled `็Hermes-os`, facts leaked into `systems/`, AND RTK enforcement lapsed during cleanup. All fixed via RTK-enforced re-verification.
- **2026-04-26** (dashboard-html): Graph broke from "node not found" + broken JSON. See `dashboard-html-safe-update` skill.
- Layered Context Architecture: `layered-context-architecture-review` skill
- Dashboard validation: `dashboard-html-safe-update` skill
- Fact Store API: `fact_store` tool (add/search/probe)
- Original Obsidian skill: `obsidian` (basic CRUD)
