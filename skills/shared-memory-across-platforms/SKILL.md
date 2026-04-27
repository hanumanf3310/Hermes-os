---
name: shared-memory-across-platforms
description: Configure Hermes Agent so memory and user profile are truly shared across CLI, Telegram, and other messaging platforms. Solves the common issue where memory appears saved but is not retrieved correctly on different platforms.
version: 1.0.0
author: Hermes Agent
tags: [memory, telegram, multi-platform, configuration, hermes]
---

# Shared Memory Across Platforms

## The Problem

When you save memory or user profile using the `memory` tool, it appears to work in the current session. But when you switch to Telegram (or another platform), the agent gives wrong answers about things you saved — because **memory is baked into each session system_prompt at creation time**, and later memory updates do not propagate to existing sessions.

## How Memory Works in Hermes

Memory is NOT a database that gets queried at runtime. Instead:

1. When a session starts (CLI, Telegram DM, etc.), Hermes builds a `system_prompt`
2. The `system_prompt` includes: personality, memory block, and user profile block
3. This system_prompt is stored in the session JSON file and stays FIXED for that session
4. When you call `memory(action='add')` in ANY session, it updates the memory block for THAT session system_prompt only
5. Other sessions already running (or started later) will not see the update unless they rebuild their system_prompt

## Root Cause

From `state.db` investigation:
- There is NO separate `memory` or `user_profile` table
- Memory content lives ONLY inside each session `system_prompt` field
- Each platform/chat creates its own session with its own system_prompt snapshot

So if you save memory in CLI session A, then later start a Telegram session B, session B system_prompt was built BEFORE the memory was saved — so it does not have it.

## Solutions

### Solution 1: Restart the Telegram Session (Quick Fix)

When you start a NEW Telegram session, it will build a fresh system_prompt with the LATEST memory.

**How to trigger a new Telegram session:**
- Send `/new` or `/reset` in Telegram chat
- Or: delete the old session file so Hermes creates a new one

List Telegram sessions:
```
rtk ls -la ~/.hermes/sessions/session_*telegram*.json
```

Delete old Telegram session to force fresh start:
```
rtk rm ~/.hermes/sessions/session_20260419_195943_6f4694f5.json
```

After deletion, when user messages on Telegram again, Hermes will create a NEW session with current memory.

### Solution 2: Use a Shared Memory Backend (Proper Fix)

Install a memory plugin that stores memory in a central database, so ALL sessions (old and new) query from the same source.

**Available plugins (from `hermes memory status`):**

| Plugin | Type | Free? |
|--------|------|-------|
| `honcho` | API key or local | Free local |
| `mem0` | API key or local | Free tier |
| `hindsight` | API key or local | Free local |
| `holographic` | Local only | Free |

**Recommended: Honcho (free, local, no API key needed)**

```
hermes honcho setup
```

Or use holographic (simplest, no setup):
```
hermes memory setup
# Select "holographic" when prompted
```

After configuring a shared memory backend:
1. Memory is stored in a central location (not per-session)
2. Every new session (CLI or Telegram) queries the same memory store
3. Old sessions still have stale memory in their system_prompt — but new sessions will be fresh

### Solution 3: Manual Memory Sync (Emergency)

If you cannot restart sessions or setup a backend:

1. Call `session_search` to find your saved memory
2. Then re-save the memory in the current session

## Verification Steps

After applying any solution:

1. **Save a test memory** in CLI:
```
memory(action='add', target='memory', content='TEST: My name is [YourName] - saved at [timestamp]')
```

2. **Start a NEW Telegram session** (delete old session file first)

3. **Ask from Telegram**: "What is my test memory?"

4. **Expected**: Correct answer with the test content
5. **If wrong**: The solution did not work — try a different approach

## Session Management Commands

```
hermes sessions list
hermes sessions delete <session_id>
hermes sessions prune --older-than 7
```

## Quick Diagnosis

To check if memory is truly shared, compare system_prompt memory sections between sessions. If the memory content differs between sessions, they have stale snapshots.

## Summary Checklist

- [ ] Understood: memory is baked into each session system_prompt
- [ ] Understood: new memory saves do not update existing sessions
- [ ] Option A: Delete old Telegram session, new Telegram session gets fresh memory
- [ ] Option B: Setup shared memory backend (honcho/mem0) for dynamic memory
- [ ] Verified: Test memory survives platform switch
