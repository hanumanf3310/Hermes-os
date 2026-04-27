---
name: hermes-workspace-launcher
description: Launch Hermes Workspace UI and WebAPI with public tunnels (ngrok + Cloudflare) for mobile access. One command to start the full stack.
version: 1.0.0
---

# Hermes Workspace Launcher

Launch the complete Hermes Workspace stack with one command.

## Quick Start

```bash
# Start everything (UI + WebAPI + tunnels)
hermes-workspace up

# Check status
hermes-workspace status

# Stop everything
hermes-workspace down
```

## What It Does

1. ✅ Starts Hermes Workspace UI (vite dev server on port 3000)
2. ✅ Starts Hermes WebAPI (uvicorn on port 8642)
3. ✅ Creates a public tunnel for the UI
4. ✅ Creates a public tunnel for the WebAPI
5. 🎉 Returns both URLs ready for mobile access

## Known Working Topology

- UI: `http://localhost:3000`
- WebAPI: `http://localhost:8642`
- UI tunnel: ngrok works, but on free plan use the auto-generated URL (custom subdomains are paid-only)
- API tunnel: Cloudflare quick tunnel is the most reliable free option

## Exposing the launcher through chat/CLI commands

When the launcher should be reachable from both the CLI and Telegram, add a thin command wrapper rather than duplicating the launch logic in multiple places:

1. Put the actual launch/status logic in a small helper module (for example `hermes_cli/memory_graph.py`) so it can be reused from CLI and gateway handlers.
2. Register a new `CommandDef` in the central `COMMAND_REGISTRY` so the command appears in CLI help and can be resolved by aliases.
3. For Telegram, expose the command with an underscore alias if the canonical name contains hyphens, because Telegram command names only allow lowercase letters, digits, and underscores.
4. Add a dedicated gateway handler that returns the formatted public URL message instead of forwarding the command to the model.
5. Update the slash-command reference docs so the command appears in both the CLI and messaging sections.
6. Add regression tests for:
   - command registration / resolution
   - Telegram alias exposure
   - CLI handler output
   - gateway handler output
7. Keep the user-facing status message plain and compact so it renders reliably in Telegram and other messaging surfaces.

## Verification

Before telling the user it is ready, verify:

```bash
curl -s http://localhost:3000 >/dev/null
curl -s http://localhost:8642/health
```

If both return successfully, the stack is healthy.

## Prerequisites

- `~/hermes-workspace/` - Frontend UI code
- `~/hermes-agent/` - Backend API code  
- `ngrok` - For UI tunnel (free)
- `cloudflared` - For API tunnel (free)
- `pnpm` - For UI dependencies
- `~/.hermes/hermes-agent/venv/bin/python` - Python with uvicorn

## Install

Copy this skill's script to `~/.local/bin/`:

```bash
chmod +x ~/.local/bin/hermes-workspace
```

## Troubleshooting

**Port already in use:**
```bash
hermes-workspace down  # Kill existing processes
hermes-workspace up    # Restart
```

**Backend URL mismatch:**
- The UI expects the WebAPI on `8642` by default
- If you move the backend to another port, update the UI config (`HERMES_API_URL`) accordingly

**Tunnel not responding:**
- Cloudflare tunnel may take 10–15 seconds to propagate
- ngrok free plan does **not** allow custom subdomains
- localtunnel can produce a URL but may fail with `connection refused` depending on network/firewall conditions
- If a tunnel URL was previously created, starting a second one may reuse or conflict with the earlier endpoint

**WebAPI not found:**
- Ensure `~/hermes-agent/webapi/app.py` exists
- WebAPI requires FastAPI dependencies and the Hermes venv Python at `~/.hermes/hermes-agent/venv/bin/python`

## URLs After Launch

| Service | Local | Public |
|---------|-------|--------|
| UI | http://localhost:3000 | https://xxx.ngrok-free.dev |
| API | http://localhost:8642 | https://xxx.trycloudflare.com |
