#!/usr/bin/env python3
"""Hermes OS GitHub backup freshness gate.

Checks whether the restore snapshot repository contains the current Hermes OS
protected files and whether its hashes match the local dev/runtime sources.
This gate is intentionally read-only: it never pushes or mutates the backup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

DEFAULT_REPO_URL = "https://github.com/hanumanf3310/Hermes-os.git"
DEFAULT_DEV_ROOT = Path("/home/hanuman3310/hermes-agent")
DEFAULT_LIVE_ROOT = Path("/home/hanuman3310/.hermes/hermes-agent")
BACKUP_SOURCE_PREFIX = Path("sources/hermes-agent")

PROTECTED_FILES = [
    "cli.py",
    "hermes_cli/main.py",
    "hermes_cli/commands.py",
    "gateway/run.py",
    "gateway/platforms/base.py",
    "agent/skill_commands.py",
    "model_tools.py",
    "toolsets.py",
    "hermes_cli/hermes_os_format.py",
]

POLICY_FILES = [
    "website/docs/reference/merged-hard-gate-policy.yaml",
    "website/docs/reference/merged-hard-gate-policy.schema.json",
    "website/docs/reference/merged-hard-gate-policy-card.md",
    "tools/merged_policy_validator.py",
]

DEFAULT_TRACKED_FILES = PROTECTED_FILES + POLICY_FILES


@dataclass(frozen=True)
class GitInfo:
    head: str | None
    branch: str | None
    dirty_count: int | None


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _git_info(path: Path) -> GitInfo:
    if not (path / ".git").exists():
        return GitInfo(head=None, branch=None, dirty_count=None)
    head = _run(["git", "rev-parse", "HEAD"], cwd=path).stdout.strip() or None
    branch = _run(["git", "branch", "--show-current"], cwd=path).stdout.strip() or None
    status = _run(["git", "status", "--short"], cwd=path).stdout.splitlines()
    return GitInfo(head=head, branch=branch, dirty_count=len(status))


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _clone_backup(repo_url: str, tmp_parent: Path) -> tuple[Path | None, dict[str, Any]]:
    clone_path = tmp_parent / "Hermes-os"
    proc = _run(["git", "clone", "--depth", "1", repo_url, str(clone_path)], timeout=240)
    meta: dict[str, Any] = {
        "repo_url": repo_url,
        "clone_ok": proc.returncode == 0,
        "clone_stdout": proc.stdout.strip(),
        "clone_stderr": proc.stderr.strip()[-2000:],
    }
    if proc.returncode != 0:
        return None, meta
    info = _git_info(clone_path)
    meta.update({"head": info.head, "branch": info.branch, "dirty_count": info.dirty_count})
    return clone_path, meta


def _read_manifest(backup_root: Path) -> dict[str, Any] | None:
    manifest = backup_root / "restore" / "MANIFEST.json"
    if not manifest.exists():
        return None
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exact JSON error not important
        return {"error": str(exc)}


def evaluate_backup_freshness(
    *,
    backup_root: Path,
    dev_root: Path = DEFAULT_DEV_ROOT,
    live_root: Path = DEFAULT_LIVE_ROOT,
    tracked_files: list[str] | None = None,
    repo_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tracked = tracked_files or DEFAULT_TRACKED_FILES
    now = datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(timespec="seconds")

    dev_info = _git_info(dev_root)
    live_info = _git_info(live_root)
    report: dict[str, Any] = {
        "schema_version": 1,
        "checked_at_bangkok": now,
        "repo": repo_meta or {},
        "dev_checkout": {"path": str(dev_root), **dev_info.__dict__},
        "live_runtime": {"path": str(live_root), **live_info.__dict__},
        "backup_root": str(backup_root),
        "manifest_present": (backup_root / "restore" / "MANIFEST.json").exists(),
        "manifest": _read_manifest(backup_root),
        "tracked_files": tracked,
        "files": [],
        "missing_from_backup": [],
        "missing_from_dev": [],
        "missing_from_live_runtime": [],
        "hash_mismatches": [],
        "blocking_reasons": [],
    }

    for rel in tracked:
        rel_path = Path(rel)
        backup_path = backup_root / BACKUP_SOURCE_PREFIX / rel_path
        dev_path = dev_root / rel_path
        live_path = live_root / rel_path
        backup_hash = _sha256(backup_path)
        dev_hash = _sha256(dev_path)
        live_hash = _sha256(live_path)
        entry = {
            "path": rel,
            "backup_exists": backup_hash is not None,
            "dev_exists": dev_hash is not None,
            "live_exists": live_hash is not None,
            "backup_sha256": backup_hash,
            "dev_sha256": dev_hash,
            "live_sha256": live_hash,
            "backup_matches_dev": backup_hash is not None and backup_hash == dev_hash,
            "backup_matches_live": backup_hash is not None and live_hash is not None and backup_hash == live_hash,
            "dev_matches_live": dev_hash is not None and live_hash is not None and dev_hash == live_hash,
        }
        report["files"].append(entry)
        if backup_hash is None:
            report["missing_from_backup"].append(rel)
        if dev_hash is None:
            report["missing_from_dev"].append(rel)
        if live_hash is None:
            report["missing_from_live_runtime"].append(rel)
        if backup_hash is not None and dev_hash is not None and backup_hash != dev_hash:
            report["hash_mismatches"].append({"path": rel, "backup_vs": "dev"})
        if backup_hash is not None and live_hash is not None and backup_hash != live_hash:
            report["hash_mismatches"].append({"path": rel, "backup_vs": "live_runtime"})

    if report["missing_from_backup"]:
        report["blocking_reasons"].append("backup_missing_tracked_files")
    if report["missing_from_dev"]:
        report["blocking_reasons"].append("dev_missing_tracked_files")
    if report["missing_from_live_runtime"]:
        report["blocking_reasons"].append("live_runtime_missing_tracked_files")
    if report["hash_mismatches"]:
        report["blocking_reasons"].append("tracked_file_hash_mismatch")
    if not report["manifest_present"]:
        report["blocking_reasons"].append("manifest_missing")
    if report["repo"] and report["repo"].get("clone_ok") is False:
        report["blocking_reasons"].append("backup_clone_failed")

    if any(reason in report["blocking_reasons"] for reason in ("backup_clone_failed", "dev_missing_tracked_files")):
        risk = "CRITICAL"
    elif report["missing_from_backup"] or report["missing_from_live_runtime"]:
        risk = "HIGH"
    elif report["hash_mismatches"]:
        risk = "HIGH"
    elif report["repo"].get("dirty_count") not in (0, None):
        risk = "MEDIUM"
    else:
        risk = "LOW"
    report["risk"] = risk
    report["backup_fresh"] = risk == "LOW"
    report["blocking"] = risk in {"HIGH", "CRITICAL"}
    return report


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    dev_root = Path(args.dev_root).expanduser().resolve()
    live_root = Path(args.live_root).expanduser().resolve()
    if args.backup_root:
        backup_root = Path(args.backup_root).expanduser().resolve()
        repo_meta = {"repo_url": args.repo_url, "clone_ok": None, "source": "local_backup_root"}
        return evaluate_backup_freshness(
            backup_root=backup_root,
            dev_root=dev_root,
            live_root=live_root,
            repo_meta=repo_meta,
        )

    with tempfile.TemporaryDirectory(prefix="hermes-backup-freshness-") as tmp:
        backup_root, repo_meta = _clone_backup(args.repo_url, Path(tmp))
        if backup_root is None:
            report = evaluate_backup_freshness(
                backup_root=Path(tmp) / "Hermes-os",
                dev_root=dev_root,
                live_root=live_root,
                repo_meta=repo_meta,
            )
            report["risk"] = "CRITICAL"
            report["backup_fresh"] = False
            report["blocking"] = True
            return report
        return evaluate_backup_freshness(
            backup_root=backup_root,
            dev_root=dev_root,
            live_root=live_root,
            repo_meta=repo_meta,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Hermes-os GitHub backup freshness.")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    parser.add_argument("--backup-root", help="Use an already cloned backup root instead of cloning.")
    parser.add_argument("--dev-root", default=str(DEFAULT_DEV_ROOT))
    parser.add_argument("--live-root", default=str(DEFAULT_LIVE_ROOT))
    parser.add_argument("--output", help="Write JSON report to this path.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    args = parser.parse_args(argv)

    report = build_report(args)
    text = json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True)
    if args.output:
        out = Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if report.get("blocking") else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
