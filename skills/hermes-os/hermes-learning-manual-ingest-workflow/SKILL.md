---
name: hermes-learning-manual-ingest-workflow
description: Add and validate manual-only Hermes learning ingest commands (feedback/policy/note) with contract tests.
version: 1.2.0
author: Hermes Agent
---

# Hermes Learning Manual Ingest Workflow

## When to use
- You need Hermes OS learning to be explicitly operator-triggered (no auto learning loop).
- You need new command surfaces under `hermes-learning`.
- You need to ingest feedback signals, policy JSON, or long-form notes (+optional links) safely.

## Command contract
Implement/maintain these command shapes in `hermes-os-integration/skill.py`:
- `hermes-learning`
- `hermes-learning status`
- `hermes-learning run [limit] [min_samples]`
- `hermes-learning ingest feedback <task_id> <label> [note]`
- `hermes-learning ingest policy <json>`
- `hermes-learning ingest note <text> [--link <url>]... [--file <path>]... [--title <text>] [--tags a,b,c] [--quality-gate 0.0-1.0] [--force]`

Expected behavior:
- Manual-only messaging (operator-triggered only).
- `run` calls bridge `run_learning_control_cycle(... actor="operator", source="hermes-learning-command")`.
- `ingest feedback` calls bridge `capture_routing_feedback`.
- `ingest policy` parses JSON, extracts optional `rationale`, and calls bridge `propose_policy(payload, rationale=...)`.
- `ingest note` composes rationale from operator text plus optional fetched URL content and/or local file text, then calls bridge `propose_policy({}, rationale=...)`.
- `ingest note` supports multiple `--link` and multiple `--file` flags; supports metadata `--title` and `--tags`; response reports `Sources read: X/Y` and `Avg quality: NN%`.
- `ingest note` computes per-source quality and includes `source_quality[...]` entries in rationale.
- Optional quality gate: `--quality-gate <0..1>` blocks low-quality saves unless `--force` is present.

## Implementation steps
1. Update `handle_command` routing to include `hermes-learning`.
2. In `_handle_hermes_learning_command`, keep explicit usage responses for invalid input.
3. Add `ingest` subcommand branch with three kinds:
   - `feedback`: parse task_id/label/note.
   - `policy`: parse JSON payload, validate mapping type.
   - `note`: parse free text with optional repeated flags `--link <url>` and `--file <path>`; metadata flags `--title` / `--tags`; optional `--quality-gate`; optional `--force`; include inline URLs found in note text.
4. Add helpers in `skill.py`:
   - `_extract_urls(text)` regex extraction (`http/https`).
   - `_fetch_url_text(url, timeout=10, max_chars=4000)` with safe fetch + HTML/script/style cleanup.
   - `_read_text_file(file_path, max_chars=4000)` safe local file reader with `.pdf` handoff.
   - `_read_pdf_file(file_path, max_chars=4000)` best-effort PDF extraction (pypdf).
   - `_score_source_quality(text)` heuristic `0..1` quality score.
   - `_compose_learning_note_rationale(note_text, sources, source_urls, source_files, title, tags)` to compact combined evidence and per-source quality.
5. Keep legacy `hermes-os auto-run run/loop` deprecated/disabled and redirect to `hermes-learning run`.
6. Update help text and command registry strings to mention `status/run/ingest` and note-mode syntax.

## Test strategy (contract test file)
Use `skills/hermes-os/v3/test_status_readiness_policy_apply_contract.py`.

Add/maintain mock bridge support:
- `capture_routing_feedback`
- `propose_policy`
- call tracking fields (e.g., `calls_feedback`, `calls_propose`)

