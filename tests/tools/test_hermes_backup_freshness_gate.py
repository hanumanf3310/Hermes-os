import json
from pathlib import Path

from tools.hermes_backup_freshness_gate import evaluate_backup_freshness, main


def _write(path: Path, text: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_minimal_tree(root: Path, files: list[str], *, prefix: str = "") -> None:
    for rel in files:
        _write(root / prefix / rel, f"{rel}\n")


def test_evaluate_backup_freshness_blocks_when_backup_lacks_policy_files(tmp_path):
    tracked = [
        "cli.py",
        "hermes_cli/hermes_os_format.py",
        "website/docs/reference/merged-hard-gate-policy.yaml",
        "tools/merged_policy_validator.py",
    ]
    dev = tmp_path / "dev"
    live = tmp_path / "live"
    backup = tmp_path / "backup"
    _seed_minimal_tree(dev, tracked)
    _seed_minimal_tree(live, tracked)
    _seed_minimal_tree(backup, ["cli.py"], prefix="sources/hermes-agent")
    _write(backup / "restore" / "MANIFEST.json", json.dumps({"repo_url": "test"}))

    report = evaluate_backup_freshness(
        backup_root=backup,
        dev_root=dev,
        live_root=live,
        tracked_files=tracked,
        repo_meta={"clone_ok": None, "source": "test"},
    )

    assert report["backup_fresh"] is False
    assert report["blocking"] is True
    assert report["risk"] == "HIGH"
    assert report["missing_from_backup"] == tracked[1:]
    assert "backup_missing_tracked_files" in report["blocking_reasons"]


def test_evaluate_backup_freshness_blocks_when_live_runtime_lacks_policy_files(tmp_path):
    tracked = ["cli.py", "tools/merged_policy_validator.py"]
    dev = tmp_path / "dev"
    live = tmp_path / "live"
    backup = tmp_path / "backup"
    _seed_minimal_tree(dev, tracked)
    _seed_minimal_tree(live, ["cli.py"])
    _seed_minimal_tree(backup, tracked, prefix="sources/hermes-agent")
    _write(backup / "restore" / "MANIFEST.json", json.dumps({"repo_url": "test"}))

    report = evaluate_backup_freshness(
        backup_root=backup,
        dev_root=dev,
        live_root=live,
        tracked_files=tracked,
        repo_meta={"clone_ok": None, "source": "test"},
    )

    assert report["backup_fresh"] is False
    assert report["blocking"] is True
    assert report["risk"] == "HIGH"
    assert report["missing_from_live_runtime"] == ["tools/merged_policy_validator.py"]
    assert "live_runtime_missing_tracked_files" in report["blocking_reasons"]


def test_evaluate_backup_freshness_passes_when_all_hashes_match(tmp_path):
    tracked = ["cli.py", "hermes_cli/hermes_os_format.py"]
    dev = tmp_path / "dev"
    live = tmp_path / "live"
    backup = tmp_path / "backup"
    _seed_minimal_tree(dev, tracked)
    _seed_minimal_tree(live, tracked)
    _seed_minimal_tree(backup, tracked, prefix="sources/hermes-agent")
    _write(backup / "restore" / "MANIFEST.json", json.dumps({"repo_url": "test"}))

    report = evaluate_backup_freshness(
        backup_root=backup,
        dev_root=dev,
        live_root=live,
        tracked_files=tracked,
        repo_meta={"clone_ok": None, "source": "test"},
    )

    assert report["backup_fresh"] is True
    assert report["blocking"] is False
    assert report["risk"] == "LOW"
    assert report["missing_from_backup"] == []
    assert report["hash_mismatches"] == []


def test_cli_writes_json_report_and_returns_blocking_code(tmp_path, capsys):
    tracked_files = [
        "cli.py",
        "hermes_cli/main.py",
        "hermes_cli/commands.py",
        "gateway/run.py",
        "gateway/platforms/base.py",
        "agent/skill_commands.py",
        "model_tools.py",
        "toolsets.py",
        "hermes_cli/hermes_os_format.py",
        "website/docs/reference/merged-hard-gate-policy.yaml",
        "website/docs/reference/merged-hard-gate-policy.schema.json",
        "website/docs/reference/merged-hard-gate-policy-card.md",
        "tools/merged_policy_validator.py",
    ]
    dev = tmp_path / "dev"
    live = tmp_path / "live"
    backup = tmp_path / "backup"
    _seed_minimal_tree(dev, tracked_files)
    _seed_minimal_tree(live, tracked_files)
    _seed_minimal_tree(backup, tracked_files[:-1], prefix="sources/hermes-agent")
    _write(backup / "restore" / "MANIFEST.json", json.dumps({"repo_url": "test"}))
    out = tmp_path / "report.json"

    exit_code = main([
        "--backup-root",
        str(backup),
        "--dev-root",
        str(dev),
        "--live-root",
        str(live),
        "--output",
        str(out),
    ])

    captured = capsys.readouterr()
    report = json.loads(out.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert report["blocking"] is True
    assert report["missing_from_backup"] == ["tools/merged_policy_validator.py"]
    assert json.loads(captured.out)["risk"] == "HIGH"
