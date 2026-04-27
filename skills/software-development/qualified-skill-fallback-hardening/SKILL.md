---
name: qualified-skill-fallback-hardening
description: Harden skill lookup and compatibility fallbacks when qualified names, plugin namespaces, and legacy flat-tree scans overlap.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [debugging, tdd, compatibility, skills, fallback, plugin-routing]
    related_skills: [systematic-debugging, test-driven-development]
---

# Qualified Skill Fallback Hardening

Use this when a skill-loading or registry flow has to support both:
- qualified names like `namespace:skill`
- legacy bare names or flat-tree lookup
- plugin/registry-backed discovery with backward compatibility

This pattern came from hardening `tools/skills_tool.skill_view()` so unknown qualified namespaces fail fast while bare skill names still use the legacy scan.

## Goal

Narrow fallback behavior without breaking compatibility:
- keep the modern/qualified path strict
- keep the legacy path only where it is intentionally supported
- make missing-namespace behavior explicit
- preserve existing plugin-specific missing-item errors

## When to Use

Use when:
- a new registry or namespace model is being introduced
- legacy lookup still exists and may accidentally hide errors
- tests reveal that a fallback is masking the real failure mode
- the user wants compatibility preserved, but only in a narrower scope

## Steps

1. **Map the lookup order**
   - Identify every branch that can resolve the item.
   - Separate qualified-name handling from bare-name handling.
   - Mark which branch is compatibility-only.

2. **Add a failing test first**
   - One test for unknown qualified namespace failing fast.
   - One test proving bare-name legacy fallback still works.
   - One test for the existing in-namespace missing-item error.

3. **Change the narrowest branch**
   - Do not remove legacy lookup globally.
   - Only disable the fallback for qualified names when the namespace is missing.
   - Keep existing behavior when the namespace exists but the item is absent.

4. **Update the error message deliberately**
   - Mention the missing namespace.
   - Tell the user how the remaining fallback works.
   - Avoid ambiguous messages that imply the legacy scan still applies to qualified names.

5. **Verify in layers**
   - Run the targeted regression tests first.
   - Then run the broader related test module.
   - If the full suite fails for unrelated reasons, record that clearly and do not widen the fix.

6. **Document the compatibility boundary**
   - Note which names still use the legacy path.
   - Note which names now fail fast.
   - Add a changelog entry so future routing work does not reopen the same ambiguity.

## Pitfalls

- **Fallback masking**: a missing namespace should not silently search unrelated directories.
- **Over-broad fix**: removing legacy lookup for bare names can break existing users.
- **Unclear tests**: if the test only checks success/failure, it may miss the exact branch that changed.
- **Error drift**: if messages are too vague, users and future tests cannot tell which path fired.
- **Full-suite noise**: unrelated failures can hide the validity of the targeted change; separate them in the report.

## Verification Checklist

- [ ] Qualified names fail fast when namespace is unknown
- [ ] Bare names still hit legacy fallback when intended
- [ ] Existing namespace-specific missing-item error still works
- [ ] Targeted regression tests pass
- [ ] Changelog/report updated with the compatibility boundary

## Example Outcome

Good behavior:
- `myplugin:foo` → plugin lookup only
- `missingplugin:foo` → explicit namespace error
- `foo` → legacy flat-tree scan still allowed

This pattern keeps compatibility while preventing a hidden fallback from obscuring a real routing failure.
