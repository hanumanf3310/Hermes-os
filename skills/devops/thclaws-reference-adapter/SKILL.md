---
name: thclaws-reference-adapter
description: Reference-only Hermes adapter for thClaws, a local-first Rust AI agent workspace/harness; supports provenance, feature/risk reporting, and gated adoption planning without installing, running, or granting tools to thClaws.
version: 0.1.0
author: Hermes Agent
metadata:
  hermes:
    tags: [thclaws, external-harness, agent-workspace, hermes-os, governance, reference-only]
    related_skills: [external-agent-skill-radar, hermes-learning-manual-ingest-workflow, omx-coding-agent]
---

# thClaws Reference Adapter

Use this skill when Boss asks about thClaws adoption, installation readiness, feature mapping, or whether thClaws should be used alongside Hermes OS.

## Safety stance

This adapter is **reference-only** by default.

It may:
- Read local study/report artifacts.
- Report thClaws version/provenance from the previously studied snapshot.
- Summarize features, risks, and Hermes OS adoption phases.
- Prepare approval-gated install/build/smoke plans.

It must not, unless Boss gives a separate explicit approval for that scope:
- Install thClaws.
- Build thClaws.
- Run thClaws GUI/CLI/one-shot/team modes.
- Pass provider credentials or secrets to thClaws.
- Import thClaws skills/plugins into Hermes automatically.
- Start MCP servers or external processes through thClaws.
- Let thClaws mutate production repos, deploy infra, push, merge, or edit secrets.

## Provenance from validated study

```text
Canonical repo: https://github.com/thClaws/thClaws
Studied snapshot: c69986b4f172879f9a926f6a7f0c43c4e5ec3af7
Observed current version: v0.3.3
Social post discussed: v0.3.1
Study report: /tmp/thclaws_hermes_os_report.md
Fact IDs: 230, 231
Learning ID: policy-0001-candidate-0028
```

## GPT / OpenAI support verification workflow

When Boss asks whether thClaws can use GPT like OMX, distinguish two questions:

1. **Code support** — does the thClaws build list OpenAI / OpenAI-compatible providers?
2. **Local readiness** — does the current machine have usable OpenAI credentials/config for thClaws?

Validated pattern from this conversation:
- README advertises **OpenAI** as a supported multi-provider option.
- `thclaws-safe` now starts from `gpt-5.4-mini` and, when `OPENAI_API_KEY` is absent, prefers a local OpenAI-compatible endpoint before falling back to `ollama/qwen3.5:cloud`.
- If no credentials are present, say **supported in code but not configured locally** unless a local OpenAI-compatible endpoint or Ollama fallback is reachable.
- In the patched release, the OpenAI/OpenAI Responses path can honor `OPENAI_BASE_URL` for an OpenAI-compatible endpoint, including a local no-auth mock server.
- Reusable smoke pattern: unset `OPENAI_API_KEY`, point `THCLAWS_LOCAL_OPENAI_BASE_URL` at a local `/v1/chat/completions` endpoint (with `THCLAWS_LOCAL_OPENAI_PROBE_URL` on `/v1/models`), and run `thclaws-safe --model gpt-5.4-mini "Reply exactly: ..."`; a matching exact-response output proves the keyless local OpenAI path works when the endpoint itself does not require auth.
- If the local OpenAI probe is unreachable, the wrapper falls back to `ollama/qwen3.5:cloud` and logs `fallback_reason=missing OPENAI_API_KEY -> using local Ollama fallback`.
- If a run still CONNECTs to `api.openai.com:443` instead of the configured base URL, treat it as a regression in provider/base-URL plumbing and inspect the OpenAI provider path before claiming success.

Recommended local readiness checks:
- `compgen -e | grep -E '^(OPENAI|ANTHROPIC|OPENROUTER|THCLAWS)'`
- probe standard config locations for thClaws settings / env files:
  - `~/.config/thclaws/settings.json`
  - `~/.thclaws/settings.json`
  - `~/.config/thclaws/.env`
  - `~/.thclaws/.env`
- if credentials are absent, do not claim GPT is ready; report that manual OpenAI setup is still required.

Reporting rule:
- Answer **yes** to “can thClaws use GPT?” only when the build/runtime/provider path supports OpenAI *and* Boss has valid credentials configured.
- Otherwise answer: **“supported by thClaws, but not ready on this machine yet.”**

## Positioning

