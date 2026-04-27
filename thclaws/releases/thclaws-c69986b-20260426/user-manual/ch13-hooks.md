# Chapter 13 — Hooks

Hooks are shell commands that fire on agent lifecycle events. They're
how you plug thClaws into your existing tooling: log every tool call,
send a notification when a session ends, block commits until a test
passes.

## Events

| Event | Fires when | Env vars exposed |
|---|---|---|
| `pre_tool_use` | Right before a tool runs | `THCLAWS_TOOL_NAME`, `THCLAWS_TOOL_INPUT` |
| `post_tool_use` | After a tool returns successfully | `THCLAWS_TOOL_NAME`, `THCLAWS_TOOL_OUTPUT` |
| `post_tool_use_failure` | After a tool errors | `THCLAWS_TOOL_NAME`, `THCLAWS_TOOL_ERROR` |
| `permission_denied` | User types `n` on a tool prompt | `THCLAWS_TOOL_NAME` |
| `session_start` | When a session begins | `THCLAWS_SESSION_ID`, `THCLAWS_MODEL` |
| `session_end` | On `/quit` or window close | `THCLAWS_SESSION_ID`, `THCLAWS_MODEL` |
| `pre_compact` | Before history compaction | — |
| `post_compact` | After compaction finishes | — |

## Configuring hooks

In `.thclaws/settings.json` (project) or
`~/.config/thclaws/settings.json` (user):

```json
{
  "hooks": {
    "pre_tool_use":  "echo \"tool: $THCLAWS_TOOL_NAME\" >> /tmp/thclaws.log",
    "post_tool_use": "echo \"done: $THCLAWS_TOOL_NAME\" >> /tmp/thclaws.log",
    "session_start": "osascript -e 'display notification \"thClaws started\"'",
    "session_end":   "osascript -e 'display notification \"thClaws ended\"'"
  }
}
```

Each value is a shell snippet run via `/bin/sh -c`. Env vars are
available exactly as documented above.

## Practical recipes

### Log every bash command to a file

```json
{
  "hooks": {
    "pre_tool_use": "[ \"$THCLAWS_TOOL_NAME\" = Bash ] && echo \"[$(date)] $THCLAWS_TOOL_INPUT\" >> ~/.thclaws-bash.log"
  }
}
```

### Desktop notification on turn complete

```json
{
  "hooks": {
    "session_end": "notify-send 'thClaws' 'Session done'"
  }
}
```

macOS: replace with `osascript -e 'display notification "Session done" with title "thClaws"'`.

### Auto-commit after every successful edit

```json
{
  "hooks": {
    "post_tool_use": "[ \"$THCLAWS_TOOL_NAME\" = Edit -o \"$THCLAWS_TOOL_NAME\" = Write ] && git add -A && git commit -m 'thclaws: edit' --no-verify"
  }
}
```

(Add `--no-verify` cautiously — it skips pre-commit hooks.)

### Ping a webhook on permission denial

```json
{
  "hooks": {
    "permission_denied": "curl -s -X POST -H 'Content-Type: application/json' -d \"{\\\"tool\\\": \\\"$THCLAWS_TOOL_NAME\\\"}\" https://hooks.example.com/denied"
  }
}
```

## Failure handling

Hooks that exit with a non-zero status print a warning to stderr but
don't stop the agent. They run in the same cwd as thClaws, so file
paths in the script are relative to the sandbox root. Long-running
hooks block the turn — keep them fast or background them
(`command &`).

## Debugging

```bash
thclaws --cli --verbose
```

Verbose mode prints each hook invocation before running it.

## What hooks aren't

Hooks **can't mutate** the tool call — they're observers. To block a
tool, use the `permissions.deny` list (Chapter 5). To rewrite a tool
input, the model has to do it.
