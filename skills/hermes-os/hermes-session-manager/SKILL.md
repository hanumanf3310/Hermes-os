---
name: hermes-session-manager
title: Hermes Session Manager
version: 1.0.0
description: |
  Session state management for Hermes inspired by Claude OS.
  Provides 4-field session persistence, auto-category detection,
  and seamless integration with Hermes startup workflow.
tags:
  - session-management
  - memory
  - cli
  - workflow
requires_tools:
  - terminal
  - file
triggers:
  - session
  - checkpoint
  - continue
  - resume
  - pending
  - task
---

# Hermes Session Manager Skill

## Overview

Session Manager ช่วยให้ Hermes **จำว่า Boss กำลังทำอะไรค้างไว้** เหมือน Claude OS ที่ให้ AI มีความจำระยะยาว

### Features

- **4-Field Session State**: `last_task`, `last_branch`, `stopped_at`, `one_liner`
- **Auto-Category Detection**: จับคำพูดภาษาไทย/อังกฤษอัตโนมัติ
- **Pending Items**: ติดตามงานที่ต้องทำ
- **Freshness Detection**: บอกว่า session ยังใหม่อยู่หรือไม่ (< 24 ชม.)
- **CLI Integration**: `hermes-session` command

## Quick Start

```bash
# Save current session
hermes-session save "Fix auth bug" "Need rate limiting" "feature/auth" "~/myproject"

# View current session
hermes-session

# Add pending task
hermes-session add-pending "Write tests for login"

# Complete pending task
hermes-session complete "Write tests for login"

# Clear session
hermes-session clear
```

## Architecture

```
User Message
    ↓
[Category Detector] ──→ Auto-detect category (thai/en patterns)
    ↓
[Session Manager] ──→ Load/Save session state
    ↓
[Hermes Startup] ──→ "Continue where we left off?"
```

## File Structure

```
~/.hermes/
├── session-state.json          # Current session
├── session-history/            # (future) Historical sessions
└── triggers/
    └── memory_triggers.yaml    # Auto-detection patterns
```

## Session State Format

```json
{
  "session_id": "sess-20260426-194427",
  "last_task": "Fix auth bug",
  "last_branch": "feature/auth",
  "stopped_at": "2026-04-26T19:44:27",
  "one_liner": "Need rate limiting",
  "project_context": {
    "repo": "/home/hanuman3310/myproject",
    "active_files": ["src/auth.ts"]
  },
  "pending_items": [
    "Write tests for login",
    "Update documentation"
  ]
}
```

## Category Detection Rules

| Category | Thai Patterns | English Patterns |
|----------|---------------|------------------|
| user | ฉันชอบ, ผมชอบ | I prefer, I like |
| project | โปรเจกต์นี้, project นี้ | This project, We use |
| tech | API, ฟังก์ชัน, database | API, Function, Code |
| security | password, token, secret | Password, Token, Secret |
| environment | ทำงานอยู่, WSL | Using WSL, Environment |

## Hermes Integration

### On Startup (Auto)

```python
from core.session_state import SessionManager

manager = SessionManager()
state = manager.load()

if state.is_fresh:
    print(f"📋 Last session: {state.last_task}")
    print(f"   Status: {state.one_liner}")
    # Ask: Continue? (Yes/No/New)
```

### Manual Checkpoint

```python
# When Boss says "done" or task complete
manager.create_checkpoint(
    task="Current task name",
    one_liner="Quick summary"
)
```

## CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| `hermes-session` | Show current session |
| `hermes-session save <task> <one-liner> [branch] [repo]` | Create checkpoint |
| `hermes-session clear` | Clear all state |
| `hermes-session pending` | List pending items |
| `hermes-session add-pending <item>` | Add to pending |
| `hermes-session complete <item>` | Mark as done |
| `hermes-session show` | Raw JSON output |

## Examples

### Example 1: Starting Work

```
Boss: /session save "Refactor auth module" "Extract JWT logic to separate file"

Hermes: ✅ Saved session: sess-20260426-201500
        📋 Last Task: Refactor auth module
           Status: Extract JWT logic to separate file
```

### Example 2: Auto-Detect on Conversation

```
Boss: "ฉันชอบให้ตอบสั้นๆ"

Hermes: 💾 Auto-saved: 'ชอบให้ตอบสั้นๆ' (user, confidence: 95%)
```

### Example 3: Continue Session

```
[Boss starts new chat]

Hermes: 📋 เจอ session ที่ค้างไว้ (2 hours ago)
        Task: Refactor auth module
        Status: Extract JWT logic to separate file
        ⏳ Pending: 2 items

        Continue where we left off? [Yes/No/New Task]
```

## Future Enhancements

- [ ] Trust score for session items
- [ ] Git integration (auto-detect branch/repo)
- [ ] Session history / timeline
- [ ] Integration with Knowledge Lifecycle Engine
- [ ] File change tracking

## Testing

```bash
# Test category detection
python core/category_detector.py

# Test session state
python core/session_state.py

# Test CLI
./bin/hermes-session save "Test" "Testing"
./bin/hermes-session
```

## Dependencies

- Python 3.8+
- Standard library only (no external deps)

## Author

Hermes OS - Phase 1 Enhancement