```text
Hermes OS = Boss-facing coordinator, policy gate, memory/fact/learning layer, router/fleet controller
thClaws   = external local-first Rust agent workspace/harness with GUI, CLI, skills, MCP, KMS, subagents, and Agent Teams
Adapter   = safety wrapper that keeps thClaws outside Hermes OS core
```

Do not recommend replacing Hermes OS with thClaws. Recommend using thClaws as an optional external workspace/team backend only after gates pass.

## Recommended adoption phases

1. **Reference-only adapter** — current phase. No install/run.
2. **Install/build readiness gate** — only after Boss approves; check toolchain, dependencies, version, license, and build path.
3. **Local smoke gate** — run only non-provider `--help`/`--version`/dry smoke where possible; no secrets.
4. **Workspace wrapper** — optional controlled commands, allowlisted repo path, no push/merge/deploy.
5. **Team backend evaluation** — only in disposable repo/worktree; audit logs required.
6. **Optional Hermes OS router integration** — thClaws as opt-in backend, never default autonomous executor.

## Risk checklist before any execution approval

- Repo/version changed since study?
- Changelog reviewed?
- Dependencies reviewed enough for local build?
- No credentials/secrets passed?
- Repo target is disposable or explicitly approved?
- Command is allowlisted and RTK-wrapped?
- Audit log path prepared?
- Rollback/cleanup plan exists?

## Helper scripts

Linked helper scripts may be available under `scripts/`.

Current helper scripts:

```bash
python3 ~/.hermes/skills/devops/thclaws-reference-adapter/scripts/thclaws_adapter_report.py
python3 ~/.hermes/skills/devops/thclaws-reference-adapter/scripts/thclaws_readiness_gate.py
```

When using Hermes `terminal`, Boss requires explicit RTK wrapping:

```bash
rtk run "python3 ~/.hermes/skills/devops/thclaws-reference-adapter/scripts/thclaws_adapter_report.py"
rtk run "python3 ~/.hermes/skills/devops/thclaws-reference-adapter/scripts/thclaws_readiness_gate.py"
```

`thclaws_readiness_gate.py` writes:

```text
~/.hermes/database/thclaws-adapter/phase2_readiness.json
~/.hermes/database/thclaws-adapter/phase2_readiness.md
```

Phase 3 helper:

```bash
rtk run "python3 ~/.hermes/skills/devops/thclaws-reference-adapter/scripts/thclaws_phase3_build_probe.py"
```

Writes:

```text
~/.hermes/database/thclaws-adapter/phase3_build_probe.json
~/.hermes/database/thclaws-adapter/phase3_build_probe.md
~/.hermes/database/thclaws-adapter/phase3_cargo_check.log
```

It runs compile-only `cargo check --locked -p thclaws-core --bins --lib`; it does not run thClaws binaries, GUI, prompts, teams, MCP/plugins, or pass secrets. Latest observed blocker: `pkg-config`/`libdbus-1-dev` missing for transitive `libdbus-sys` via keyring/secret-service on Linux.

## Phase 3 remote-continuation lessons

When Phase 3 build probe fails on missing Linux system prerequisites:

```text
pkg-config command could not be found
libdbus-sys requires dbus-1 via pkg-config
likely packages: pkg-config libdbus-1-dev
```

Use this safe sequence:

1. Do **not** keep retrying the same `cargo check` until prerequisites are installed.
2. Ask for/record explicit Boss approval before system package install.
3. Try only RTK-wrapped install commands, for example:

```bash
rtk run "sudo apt-get update && sudo apt-get install -y pkg-config libdbus-1-dev"
```

4. If sudo fails with `sudo: a terminal is required to read the password`, stop; do not ask Boss to send a sudo password in chat. Mark Phase 3 blocked until Boss can run the command interactively or provides a secure sudo-capable remote path.
5. If Boss is away from the computer, remote options may help but must be treated as access troubleshooting, not build execution:
   - AnyDesk ID can sometimes be read from Windows config under `/mnt/c/ProgramData/AnyDesk/service.conf` or `system.conf`; do not print passwords/secrets.
   - If AnyDesk says it is waiting for the remote side to accept, unattended access is not available and someone at the PC must accept.
   - Tailscale IPs from the mobile app may refer to the phone itself, not the Windows/WSL host; verify device name before probing.
   - If WSL lacks a Tailscale interface, route probes to `100.x.y.z` may time out even when the phone is connected.
   - `hermes-workspace-launcher` can expose Hermes Workspace via tunnels, but it does not solve sudo/password requirements by itself.
