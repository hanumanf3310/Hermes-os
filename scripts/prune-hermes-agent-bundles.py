#!/usr/bin/env python3
"""Prune temporary Hermes OS git bundle fallbacks after Git checkpoint verification."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


DEFAULT_BACKUP_DIR = Path.home() / "hermes-agent-backups"


def path_size(path: Path) -> int:
    if path.is_file() or path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for child in path.rglob("*"):
        if child.is_file() or child.is_symlink():
            try:
                total += child.stat().st_size
            except OSError:
                pass
    return total


def resolve_target(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def ensure_safe_target(target: Path) -> None:
    home = Path.home().resolve(strict=False)
    expected = DEFAULT_BACKUP_DIR.resolve(strict=False)
    if target != expected:
        raise SystemExit(f"refusing to prune unexpected path: {target}")
    if target in {Path("/"), home}:
        raise SystemExit(f"refusing unsafe target: {target}")


def newest_bundles(target: Path, keep_latest: int) -> set[Path]:
    bundles = [p for p in target.rglob("*.bundle") if p.is_file()]
    bundles.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return set(bundles[:keep_latest])


def remove_empty_dirs(target: Path, dry_run: bool) -> list[str]:
    removed: list[str] = []
    dirs = [p for p in target.rglob("*") if p.is_dir()]
    dirs.sort(key=lambda p: len(p.parts), reverse=True)
    for directory in dirs:
        try:
            next(directory.iterdir())
        except StopIteration:
            removed.append(str(directory))
            if not dry_run:
                directory.rmdir()
        except OSError:
            continue
    return removed


def prune(target: Path, keep_latest: int, dry_run: bool) -> dict[str, object]:
    ensure_safe_target(target)
    if not target.exists():
        return {
            "backup_dir": str(target),
            "exists": False,
            "dry_run": dry_run,
            "keep_latest": keep_latest,
            "deleted": [],
            "kept": [],
            "freed_bytes": 0,
        }

    before_size = path_size(target)
    kept = newest_bundles(target, keep_latest)
    deleted: list[str] = []

    if keep_latest == 0:
        deleted = [str(target)]
        if not dry_run:
            shutil.rmtree(target)
        return {
            "backup_dir": str(target),
            "exists": True,
            "dry_run": dry_run,
            "keep_latest": keep_latest,
            "deleted": deleted,
            "kept": [],
            "freed_bytes": before_size,
        }

    files = [p for p in target.rglob("*") if p.is_file() or p.is_symlink()]
    for item in files:
        if item in kept:
            continue
        deleted.append(str(item))
        if not dry_run:
            item.unlink()

    deleted.extend(remove_empty_dirs(target, dry_run))
    if dry_run:
        freed = before_size - sum(path_size(p) for p in kept)
    else:
        freed = before_size - path_size(target)
    return {
        "backup_dir": str(target),
        "exists": True,
        "dry_run": dry_run,
        "keep_latest": keep_latest,
        "deleted": deleted,
        "kept": [str(p) for p in sorted(kept)],
        "freed_bytes": max(freed, 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete or trim temporary Hermes OS bundle fallbacks after verified Git checkpoint restore proof."
    )
    parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR))
    parser.add_argument("--keep-latest", type=int, choices=(0, 1), default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--after-verified-git-checkpoint",
        action="store_true",
        help="Required confirmation that push plus fresh-clone manifest/hash verification already passed.",
    )
    args = parser.parse_args()

    if not args.after_verified_git_checkpoint:
        parser.error("--after-verified-git-checkpoint is required")

    target = resolve_target(Path(args.backup_dir))
    result = prune(target, args.keep_latest, args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
