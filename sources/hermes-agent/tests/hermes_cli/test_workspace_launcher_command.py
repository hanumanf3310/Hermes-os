import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from hermes_cli.commands import resolve_command, telegram_bot_commands


def test_hermes_workspace_command_registry_and_telegram_alias():
    cmd = resolve_command("hermes-workspace")
    assert cmd is not None
    assert cmd.name == "hermes-workspace"
    assert resolve_command("hermes_workspace").name == "hermes-workspace"
    assert resolve_command("workspace").name == "hermes-workspace"

    telegram_names = {name for name, _ in telegram_bot_commands()}
    assert "hermes_workspace" in telegram_names
    assert "hermes-workspace" not in telegram_names


def test_workspace_launcher_defaults_to_up(monkeypatch, tmp_path):
    import hermes_cli.workspace_launcher as launcher_mod
    from hermes_cli.workspace_launcher import parse_workspace_launcher_request, run_workspace_launcher

    fake_launcher = tmp_path / "hermes-workspace"
    fake_launcher.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(launcher_mod, "_WORKSPACE_LAUNCHER", fake_launcher)

    calls = []

    def fake_run(args, capture_output, text, timeout, check):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="STATUS OK", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    request, error = parse_workspace_launcher_request("")
    assert error is None
    assert request.action == "up"

    result = run_workspace_launcher(request)

    assert calls == [[str(fake_launcher), "up"]]
    assert result.ok is True
    assert result.output == "STATUS OK"


def test_workspace_launcher_rejects_unknown_subcommand():
    from hermes_cli.workspace_launcher import parse_workspace_launcher_request

    request, error = parse_workspace_launcher_request("explode")

    assert request is None
    assert error == "Usage: /hermes_workspace [up|status|down|restart]"


@pytest.mark.asyncio
async def test_gateway_hermes_workspace_handler_uses_launcher(monkeypatch):
    import gateway.run as gateway_run
    from gateway.config import Platform
    from gateway.platforms.base import MessageEvent
    from gateway.session import SessionSource
    from hermes_cli.workspace_launcher import WorkspaceLauncherResult

    runner = object.__new__(gateway_run.GatewayRunner)
    runner.name = "test"
    runner.session_store = None
    runner.config = SimpleNamespace(group_sessions_per_user=True, thread_sessions_per_user=False)
    runner.adapters = {}
    runner.hooks = MagicMock()

    source = SessionSource(
        platform=Platform.TELEGRAM,
        user_id="12345",
        chat_id="67890",
        user_name="Boss",
    )
    event = MessageEvent(text="/hermes_workspace status", source=source)

    calls = []

    def fake_run(request):
        calls.append(request.action)
        return WorkspaceLauncherResult(ok=True, action=request.action, output="🟢 UI: http://localhost:3000")

    monkeypatch.setattr("hermes_cli.workspace_launcher.run_workspace_launcher", fake_run)

    result = await runner._handle_workspace_command(event)

    assert calls == ["status"]
    assert "Hermes Workspace" in result
    assert "http://localhost:3000" in result


def test_active_session_bypass_includes_workspace_commands():
    source = Path("gateway/platforms/base.py").read_text(encoding="utf-8")

    assert '"hermes-workspace"' in source
    assert '"hermes_workspace"' in source
    assert '"workspace"' in source
