#!/usr/bin/env python3
"""thClaws Phase 2 install/build readiness gate.

This script performs local, mostly read-only readiness checks for thClaws adoption.
It may inspect toolchain versions and repo metadata. It does NOT run thClaws GUI,
CLI prompt, one-shot agent, teams, MCP servers, plugins, or provider auth.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(os.environ.get('THCLAWS_REPO', '/tmp/thclaws-study'))
OUT_DIR = Path(os.environ.get('THCLAWS_ADAPTER_OUT', str(Path.home() / '.hermes/database/thclaws-adapter')))
OUT_JSON = OUT_DIR / 'phase2_readiness.json'
OUT_MD = OUT_DIR / 'phase2_readiness.md'

FORBIDDEN_EXECUTION = [
    'thclaws --cli', 'thclaws -p', 'thclaws team', 'MCP server spawn',
    'plugin install', 'provider login/auth', 'GUI launch',
]


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 30) -> dict:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout)
        return {'cmd': cmd, 'exit_code': proc.returncode, 'stdout': proc.stdout.strip()[-4000:], 'stderr': proc.stderr.strip()[-4000:]}
    except Exception as exc:  # noqa: BLE001
        return {'cmd': cmd, 'exit_code': None, 'error': repr(exc), 'stdout': '', 'stderr': ''}


def read_text(path: Path, limit: int = 200000) -> str:
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8', errors='ignore')[:limit]


def parse_root_manifest() -> dict:
    text = read_text(REPO / 'Cargo.toml')
    result = {'exists': bool(text), 'workspace_members': [], 'raw_head': text[:2000]}
    m = re.search(r'members\s*=\s*\[(.*?)\]', text, re.S)
    if m:
        result['workspace_members'] = re.findall(r'"([^"]+)"', m.group(1))
    return result


def parse_core_manifest() -> dict:
    text = read_text(REPO / 'crates/core/Cargo.toml')
    deps = []
    section = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('[') and s.endswith(']'):
            section = s.strip('[]')
            continue
        if section and 'dependencies' in section and s and not s.startswith('#') and '=' in s:
            deps.append(s.split('=', 1)[0].strip())
    version = None
    name = None
    for key in ['name', 'version']:
        m = re.search(rf'^{key}\s*=\s*"([^"]+)"', text, re.M)
        if m:
            if key == 'name':
                name = m.group(1)
            else:
                version = m.group(1)
    return {'exists': bool(text), 'name': name, 'version': version, 'dependency_count': len(deps), 'dependencies_sample': deps[:40]}


def parse_frontend_manifest() -> dict:
    path = REPO / 'frontend/package.json'
    try:
        data = json.loads(read_text(path)) if path.exists() else {}
    except Exception as exc:  # noqa: BLE001
        return {'exists': path.exists(), 'error': repr(exc)}
    deps = list((data.get('dependencies') or {}).keys())
    dev_deps = list((data.get('devDependencies') or {}).keys())
    return {'exists': path.exists(), 'name': data.get('name'), 'version': data.get('version'), 'scripts': data.get('scripts', {}), 'dependencies_count': len(deps), 'dev_dependencies_count': len(dev_deps), 'dependencies_sample': deps[:30], 'dev_dependencies_sample': dev_deps[:30]}


def parse_changelog() -> dict:
    text = read_text(REPO / 'CHANGELOG.md')
    versions = re.findall(r'^##\s+\[?v?([0-9]+\.[0-9]+\.[0-9]+)\]?', text, re.M)
    return {'exists': bool(text), 'versions_head': versions[:10], 'mentions_031': '0.3.1' in text, 'mentions_033': '0.3.3' in text}


def detect_risk_patterns() -> dict:
    patterns = {
        'plugin_install': r'plugin.*install|install.*plugin',
        'skill_install': r'skill.*install|install.*skill',
        'mcp': r'\bMCP\b|mcp',
        'shell_escape': r'shell escape|! command|destructive command|Command warnings',
        'provider_keys': r'OPENAI|ANTHROPIC|GEMINI|API[_-]?KEY|DASHSCOPE|OPENROUTER',
        'teams': r'Agent Teams|team mode|worktree',
    }
    docs = []
    for rel in ['README.md', 'SECURITY.md', 'user-manual/ch05-permissions.md', 'user-manual/ch12-skills.md', 'user-manual/ch15-subagents.md', 'user-manual/ch17-agent-teams.md']:
        docs.append((rel, read_text(REPO / rel)))
    hits = {}
    for name, pat in patterns.items():
        rx = re.compile(pat, re.I)
        hits[name] = [rel for rel, text in docs if rx.search(text)]
    return hits


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    checks = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'phase2_install_build_readiness_gate', 'executes_thclaws': False, 'installs_thclaws': False, 'builds_thclaws': False, 'passes_secrets': False, 'repo_path': str(REPO), 'repo_exists': REPO.exists(), 'forbidden_execution_without_next_approval': FORBIDDEN_EXECUTION}
    checks['toolchain'] = {
        'git': run(['git', '--version']), 'rustc': run(['rustc', '--version']), 'cargo': run(['cargo', '--version']),
        'node': run(['node', '--version']), 'npm': run(['npm', '--version']), 'pnpm': run(['pnpm', '--version']) if shutil.which('pnpm') else {'missing': True},
    }
    if REPO.exists():
        checks['git'] = {'commit': run(['git', 'rev-parse', 'HEAD'], REPO), 'remote': run(['git', 'remote', '-v'], REPO), 'status': run(['git', 'status', '--short'], REPO)}
        checks['root_manifest'] = parse_root_manifest()
        checks['core_manifest'] = parse_core_manifest()
        checks['frontend_manifest'] = parse_frontend_manifest()
        checks['changelog'] = parse_changelog()
        checks['risk_patterns'] = detect_risk_patterns()
        checks['cargo_metadata_no_deps'] = run(['cargo', 'metadata', '--no-deps', '--format-version', '1'], REPO, timeout=60)
    else:
        checks['error'] = 'repo cache missing; clone/fetch required before build readiness'

    ready = checks.get('repo_exists') and checks['toolchain']['cargo'].get('exit_code') == 0 and checks['toolchain']['rustc'].get('exit_code') == 0
    checks['phase2_readiness'] = 'ready_for_optional_build_probe' if ready else 'not_ready'
    checks['next_gate_required'] = 'Phase 3 local smoke/build probe requires separate Boss approval before running cargo build/check or thClaws binaries.'

    OUT_JSON.write_text(json.dumps(checks, indent=2, ensure_ascii=False), encoding='utf-8')
    lines = ['# thClaws Phase 2 Readiness Gate', '', f"Generated UTC: {checks['generated_utc']}", '', '## Safety', '', f"- Executes thClaws: {checks['executes_thclaws']}", f"- Installs thClaws: {checks['installs_thclaws']}", f"- Builds thClaws: {checks['builds_thclaws']}", f"- Passes secrets: {checks['passes_secrets']}", '', '## Repo', '', f"- Path: `{REPO}`", f"- Exists: {checks['repo_exists']}", f"- Commit: `{checks.get('git', {}).get('commit', {}).get('stdout', '')}`", f"- Core version: `{checks.get('core_manifest', {}).get('version')}`", '', '## Toolchain', '']
    for k, v in checks['toolchain'].items():
        if v.get('missing'):
            lines.append(f'- {k}: missing')
        else:
            txt = (v.get('stdout') or v.get('stderr') or '').splitlines()
            lines.append(f"- {k}: exit={v.get('exit_code')} `{txt[0] if txt else ''}`")
    lines += ['', '## Risk pattern evidence', '']
    for k, files in checks.get('risk_patterns', {}).items():
        lines.append(f'- {k}: {", ".join(files) if files else "not found in scanned docs"}')
    lines += ['', '## Result', '', f"- Phase 2 readiness: `{checks['phase2_readiness']}`", f"- Next gate: {checks['next_gate_required']}", '', f'JSON: `{OUT_JSON}`']
    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(OUT_MD.read_text(encoding='utf-8'))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
