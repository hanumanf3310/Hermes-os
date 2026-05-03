---
name: project-glossary-ddd
title: Project Glossary Creation (Domain-Driven Design Style)
version: 1.0.0
description: |
  Create and maintain a project glossary / shared language document inspired by
  Domain-Driven Design's Ubiquitous Language pattern and Matt Pocock's CONTEXT.md.

  Ensures AI agents, developers, and stakeholders use consistent terminology,
  reducing miscommunication and token waste in prompts.

  Evidence-first. Hermes OS compatible.

tags:
  - glossary
  - ddd
  - context
  - vocabulary
  - shared-language
  - hermes-os
requires_tools:
  - file
  - terminal
author: Boss (Hermes OS Operator)
based_on: mattpocock/context.md + Domain-Driven Design
---

# Project Glossary Creation Skill

## Philosophy

**"A project without a shared language is a project doomed to miscommunication."**

When teams (or AI agents) collaborate on a project, they often use different terms for the same concept. This wastes tokens, creates bugs, and slows down development.

This skill creates a **CONTEXT.md** (or equivalent) that serves as the project's Ubiquitous Language — a living dictionary that everyone (including Hermes AI) agrees to use.

---

## When to Use

Trigger this skill when:
- Starting a new project or sub-system
- Project has grown complex (10+ concepts, multiple agents/stakeholders)
- Boss says "AI ไม่เข้าใจโปรเจกต์ของเรา"
- Inconsistent terminology detected in code, docs, or conversations
- New team member / AI agent joins the project
- Onboarding a new execution backend (thClaws, OMX, etc.)

Do NOT use when:
- Simple one-off script (no persistent vocabulary needed)
- Temporary experiment (throwaway)
- Project already has comprehensive glossary (check first)

---

## Workflow

### Phase 1: Discover Terms

```bash
# Extract candidate terms from codebase
rtk run "grep -rhE '^class |^def |^# ' --include='*.py' | sort | uniq" | head -50

# Extract from existing docs
rtk run "grep -rhE '^#{1,3} ' --include='*.md' | sed 's/#//g' | sort | uniq"

# Extract from config files
rtk run "cat ~/.hermes/config.yaml | grep -v '^#' | grep ':'"

# Extract from fact store
# fact_store.search(query='terminology OR vocabulary OR naming')
```

### Phase 2: Interview Stakeholders (Grill-Me Style)

Ask Boss / team:
1. "What are the 10 most important concepts in this project?"
2. "What terms do different people use for the same thing?"
3. "What terms confuse you when reading the code/docs?"
4. "What abbreviations does the team use?"
5. "What terms have you seen AI get wrong?"

Record all answers as evidence.

### Phase 3: Draft Glossary

Create `PROJECT_ROOT/CONTEXT.md` or `~/project-name/CONTEXT.md`:

```markdown
# {Project Name} Glossary

**Version:** 1.0.0
**Date:** YYYY-MM-DD
**Timezone:** Asia/Bangkok (UTC+7)
**Author:** {Name}

## Purpose
{1-2 sentences why this glossary exists}

## Core Terms

| Term | Meaning | Used in | Notes |
|------|---------|---------|-------|
| ... | ... | ... | ... |

## Execution Context Terms

| Term | Meaning | When Used |
|------|---------|-----------|
| ... | ... | ... |

## Abbreviations

| Short | Full |
|-------|------|
| ... | ... |

## Naming Conventions

### Files
- Pattern: {rule}

### Variables
- Pattern: {rule}

## Anti-Patterns

| Don't | Do |
|-------|-----|
| ... | ... |

## Related Documents
- {link to README}
- {link to AGENTS.md}
- {link to policy}
```

### Phase 4: Validate Glossary

```bash
# Verify glossary terms actually appear in codebase
rtk run "python3 -c \"
import re
glossary = open('CONTEXT.md').read()
terms = re.findall(r'\| (\w+) \|', glossary)
for term in terms[:20]:
    count = subprocess.run(['grep', '-r', term, '--include=*.py'], capture_output=True)
    print(f'{term}: {len(count.stdout.splitlines())} occurrences')
\""
# Terms with 0 occurrences = candidate for removal
```

### Phase 5: Maintain

Schedule quarterly reviews:
- Terms added/removed?
- Abbreviations changed?
- New execution contexts?
- Boss feedback on confusion?

Update version number on each change.

---

## Hermes OS Specific

### Integration with Fact Store

Each term should be backed by evidence:

```python
fact_store.add(
    category="project-terminology",
    content="Term 'RTK' means 'RunTokenKit' used in all terminal commands",
    tags="terminology,rtk,glossary,{project}"
)
```

### Integration with Skills

When creating Hermes skills:
```yaml
# In SKILL.md frontmatter
context_file: ~/project-name/CONTEXT.md
# Skill loader reads CONTEXT.md before executing
```

### Integration with Dashboard

Add glossary version as a node:
```javascript
{
    "id": "{project}_glossary_v1",
    "label": "Project Glossary v1.0",
    "type": "documentation",
    "status": "active"
}
```

---

## Example: Hermes OS Glossary

See: `~/hermes-os-blueprint/CONTEXT.md`

Key sections:
1. Core Terms (Hermes OS, Boss, น้องเมส, RTK)
2. Execution Limbs (Fleet, thClaws, OMX)
3. Skill Prefixes (skill_*, proj_*, cat_*)
4. Evidence Labels (✅ 🧭 ⚠️ ❌ 🛑)
5. Protocols (Tiny Trade, Communication)
6. File Paths (standardized)
7. Abbreviations
8. Naming Conventions
9. Anti-Patterns
10. Rules of Thumb

---

## Related
- mattpocock/skills (CONTEXT.md concept)
- hermes-os-blueprint (training context)
- fact-store-evidence-reporting (evidence backing)
- external-repo-analysis-for-os-adoption (research for adoption)