Required tests:
1. `hermes-learning run` executes manual cycle and passes source `hermes-learning-command`.
2. `hermes-learning ingest feedback ...` returns success and records bridge call args.
3. `hermes-learning ingest policy ...` returns success and records parsed payload + rationale.
4. `hermes-learning ingest note <text>` creates candidate with rationale derived from note text.
5. `hermes-learning ingest note ... --link ... --link ...` reads multiple links and includes each source in rationale.
6. `hermes-learning ingest note ... --file <path>` reads attachment content and includes file path + summary in rationale.
7. `hermes-learning ingest note ... --title ... --tags ...` injects metadata fields into rationale.
8. `hermes-learning ingest note ... --file <pdf>` uses PDF extractor path and persists extracted evidence.
9. `hermes-learning ingest note ... --quality-gate X` blocks save when avg quality is below threshold.
10. `hermes-learning ingest note ... --quality-gate X --force` allows override save.

Run targeted tests:
- `pytest -q ~/.hermes/skills/hermes-os/v3/test_status_readiness_policy_apply_contract.py -q`

## Pitfalls
- `ingest feedback` needs a real `task_id` that already has routing telemetry; otherwise bridge returns not found.
- URL fetch can fail (404/timeout); keep ingest successful with partial sources and report `Sources read: X/Y`.
- File ingest supports text files and best-effort PDF extraction (`pypdf`). Scanned-image PDFs may still require OCR pipeline.
- Keep usage strings precise; contract tests assert output snippets.
- Avoid re-enabling auto scheduler loops when user requested manual-only mode.
- The shell command `hermes-learning` may not exist in PATH even when the Hermes OS skill command works through Telegram/runtime. If `command -v hermes-learning` fails, invoke the skill directly for manual ingest verification:

```bash
python3 - <<'PY'
import importlib.util
from pathlib import Path
skill_path = Path.home() / ".hermes/skills/hermes-os-integration/skill.py"
spec = importlib.util.spec_from_file_location("hermes_os_integration_skill", skill_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
skill = mod.HermesOSSkill()
assert skill.initialize() and skill.is_active()
print(skill.handle_command(
    "hermes-learning",
    "ingest note <summary> --link <url> --file <report.md> --title <title> --tags tag1,tag2 --quality-gate 0.7"
))
PY
```

## Research/link ingest workflow (reusable)
When Boss asks to study a link/repo, report, and ingest it:
1. Canonicalize the user URL by removing tracking params when possible, but keep the original/source URL in the report.
2. Fetch/clone/read the source with tools; for GitHub repos, shallow clone to `/tmp/<repo>-study`, read README/architecture/runbook/testing docs, and gather lightweight stats.
3. Write a compact source-backed report to `/tmp/<topic>_learning_report.md` (avoid secrets; include source URL, snapshot commit if cloned, key findings, risks, and applicability to Hermes/Fleet).
4. Ingest with `hermes-learning ingest note ... --link <canonical-url> --file <report> --title ... --tags ... --quality-gate 0.7`.
5. Verify the returned `policy_id`, `Sources read: X/Y`, and optionally search `~/.hermes/state/hermes_os_learning_policy.jsonl` for the policy title.
6. Add a concise `fact_store` entry for durable recall when the topic is likely reusable.

## Post-change documentation + memory sync (recommended)
After command-surface changes are merged, sync durable docs so operators don't drift:
1. Update `~/.hermes/database/hermes-os-learning/LEARNING_DATABASE.md` with a current-state section.
2. Ensure quick docs exist and match runtime behavior:
   - `README.md` (overview)
   - `QUICK_GUIDE.md` (copy/paste command examples)
3. Add/refresh a documentation index section in `LEARNING_DATABASE.md` linking README/QUICK_GUIDE/PHASE3 plan.
4. Persist a compact fact via `fact_store` describing current command contract and safety posture (manual-only, no auto-apply, quality gate semantics).

## Done criteria
- Command behavior works for no-args/status/run/ingest.
- Contract tests for these paths pass.
- Help/command discovery text reflects `status/run/ingest`.
- Learning docs are synchronized (LEARNING_DATABASE + README + QUICK_GUIDE + index links).
- One concise fact entry captures the new behavior for future recall.