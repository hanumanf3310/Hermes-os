"""Hermes core update impact gate helper.

This helper compares the current Hermes Agent / Hermes OS checkout against an
upstream core candidate, classifies the impact on protected Hermes OS surfaces,
and formats an evidence-first report for CLI and Telegram use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import shlex
import subprocess
from typing import Iterable


DEFAULT_UPSTREAM_REPO = "https://github.com/NousResearch/hermes-agent"
DEFAULT_UPSTREAM_REF = "main"

_USAGE = "Usage: /hermes-core-update-impact-gate [--upstream URL] [--ref REF]"

_CRITICAL_SURFACES = {
    "cli.py": "command-routing",
    "gateway/run.py": "command-routing",
    "gateway/platforms/base.py": "command-routing",
    "hermes_cli/commands.py": "command-routing",
    "hermes_cli/workspace_launcher.py": "command-routing",
    "agent/skill_commands.py": "command-routing",
    "hermes_cli/policy_gate.py": "policy-gate",
    "tools/merged_policy_validator.py": "policy-gate",
    "website/docs/reference/merged-hard-gate-policy.yaml": "policy-gate",
    "website/docs/reference/merged-hard-gate-policy.schema.json": "policy-gate",
    "hermes_cli/hermes_os_format.py": "status-format",
    "hermes_cli/main.py": "status-format",
    "agent/context_mode_retrieval.py": "context-routing",
    "agent/policy_compliance_checker.py": "context-routing",
    "agent/smart_model_routing.py": "context-routing",
    "run_agent.py": "context-routing",
    "model_tools.py": "context-routing",
    "toolsets.py": "context-routing",
    "core/": "context-routing",
}

_HIGH_SURFACES = {
    "tests": "tests",
    "website/docs": "docs",
    "dashboard.html": "dashboard",
    "README.md": "docs",
}


@dataclass(frozen=True)
class CoreUpdateImpactRequest:
    upstream_repo: str = DEFAULT_UPSTREAM_REPO
    upstream_ref: str = DEFAULT_UPSTREAM_REF


@dataclass(frozen=True)
class CoreUpdateImpactResult:
    ok: bool = False
    error: str = ""
    repo_path: str = ""
    local_branch: str = ""
    local_head: str = ""
    upstream_repo: str = DEFAULT_UPSTREAM_REPO
    upstream_ref: str = DEFAULT_UPSTREAM_REF
    upstream_head: str = ""
    latest_tag: str = ""
    ahead: int = 0
    behind: int = 0
    dirty_files: tuple[str, ...] = field(default_factory=tuple)
    untracked_files: tuple[str, ...] = field(default_factory=tuple)
    changed_files: tuple[str, ...] = field(default_factory=tuple)
    impacted_surfaces: tuple[str, ...] = field(default_factory=tuple)
    protected_files: tuple[str, ...] = field(default_factory=tuple)
    risk: str = "LOW"
    backup_required: bool = False
    next_action: str = "Safe to review with normal verification."


def core_update_impact_usage() -> str:
    return _USAGE


def parse_core_update_impact_request(raw_args: str | None) -> tuple[CoreUpdateImpactRequest | None, str | None]:
    tokens = shlex.split(raw_args or "")
    upstream_repo = DEFAULT_UPSTREAM_REPO
    upstream_ref = DEFAULT_UPSTREAM_REF

    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if token in {"-h", "--help"}:
            return None, _USAGE
        if token in {"-u", "--upstream"}:
            idx += 1
            if idx >= len(tokens):
                return None, f"Missing value for {token}.\n{_USAGE}"
            upstream_repo = tokens[idx]
        elif token.startswith("--upstream="):
            upstream_repo = token.split("=", 1)[1].strip()
        elif token in {"-r", "--ref"}:
            idx += 1
            if idx >= len(tokens):
                return None, f"Missing value for {token}.\n{_USAGE}"
            upstream_ref = tokens[idx]
        elif token.startswith("--ref="):
            upstream_ref = token.split("=", 1)[1].strip()
        else:
            return None, f"Unknown argument: {token}\n{_USAGE}"
        idx += 1

    return CoreUpdateImpactRequest(upstream_repo=upstream_repo, upstream_ref=upstream_ref), None


def classify_core_update_impact(
    changed_files: Iterable[str],
    dirty_files: Iterable[str] = (),
    untracked_files: Iterable[str] = (),
) -> tuple[str, tuple[str, ...], tuple[str, ...], bool, str]:
    """Classify the impact on Hermes OS surfaces from file paths."""

    combined = []
    seen = set()
    for source in (changed_files, dirty_files, untracked_files):
        for path in source:
            path = path.strip().replace("\\", "/")
            if not path or path in seen:
                continue
            seen.add(path)
            combined.append(path)

    impacted: list[str] = []
    protected: list[str] = []
    risk = "LOW"
    next_action = "Safe to review with normal verification."

    def mark(surface: str, file_path: str) -> None:
        nonlocal risk, next_action
        if surface not in impacted:
            impacted.append(surface)
        if file_path not in protected:
            protected.append(file_path)
        if risk != "CRITICAL":
            risk = "CRITICAL"
            next_action = (
                "Stop before merge: capture a backup branch and restore point, then run focused Hermes OS parity smoke tests."
            )

    for path in combined:
        if path in _CRITICAL_SURFACES:
            mark(_CRITICAL_SURFACES[path], path)
            continue
        if path.startswith("core/"):
            if "context-routing" not in impacted:
                impacted.append("context-routing")
            if risk not in {"CRITICAL"}:
                risk = "HIGH"
                next_action = "Create a backup branch and run focused Hermes OS parity smoke tests before update."
            continue
        for prefix, surface in _HIGH_SURFACES.items():
            if path.startswith(prefix):
                if surface not in impacted:
                    impacted.append(surface)
                if risk == "LOW":
                    risk = "HIGH"
                    next_action = "Create a backup branch and run focused Hermes OS parity smoke tests before update."
                break
        else:
            if risk == "LOW":
                risk = "MEDIUM"
                next_action = "Proceed with a staged update and rerun the focused verification suite."

    backup_required = risk in {"HIGH", "CRITICAL"}
    if not combined:
        next_action = "No file-level drift detected; safe to review with normal verification."

    return risk, tuple(impacted), tuple(protected), backup_required, next_action


def _run_git(args: list[str], *, cwd: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)


def _git_stdout(args: list[str], *, cwd: str | None = None, timeout: int = 120) -> str:
    result = _run_git(args, cwd=cwd, timeout=timeout)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(stderr or f"git command failed: {' '.join(args)}")
    return (result.stdout or "").strip()


def run_core_update_impact_gate(request: CoreUpdateImpactRequest, *, timeout: int = 120) -> CoreUpdateImpactResult:
    """Inspect the current repo against an upstream core candidate."""

    try:
        repo_path = _git_stdout(["rev-parse", "--show-toplevel"], timeout=timeout)
        local_branch = _git_stdout(["branch", "--show-current"], cwd=repo_path, timeout=timeout)
        local_head = _git_stdout(["rev-parse", "HEAD"], cwd=repo_path, timeout=timeout)
        status_raw = _git_stdout(["status", "--porcelain=v1"], cwd=repo_path, timeout=timeout)

        dirty_files: list[str] = []
        untracked_files: list[str] = []
        for line in status_raw.splitlines():
            if len(line) < 3:
                continue
            path = line[3:].strip()
            if line.startswith("??"):
                untracked_files.append(path)
            else:
                dirty_files.append(path)

        fetch_result = _run_git(
            ["fetch", "--depth", "1", "--no-tags", request.upstream_repo, request.upstream_ref],
            cwd=repo_path,
            timeout=timeout,
        )
        if fetch_result.returncode != 0:
            stderr = (fetch_result.stderr or fetch_result.stdout or "").strip()
            return CoreUpdateImpactResult(ok=False, error=stderr or "Failed to fetch upstream core candidate.")

        upstream_head = _git_stdout(["rev-parse", "FETCH_HEAD"], cwd=repo_path, timeout=timeout)
        ahead_behind = _git_stdout(["rev-list", "--left-right", "--count", f"HEAD...FETCH_HEAD"], cwd=repo_path, timeout=timeout)
        ahead_str, behind_str = ahead_behind.split(maxsplit=1)
        ahead = int(ahead_str)
        behind = int(behind_str)

        changed_output = _git_stdout(["diff", "--name-only", "HEAD", "FETCH_HEAD"], cwd=repo_path, timeout=timeout)
        changed_files = tuple(line.strip() for line in changed_output.splitlines() if line.strip())

        tags_output = _run_git(
            ["ls-remote", "--tags", "--refs", "--sort=-version:refname", request.upstream_repo],
            timeout=timeout,
        )
        latest_tag = ""
        if tags_output.returncode == 0:
            for line in (tags_output.stdout or "").splitlines():
                if "\trefs/tags/" in line:
                    latest_tag = line.split("refs/tags/", 1)[1].strip()
                    break

        risk, impacted_surfaces, protected_files, backup_required, next_action = classify_core_update_impact(
            changed_files,
            dirty_files,
            untracked_files,
        )

        return CoreUpdateImpactResult(
            ok=True,
            repo_path=repo_path,
            local_branch=local_branch or "(detached)",
            local_head=local_head,
            upstream_repo=request.upstream_repo,
            upstream_ref=request.upstream_ref,
            upstream_head=upstream_head,
            latest_tag=latest_tag,
            ahead=ahead,
            behind=behind,
            dirty_files=tuple(dirty_files),
            untracked_files=tuple(untracked_files),
            changed_files=changed_files,
            impacted_surfaces=impacted_surfaces,
            protected_files=protected_files,
            risk=risk,
            backup_required=backup_required,
            next_action=next_action,
        )
    except Exception as exc:
        return CoreUpdateImpactResult(ok=False, error=str(exc))


def format_core_update_impact_result(result: CoreUpdateImpactResult) -> str:
    if not result.ok:
        return "\n".join([
            "🧩 **Hermes Core Update Impact Gate**",
            "━━━━━━━━━━━━━━━━━━━━━",
            f"❌ **Blocked:** {result.error or 'Unable to inspect the current repository.'}",
            _USAGE,
        ])

    def _bullet_list(items: Iterable[str], *, limit: int = 25) -> list[str]:
        lines: list[str] = []
        values = list(items)
        for item in values[:limit]:
            lines.append(f"  • {item}")
        if len(values) > limit:
            lines.append(f"  • … and {len(values) - limit} more")
        if not values:
            lines.append("  • (none)")
        return lines

    lines = [
        "🧩 **Hermes Core Update Impact Gate**",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"✅ **Status:** {result.risk}",
        f"📦 **Repo:** `{result.repo_path}`",
        f"🌿 **Branch:** `{result.local_branch}`",
        f"🧷 **Local HEAD:** `{result.local_head}`",
        f"⬆️ **Upstream:** `{result.upstream_repo}` (`{result.upstream_ref}`)",
        f"⬆️ **Upstream HEAD:** `{result.upstream_head}`",
        f"🏷️ **Latest upstream tag:** `{result.latest_tag or 'n/a'}`",
        f"↔️ **Ahead/behind:** `{result.ahead}` ahead / `{result.behind}` behind",
        f"🧹 **Dirty files:** `{len(result.dirty_files)}`",
        f"🆕 **Untracked files:** `{len(result.untracked_files)}`",
        f"🛡️ **Backup required:** `{'yes' if result.backup_required else 'no'}`",
        "",
        "🔎 **Impacted Hermes OS surfaces**",
    ]
    lines.extend(_bullet_list(result.impacted_surfaces))
    lines.extend([
        "",
        "🧱 **Protected files touched**",
    ])
    lines.extend(_bullet_list(result.protected_files))
    lines.extend([
        "",
        "📁 **Changed files**",
    ])
    lines.extend(_bullet_list(result.changed_files, limit=20))
    lines.extend([
        "",
        f"➡️ **Next action:** {result.next_action}",
        "",
        "✅ **Interpretation:** compare-first complete; update only after backup + parity smoke tests.",
    ])
    return "\n".join(lines)