6. After Boss installs prerequisites interactively, rerun only the same compile-only Phase 3 helper before moving to any thClaws binary/GUI/team execution gate.

## Phase 3 build blocker playbook

If `cargo check --locked -p thclaws-core --bins --lib` fails with `pkg_config failed` / `pkg-config command could not be found` / `libdbus-sys`:

1. Confirm without guessing:

```bash
rtk run "command -v pkg-config || true; dpkg -s pkg-config libdbus-1-dev 2>/dev/null | sed -n '1,120p' || true"
```

2. If packages are missing, install only after explicit Boss approval because this mutates system packages:

```bash
rtk run "sudo apt-get update && sudo apt-get install -y pkg-config libdbus-1-dev"
```

3. If sudo fails with `sudo: a terminal is required to read the password`, do **not** ask Boss to send the sudo password in chat. Ask Boss to run the apt command interactively on the machine/WSL or through a pre-existing remote access path, then rerun the Phase 3 helper.

4. If Boss wants future package installs without being at the PC, use a narrow root-owned helper rather than broad passwordless sudo. Bootstrap pattern:

```text
/usr/local/sbin/hermes-admin
/etc/sudoers.d/hermes-admin containing:
<linux-user> ALL=(root) NOPASSWD: /usr/local/sbin/hermes-admin *
```

The initial helper may be fixed allowlist only, for example `list-approved` and `install-thclaws-deps` for `pkg-config libdbus-1-dev`. If `/usr/local/sbin/hermes-admin` is missing, Boss must create/install it interactively once with `sudo` at the PC; Hermes cannot create it via chat without a sudo-capable path.

If extending the helper later to support `request-package`, `approve-package`, `install-approved`, `list-pending`, and `audit`, prepare the upgraded script in `/tmp/hermes-admin.new` and syntax-check it, but expect self-upgrade to fail unless the old helper explicitly supports upgrade. Have Boss run one interactive command such as:

```bash
sudo bash -n /tmp/hermes-admin.new && sudo cp /usr/local/sbin/hermes-admin /usr/local/sbin/hermes-admin.bak && sudo install -m 0755 -o root -g root /tmp/hermes-admin.new /usr/local/sbin/hermes-admin && sudo /usr/local/sbin/hermes-admin list-approved
```

Keep approvals/audit package-scoped and validate package names with a restrictive regex; never add broad `NOPASSWD: ALL`.

5. If Boss has AnyDesk installed on Windows but forgot the ID, the ID can often be read from WSL without exposing passwords:

```bash
rtk run "python3 - <<'PY'
from pathlib import Path
import re
for p in [Path('/mnt/c/ProgramData/AnyDesk/service.conf'), Path('/mnt/c/ProgramData/AnyDesk/system.conf')]:
    if p.exists():
        text = p.read_text(encoding='utf-8', errors='ignore')
        for m in re.finditer(r'(?i)(?:ad\\.anynet\\.id|^id)\\s*=\\s*([0-9]{6,12})', text, re.M):
            print(m.group(1))
PY"
```

Only report the AnyDesk ID; do not print or store password/hash/token-like config values.

## Phase 4/5 CLI smoke lessons

After Phase 3 compile passes, use gated smoke tests in this order:

1. **Phase 4 help/version smoke** — safe without provider secrets or prompt execution:

```bash
rtk run "cd /tmp/thclaws-study && cargo run --locked -p thclaws-core --bin thclaws-cli -- --version && cargo run --locked -p thclaws-core --bin thclaws-cli -- --help"
```

Observed successful output from studied snapshot included:

```text
thclaws-cli 0.3.3
revision: c69986b (main)
```

2. **Phase 5 real-run prompt smoke** — requires separate Boss approval because it executes the agent/provider path. Use a disposable workspace, no GUI/team/MCP/plugins, short timeout, max-iterations 1, and disallow mutation/network/search tools where possible:

```bash
rtk run "timeout 90s /tmp/thclaws-study/target/debug/thclaws-cli --print --model ollama/gemma4:26b --permission-mode ask --max-iterations 1 --disallowed-tools Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch 'Reply exactly: THCLAWS_REAL_SMOKE_OK'"
```

Successful expected output:

