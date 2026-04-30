import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from hermes_cli.commands import resolve_command, telegram_bot_commands


def test_hermes_workspace_command_registry_and_telegram_alias():
    cmd = resolve_command("hermes-workspace")
    assert cmd is not None
    assert cmd.name == "hermes-workspace"
    assert resolve_command("hermes_workspace").name == "hermes-workspace"

    telegram_names = {name for name, _ in telegram_bot_commands()}
    assert "hermes_workspace" in telegram_names
    assert "hermes-workspace" not in telegram_names


def test_workspace_launcher_defaults_to_status(monkeypatch):
    from hermes_cli.workspace_launcher import run_workspace_launcher

    calls = []

    def fake_run(args, capture_output, text, timeout):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="STATUS OK", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_workspace_launcher("")

    assert calls == [["hermes-workspace", "status"]]
    assert "STATUS OK" in result


def test_workspace_launcher_rejects_unknown_subcommand():
    from hermes_cli.workspace_launcher import run_workspace_launcher

    result = run_workspace_launcher("explode")

    assert "Usage: /hermes-workspace [up|status|down]" in result


@pytest.mark.asyncio
async def test_gateway_hermes_workspace_handler_uses_launcher(monkeypatch):
    import gateway.run as gateway_run
    from gateway.config import Platform
    from gateway.platforms.base import MessageEvent
    from gateway.session import SessionSource

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

    monkeypatch.setattr(
        "hermes_cli.workspace_launcher.run_workspace_launcher",
        lambda raw_args: f"called:{raw_args}",
    )

    result = await runner._handle_hermes_workspace_command(event)

    assert result == "called:status"
