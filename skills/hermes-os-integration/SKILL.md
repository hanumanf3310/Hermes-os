---
name: hermes-os-integration
description: Hermes OS integration skill - Auto-routes tasks to Enterprise Agent Fleet when in hermes_os mode. Safe, non-invasive, and version-independent.
category: hermes-os
author: hanuman3310
version: 1.0.0
---

# Hermes OS Integration Skill

## Overview

This skill provides seamless integration between Hermes Agent and Enterprise Agent Fleet
through Hermes OS mode. It auto-detects when Hermes OS is active and routes
tasks accordingly.

**Philosophy**: Everything routes through Hermes OS. Boss never needs to know
whether Hermes or Fleet handles the task.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           Hermes Gateway (Telegram/Discord)                 │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
              ┌──────────────────────┐
              │  hermes-os skill    │
              │  (this module)      │
              └──────────┬───────────┘
                         ↓
           ┌──────────────────────────┐
           │  HermesOS Bridge       │
           │  ~/.hermes/os/         │
           └──────────┬─────────────┘
                      ↓
         ┌──────────────────────────────┐
         │  HermesOS Core             │
         │  (hermes_os.py)            │
         └──────────┬─────────────────┘
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
┌───────┐      ┌────────┐     ┌────────┐
│Hermes │      │ Fleet  │     │ Router │
│Direct │      │(7M+21S)│     │ Core   │
└───────┘      └────────┘     └────────┘
```

## Auto-Detection Flow

1. Skill loads on Hermes startup
2. Check `~/.hermes/state/hermes-os.json`
3. If mode == "hermes_os": Activate bridge
4. All commands prefixed with `/` or complex tasks auto-route

## Commands

| Command | Description |
|---------|-------------|
| `hermes-os` | Show OS status |
| `hermes-os status` | Detailed status |
| `hermes-os fleet` | Fleet health |
| `fleet "task"` | Route task to Fleet |
| `fleet plan "task"` | Dry run |
| `fleet run "task"` | Execute task |

**Note**: Commands do NOT use `/` prefix in this system.

## Auto-Routing

Messages are automatically analyzed:

- **Simple tasks** → Hermes direct (file, search, calendar)
- **Complex tasks** → Fleet orchestrated (multi-step, multi-division)
- **Safety-critical** → Fleet + Safety Gate enforced

## Configuration

```yaml
# ~/.hermes/config.yaml (auto-generated)
hermes_os:
  auto_route: true
  safety_threshold: 0.7
  complexity_threshold: 0.6
  rtk_enabled: true
```

## Integration Points

### Entry Points
- `SKILL.md`: Documentation
- `skill.py`: Main skill module
- `bridge.py`: HermesOS bridge wrapper

### Dependencies
- `~/.hermes/os/hermes_os.py`: Core OS
- `~/.hermes/os/fleet/`: Fleet modules
- `~/.hermes/os/core/`: Router, Formatter

## Status

| Component | Status |
|-----------|--------|
| Core OS | ✅ Ready |
| Fleet | ✅ Ready (7M+21S) |
| Router | ✅ Ready |
| Formatter | ✅ Ready |
| Bridge | 🔄 In Progress |
| CLI Integration | ✅ Ready |
| Auto-load Config | 🔄 In Progress |

## Usage Examples

```
Boss: "สร้าง API มี auth"
→ Hermes OS → Router → ⚡ Hermes Direct
→ Result in Telegram

Boss: "Build complete system with docs"
→ Hermes OS → Router → 🌐 Fleet Multi
→ Fleet (DIV-02 + DIV-04) → Result

Boss: "fleet plan สร้าง database migration"
→ Dry run → Show plan → Ask confirm
```

## Safety

- Non-invasive: No Hermes core modification
- Reversible: Delete skill = remove integration
- Isolated: Errors in skill don't break Hermes
- Version independent: Works with any Hermes version

## Future Improvements

- [ ] Natural language trigger (no / command needed)
- [ ] LLM learns when to use Fleet automatically
- [ ] Boss preference memory (often uses Fleet for X)