```text
THCLAWS_REAL_SMOKE_OK
```

Ollama-specific finding:

- Native thClaws Ollama provider uses `http://localhost:11434/api/chat` by default and does **not** use an API key.
- Configure native Ollama with `--model ollama/<model>` and optional `OLLAMA_BASE_URL` only when Ollama is not on localhost.
- If the default provider errors with `no API key found for provider 'anthropic' — set ANTHROPIC_API_KEY`, switch explicitly to a local Ollama model if available rather than trying to set an Ollama API key.
- Validate Ollama availability with:

```bash
rtk run "curl -sS http://localhost:11434/api/tags | python3 -m json.tool | sed -n '1,80p'"
```

Known artifact paths from Boss host:

```text
~/.hermes/database/thclaws-adapter/phase4_cli_smoke.md
~/.hermes/database/thclaws-adapter/phase5_real_run_smoke.md
```

### Boss-approved native Ollama cloud models

Boss provided and validated these native Ollama cloud models for thClaws:

```text
kimi-k2.5:cloud     — Multimodal reasoning with subagents
glm-5.1:cloud       — Reasoning and code generation
qwen3.5:cloud       — Reasoning, coding, and agentic tool use with vision
minimax-m2.7:cloud  — Fast, efficient coding and real-world productivity
```

Boss selected `qwen3.5:cloud` as the default thClaws native Ollama model. Use it as:

```bash
--model ollama/qwen3.5:cloud
```

Coding benchmark lesson from Hermes-OS update-auditor classifier task:

```text
qwen3.5:cloud       passed visible pytest + hidden tests in 91s; best thClaws coding/verification choice.
glm-5.1:cloud       timed out/failed on the same coding benchmark; do not use for correctness-critical implementation without retesting.
minimax-m2.7:cloud  was fast but failed visible pytest while self-reporting success; do not trust self-report without tests.
```

Routing rule after this benchmark:
- Use thClaws `qwen3.5:cloud` for safe controlled verification, secondary implementation, or Hermes-OS external worker tasks.
- Prefer OMX/Codex `gpt-5.4-mini` with workspace-write sandbox for primary correctness-critical implementation when available.
- Always require real tests/hidden tests; never accept thClaws self-report as proof of correctness.

A reusable 4-model smoke harness pattern:

1. Create a disposable workspace under `/tmp/thclaws-4model-smoke-<UTC>`.
2. For each model, run a one-turn exact-response prompt through `thclaws-cli --print`.
3. Keep `--permission-mode ask`, `--max-iterations 1`, and disallow mutation/network/search tools:

```bash
rtk run "timeout 150s /tmp/thclaws-study/target/debug/thclaws-cli --print --model ollama/<model> --permission-mode ask --max-iterations 1 --disallowed-tools Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch 'Real smoke test only. Do not call tools. Reply exactly: THCLAWS_REAL_SMOKE_OK'"
```

Observed 4/4 pass on Boss host:

```text
kimi-k2.5:cloud     passed 2.111s
glm-5.1:cloud       passed 0.93s
qwen3.5:cloud       passed 1.416s
minimax-m2.7:cloud  passed 4.209s
```

Report artifacts:

```text
~/.hermes/database/thclaws-adapter/phase5_ollama_4model_smoke_20260426T071941Z.md
~/.hermes/database/thclaws-adapter/phase5_ollama_4model_smoke_20260426T071941Z.json
```

Readiness conclusion: thClaws is ready for controlled non-mutating CLI usage with native Ollama, defaulting to `ollama/qwen3.5:cloud`.

Next approval boundary after Phase 5: any workspace file mutation, team agents, MCP/plugins, GUI use, or production repository access requires a separate Boss approval and a narrow allowlist/audit plan.

## Update-safe production harness pattern

When Boss asks to use thClaws for real work while preserving update safety, do **not** run the mutable upstream checkout directly. Use a current/candidate/releases layout and a wrapper.

### Safe update checklist

Before promoting any new thClaws release, verify:

- version / commit / release source is known
- changelog or release notes were reviewed
- existing config still points to the intended primary and fallback models
- `.thclaws/settings.json` or equivalent local config is preserved
- primary remains `gpt-5.4-mini` when that is the Boss-selected default
- fallback remains `ollama/qwen3.5:cloud` when that is the Boss-selected native Ollama fallback
- OpenAI-compatible custom endpoint behavior still works if the build previously depended on `OPENAI_BASE_URL`
- `hello` path still works end-to-end
- fallback path still works end-to-end
- provider/error logs do not show an unexpected regression to `api.openai.com` or auth failures
- regression tests and smoke tests pass before `current` is repointed

