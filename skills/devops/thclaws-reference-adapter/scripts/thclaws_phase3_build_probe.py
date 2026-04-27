#!/usr/bin/env python3
"""thClaws Phase 3 local build/smoke probe.

This helper runs a controlled Rust compile check only. It does NOT run thClaws
binaries, GUI, CLI prompt, one-shot prompts, teams, MCP servers, plugins, or
provider authentication. It may download/build Rust dependencies via cargo.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(os.environ.get('THCLAWS_REPO', '/tmp/thclaws-study'))
OUT_DIR = Path(os.environ.get('THCLAWS_ADAPTER_OUT', str(Path.home() / '.hermes/database/thclaws-adapter')))
OUT_JSON = OUT_DIR / 'phase3_build_probe.json'
OUT_MD = OUT_DIR / 'phase3_build_probe.md'
OUT_LOG = OUT_DIR / 'phase3_cargo_check.log'

CARGO_CMD = ['cargo', 'check', '--locked', '-p', 'thclaws-core', '--bins', '--lib']


def run_probe() -> dict:
    started = datetime.now(timezone.utc)
    env = os.environ.copy()
    env.pop('OPENAI_API_KEY', None)
    env.pop('ANTHROPIC_API_KEY', None)
    env.pop('GEMINI_API_KEY', None)
    env.pop('GOOGLE_API_KEY', None)
    env.pop('DASHSCOPE_API_KEY', None)
    env.pop('OPENROUTER_API_KEY', None)
    proc = subprocess.run(CARGO_CMD, cwd=str(REPO), text=True, capture_output=True, timeout=900, env=env)
    ended = datetime.now(timezone.utc)
    combined = ''
    if proc.stdout:
        combined += '--- stdout ---\n' + proc.stdout
    if proc.stderr:
        combined += '\n--- stderr ---\n' + proc.stderr
    OUT_LOG.write_text(combined, encoding='utf-8', errors='ignore')
    return {
        'cmd': CARGO_CMD,
        'cwd': str(REPO),
        'exit_code': proc.returncode,
        'started_utc': started.isoformat(),
        'ended_utc': ended.isoformat(),
        'duration_seconds': (ended - started).total_seconds(),
        'stdout_tail': proc.stdout[-4000:],
        'stderr_tail': proc.stderr[-4000:],
        'log_path': str(OUT_LOG),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'phase3_local_build_smoke_probe',
        'executes_thclaws_binary': False,
        'launches_gui': False,
        'runs_cli_prompt': False,
        'runs_team_mcp_plugin': False,
        'passes_provider_secrets': False,
        'mutates_production': False,
        'repo_path': str(REPO),
        'repo_exists': REPO.exists(),
        'probe_kind': 'cargo_check_compile_only',
        'cargo_command': CARGO_CMD,
    }
    if not REPO.exists():
        result['status'] = 'failed_repo_missing'
        OUT_JSON.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print('Repo missing:', REPO)
        return 2
    try:
        result['probe'] = run_probe()
        result['status'] = 'passed' if result['probe']['exit_code'] == 0 else 'failed'
    except subprocess.TimeoutExpired as exc:
        result['status'] = 'timeout'
        result['timeout_seconds'] = exc.timeout
        result['stdout_tail'] = (exc.stdout or '')[-4000:] if isinstance(exc.stdout, str) else ''
        result['stderr_tail'] = (exc.stderr or '')[-4000:] if isinstance(exc.stderr, str) else ''
    except Exception as exc:  # noqa: BLE001
        result['status'] = 'error'
        result['error'] = repr(exc)

    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    p = result.get('probe', {})
    lines = [
        '# thClaws Phase 3 Local Build/Smoke Probe',
        '',
        f"Generated UTC: {result['generated_utc']}",
        '',
        '## Safety',
        '',
        f"- Executes thClaws binary: {result['executes_thclaws_binary']}",
        f"- Launches GUI: {result['launches_gui']}",
        f"- Runs CLI prompt: {result['runs_cli_prompt']}",
        f"- Runs team/MCP/plugin: {result['runs_team_mcp_plugin']}",
        f"- Passes provider secrets: {result['passes_provider_secrets']}",
        '',
        '## Probe',
        '',
        f"- Command: `{' '.join(CARGO_CMD)}`",
        f"- Repo: `{REPO}`",
        f"- Status: `{result['status']}`",
        f"- Exit code: `{p.get('exit_code', '')}`",
        f"- Duration seconds: `{p.get('duration_seconds', '')}`",
        '',
        '## Artifacts',
        '',
        f"- JSON: `{OUT_JSON}`",
        f"- Cargo log: `{OUT_LOG}`",
    ]
    if result['status'] != 'passed':
        tail = p.get('stderr_tail') or result.get('stderr_tail') or ''
        lines += ['', '## Error tail', '', '```text', tail[-3000:], '```']
    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(OUT_MD.read_text(encoding='utf-8'))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
