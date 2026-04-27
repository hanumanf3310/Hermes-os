#!/usr/bin/env python3
"""Reference-only thClaws adapter report.

This script reads local study artifacts and prints a compact status report.
It does NOT install, build, run, or execute thClaws.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

REPORT = Path('/tmp/thclaws_hermes_os_report.md')
REPO = Path('/tmp/thclaws-study')

PROVENANCE = {
    'canonical_repo': 'https://github.com/thClaws/thClaws',
    'snapshot_commit': 'c69986b4f172879f9a926f6a7f0c43c4e5ec3af7',
    'observed_version': 'v0.3.3',
    'post_version': 'v0.3.1',
    'study_report': str(REPORT),
    'fact_ids': '230, 231',
    'learning_id': 'policy-0001-candidate-0028',
}

FEATURES = [
    'Rust local-first agent workspace/harness',
    'Desktop GUI + CLI REPL + one-shot prompt surfaces',
    'Multi-provider: Anthropic, OpenAI, Gemini, DashScope, OpenRouter, Ollama, Agentic Press',
    'MCP, SKILL.md, AGENTS.md/CLAUDE.md, plugin manifests',
    'KMS/local knowledge, memory, subagents, Agent Teams',
    'Worktree-based team isolation, permissions, filesystem sandbox, destructive command warnings',
]

PHASES = [
    'Phase 1: reference adapter (current) — no install/run',
    'Phase 2: Boss-approved install/build readiness gate',
    'Phase 3: local smoke gate with no provider secrets',
    'Phase 4: controlled workspace wrapper with allowlisted repo paths',
    'Phase 5: disposable-repo Agent Teams evaluation',
    'Phase 6: optional Hermes OS router backend integration',
]

FORBIDDEN_WITHOUT_APPROVAL = [
    'install/build/run thClaws',
    'pass API keys/provider credentials/secrets',
    'run thClaws teams/MCP/plugins',
    'mutate production repos or infrastructure',
    'push/merge/deploy or edit secrets',
]


def bullet(items):
    return '\n'.join(f'  - {item}' for item in items)


def main() -> int:
    report_exists = REPORT.exists()
    repo_cache_exists = REPO.exists()
    report_size = REPORT.stat().st_size if report_exists else 0

    print('thClaws Reference Adapter Report')
    print('=' * 34)
    print(f'generated_utc: {datetime.now(timezone.utc).isoformat()}')
    print('mode: reference-only')
    print('executes_thclaws: no')
    print('installs_or_builds_thclaws: no')
    print()
    print('Provenance:')
    for k, v in PROVENANCE.items():
        print(f'  {k}: {v}')
    print()
    print('Local artifacts:')
    print(f'  report_exists: {report_exists}')
    print(f'  report_size_bytes: {report_size}')
    print(f'  repo_cache_exists: {repo_cache_exists}')
    print()
    print('Feature map:')
    print(bullet(FEATURES))
    print()
    print('Hermes OS fit:')
    print('  Hermes OS remains coordinator/policy/memory/router.')
    print('  thClaws may become an optional external workspace/team backend after gates pass.')
    print('  This adapter keeps thClaws outside Hermes OS core.')
    print()
    print('Adoption phases:')
    print(bullet(PHASES))
    print()
    print('Forbidden without separate Boss approval:')
    print(bullet(FORBIDDEN_WITHOUT_APPROVAL))
    print()
    print('Recommended next step:')
    print('  Request explicit approval for Phase 2 install/build readiness gate if Boss wants to proceed beyond reference-only.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