If any of those fail, keep using `current`, fix or re-test in `candidate`, and do not promote.

Boss host implementation created during the validated workflow:

```text
~/.hermes/thclaws/
├── current -> releases/thclaws-c69986b-20260426/
├── candidate/
├── releases/
│   └── thclaws-c69986b-20260426/
├── reports/
├── logs/
├── smoke/
├── state/
└── bin/
    ├── thclaws-safe
    └── thclaws-update-gate
```

### `thclaws-safe` wrapper

Hermes should call only:

```bash
rtk run "$HOME/.hermes/thclaws/bin/thclaws-safe '<prompt>'"
```

Default behavior:

```text
model: ollama/qwen3.5:cloud
permission-mode: ask
max-iterations: 1
disallowed-tools: Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch
logs: ~/.hermes/thclaws/logs/
smoke/default workdirs: ~/.hermes/thclaws/smoke/
```

Verification command:

```bash
rtk run "$HOME/.hermes/thclaws/bin/thclaws-safe 'Reply exactly: THCLAWS_REAL_SMOKE_OK'"
```

Expected output:

```text
THCLAWS_REAL_SMOKE_OK
```

### `thclaws-update-gate` workflow

Use this script to validate upstream changes before promoting them to `current`.

Non-destructive/current verification:

```bash
rtk run "$HOME/.hermes/thclaws/bin/thclaws-update-gate --candidate $HOME/.hermes/thclaws/current --skip-build"
```

Fetch/build/test candidate without promotion:

```bash
rtk run "$HOME/.hermes/thclaws/bin/thclaws-update-gate --refresh"
```

Promote only after gates pass and Boss approves promotion:

```bash
rtk run "$HOME/.hermes/thclaws/bin/thclaws-update-gate --refresh --promote"
```

Gate checks include:

```text
cargo check/build when not skipped
thclaws-cli --version
thclaws-cli --help
required flag compatibility: --print, --model, --permission-mode, --max-iterations, --disallowed-tools, --help, --version
qwen3.5:cloud exact-response real smoke
mutation scan in disposable smoke workspace
report writing under ~/.hermes/thclaws/reports/
```

Observed non-destructive gate report on Boss host:

```text
~/.hermes/thclaws/reports/update_gate_20260426T075816Z.md
~/.hermes/thclaws/reports/update_gate_20260426T075816Z.json
passed: true
promoted: false
candidate/current commit: c69986b4f172879f9a926f6a7f0c43c4e5ec3af7
```

### Update and rollback safety rules

- Never update `~/.hermes/thclaws/current` in place.
- Test upstream in `candidate` first.
- If any gate fails, keep using `current`.
- Promote by creating a release under `releases/` and atomically repointing `current`.
- Rollback is symlink-only:

```bash
rtk run "ln -sfn $HOME/.hermes/thclaws/releases/<previous-release> $HOME/.hermes/thclaws/current && $HOME/.hermes/thclaws/bin/thclaws-safe 'Reply exactly: THCLAWS_REAL_SMOKE_OK'"
```

Keep thClaws update management separate from:

```text
/usr/local/sbin/hermes-admin
/var/lib/hermes-admin/
Hermes OS core
Fact Store / Hermes Learning state
~/.hermes/database/thclaws-adapter/ historical reports
```

## Update-safe production harness pattern

When Boss approves moving thClaws from smoke tests into real controlled usage, do **not** call a mutable upstream checkout directly. Promote only a tested snapshot into a stable runtime layout:

```text
~/.hermes/thclaws/
├── current -> releases/thclaws-<commit>-<date>/
├── candidate/
├── releases/
├── reports/
├── logs/
├── smoke/
├── state/
└── bin/
    ├── thclaws-safe
    └── thclaws-update-gate
```

Operational rules:

