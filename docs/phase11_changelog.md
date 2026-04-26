# Phase 11 Changelog

## 2026-04-23 — Task 2: Narrow legacy fallback
- Changed `tools/skills_tool.py` so qualified skill names (`namespace:skill`) no longer fall through to the legacy flat-tree scan when the namespace is unknown.
- Preserved the flat-tree scan as a compatibility path for bare skill names only.
- Kept plugin-specific missing-skill errors unchanged when a namespace exists but the requested skill is absent.

## Verification
- Targeted plugin skill tests passed:
  - `tests/test_plugin_skills.py::TestSkillViewQualifiedName::test_unknown_namespace_returns_error`
  - `tests/test_plugin_skills.py::TestSkillViewQualifiedName::test_bare_name_still_uses_flat_tree`
  - `tests/test_plugin_skills.py::TestSkillViewQualifiedName::test_plugin_exists_but_skill_missing`
- Full suite was also attempted, but the current branch shows unrelated pre-existing failures outside this change set.
