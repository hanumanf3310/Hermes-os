---
name: rtk-mes
description: Enforce RTK token compression on ALL terminal commands — CLI and Telegram. Load this skill to guarantee every command goes through RTK proxy with 60-90% token savings.
category: devops
tags: [rtk, token-optimization, cli, telegram, terminal, enforcement]
---

# RTK-MES Skill

## Purpose

**Enforce RTK compression on ALL terminal commands** — both CLI and Telegram. Every command executed through Hermes terminal tool is wrapped with `rtk` proxy, reducing LLM token consumption by 60-90%.

## Usage

```
/rtk-mes status    — Check if RTK is active and show token savings
/rtk-mes on        — Enable RTK wrapping (default)
/rtk-mes off       — Disable RTK wrapping
/rtk-mes gain      — Show detailed token savings report
```

## How It Works

RTK wrapping is effective only when the runtime environment is configured for it.
Verify that the `rtk` binary exists and that `HERMES_RTK_WRAP=1` is set before assuming commands are being compressed.

## Architecture

RTK wrapping is applied at 3 levels:

```
1. base.py _wrap_command()     → ALL backends (docker/ssh/modal/etc)
2. local.py _run_bash()        → local foreground
3. process_registry spawn_local() → local background
```

## Configuration

```bash
HERMES_RTK_WRAP=1   # Enable RTK wrapping for future sessions
HERMES_RTK_WRAP=0   # Disable
```

## Token Savings

```
rtk gain
─────────────────────────────────────────
Tokens saved:      40-90% on common commands
Supported:         ls, git, find, grep, 
                   docker ps, npm list, etc.
```

## For Telegram

When Boss runs commands via Telegram, RTK compresses output automatically — same token savings as CLI.

## Notes

- RTK is idempotent — no double-wrapping
- Requires: `rtk` binary in PATH (v0.37.1+)
- Skill auto-enables RTK on load

## Hermes Terminal Invocation (MANDATORY)

Boss requires **every** Hermes `terminal` tool call to be explicitly wrapped with RTK. Do not call `bash -lc`, `python`, `git`, `npm`, `pytest`, `codex`, `omx`, or any shell command directly through `terminal`.

Required form:

```bash
rtk run "<your full shell command>"
# example
rtk run "cd ~/workspace/enterprise_agent_fleet/tests && python3 test_phase2_main_agents.py"
```

Direct RTK subcommands are allowed when applicable (`rtk ls`, `rtk git`, etc.), but `rtk run "..."` is the default.

Forbidden forms in Hermes terminal calls:

```bash
bash -lc '<command>'
python3 script.py
git status
npm test
rtk '<full shell command>'
```

The quoted `rtk '<full shell command>'` pattern can fail with `No such file or directory` because RTK interprets the quoted string as a command name, not a shell command.

Only bypass RTK if `rtk` is unavailable/broken and Boss explicitly approves the temporary bypass.

## Troubleshooting

- If `rtk` appears missing, verify first:
  - `which rtk`
  - `rtk --version`
  - `echo $PATH`
- If `which rtk` succeeds but command execution fails, switch to `rtk run "..."` form.
- If policy requires RTK wrapping but environment is broken, pause and request explicit user approval before temporary bypass.
- When checking Hermes OS or similar runtime claims, do not equate a successful status command with a live daemon/process. Verify process/service evidence separately (e.g. `ps`, `systemctl`, or equivalent) before stating that the system is actively running.