- Hermes calls `~/.hermes/thclaws/bin/thclaws-safe`, never `/tmp/thclaws-study/target/...` directly.
- Default production-safe model: `ollama/qwen3.5:cloud`.
- Baseline wrapper guardrails: `--print`, `--permission-mode ask`, `--max-iterations 1`, and `--disallowed-tools Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch`.
- Keep `current` as the last tested release; test upstream updates in `candidate` first.
- `thclaws-update-gate` should check/build candidate, verify `--version`/`--help`, confirm required flags (`--print`, `--model`, `--permission-mode`, `--max-iterations`, `--disallowed-tools`, `--help`, `--version`), run a qwen3.5 smoke expecting `THCLAWS_REAL_SMOKE_OK`, scan workspace mutation, and write reports before any promote.
- Promote only after all gates pass, by copying candidate into `releases/thclaws-<commit>-<date>` and atomically repointing `current`.
- Rollback is symlink-only: repoint `current` to the previous release and rerun `thclaws-safe 'Reply exactly: THCLAWS_REAL_SMOKE_OK'`.

On Boss's host this pattern was implemented with:

```text
~/.hermes/thclaws/current -> ~/.hermes/thclaws/releases/thclaws-c69986b-20260426
~/.hermes/thclaws/bin/thclaws-safe
~/.hermes/thclaws/bin/thclaws-update-gate
```

A non-destructive update-gate verification passed and wrote:

```text
~/.hermes/thclaws/reports/update_gate_20260426T075816Z.md
```

Separation boundary: thClaws repo updates must not modify `/usr/local/sbin/hermes-admin`, `/var/lib/hermes-admin/`, Hermes OS core, Fact Store/Learning state, or historical reports under `~/.hermes/database/thclaws-adapter/`.

## Memory graph/dashboard sync lesson

When updating `~/hermes-workspace/memory-graph/dashboard.html` after new thClaws skills/facts are added, add **both nodes and cross-links**. Adding nodes alone leaves isolated clusters in the D3 graph. Boss explicitly expects thClaws/Hermes OS nodes to cross-link back to Boss Profile and the main Hermes OS/workspace/software graph.

Minimum thClaws/Hermes-OS-related nodes to include:

```text
hermes_admin_helper
thclaws_default_model
thclaws_update_safe
hermes_learning_thclaws
hermes_os_core
enterprise_fleet
cat_hermes_os
cat_external_agents
skill_thclaws_adapter
skill_hermes_learning
skill_hermes_os_integration
skill_rtk_mes
skill_writing_plans
skill_thclaws_update_gate
proj_hermes_os_runtime
proj_thclaws_harness
```

Important cross-links that keep the graph connected to Boss, Hermes OS, workspace, and software clusters:

```text
user_profile -> hermes_os_core
user_profile -> thclaws_default_model
user_profile -> thclaws_update_safe
user_profile -> hermes_learning_thclaws
user_profile -> proj_thclaws_harness
skill_hermes_os_integration -> hermes_os_core
hermes_os_core -> enterprise_fleet
hermes_os_core -> proj_hermes_os_runtime
hermes_os_core -> proj_thclaws_harness
skill_writing_plans -> thclaws_update_safe
skill_writing_plans -> proj_thclaws_harness
cat_software -> skill_thclaws_update_gate
cat_software -> proj_thclaws_harness
hermes_workspace -> proj_thclaws_harness
proj_memory_graph -> proj_thclaws_harness
thclaws_update_safe -> skill_thclaws_update_gate
```

Also connect otherwise-disconnected legacy clusters back to the main graph, for example:

```text
user_profile -> telegram_greeting
brave_api -> cat_research
cat_research -> hermes_workspace
cat_media -> hermes_workspace
cat_mcp -> hermes_os_core
cat_mlop -> hermes_os_core
cat_creative -> hermes_workspace
cat_github -> cat_software
cat_autonomous -> hermes_os_core
```

Run a structural validation after editing: parse node IDs and link triples from `dashboard.html`, assert no duplicate nodes, no duplicate links, no missing link references, no missing required cross-links, and exactly one connected component. Then load the file in the browser and verify rendered circle/link counts plus text presence for `Boss`, `Hermes OS`, and `thClaws`. On Boss's host after the final sync, validation reported 58 nodes, 80 links, 0 missing references, 0 isolated nodes, 1 connected component, and browser rendering showed 58 circles and 80 links.

## Acceptance criteria for this reference adapter

- Skill loads via `skill_view("thclaws-reference-adapter")`.
- Helper report script runs without installing/building/running thClaws.
- Output includes provenance, safety stance, recommended next gate, and local report path.
- Fact Store and Hermes Learning record that Boss approved Phase 1 reference adapter only, not thClaws execution.
