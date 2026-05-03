#!/usr/bin/env python3
"""Validate Hermes memory-graph dashboard.html static graph data.

Checks:
- duplicate node IDs
- duplicate exact links
- links referencing missing nodes
- whole graph connectivity
- required Boss/Hermes OS/thClaws working-path links

Exit code 0 = valid. Exit code 1 = validation failed.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

DEFAULT_DASHBOARD = Path.home() / "hermes-workspace/memory-graph/dashboard.html"

REQUIRED_LINKS = [
    ("user_profile", "hermes_os_core"),
    ("user_profile", "thclaws_default_model"),
    ("user_profile", "thclaws_update_safe"),
    ("user_profile", "hermes_learning_thclaws"),
    ("user_profile", "proj_thclaws_harness"),
    ("skill_hermes_os_integration", "hermes_os_core"),
    ("hermes_os_core", "enterprise_fleet"),
    ("hermes_os_core", "proj_hermes_os_runtime"),
    ("hermes_os_core", "proj_thclaws_harness"),
    ("skill_writing_plans", "thclaws_update_safe"),
    ("skill_writing_plans", "proj_thclaws_harness"),
    ("cat_software", "skill_thclaws_update_gate"),
    ("cat_software", "proj_thclaws_harness"),
    ("hermes_workspace", "proj_thclaws_harness"),
    ("proj_memory_graph", "proj_thclaws_harness"),
    ("thclaws_update_safe", "skill_thclaws_update_gate"),
    ("user_profile", "telegram_greeting"),
    ("brave_api", "cat_research"),
    ("cat_mlop", "hermes_os_core"),
    ("cat_creative", "hermes_workspace"),
    ("cat_github", "cat_software"),
    ("cat_autonomous", "hermes_os_core"),
    ("cat_mcp", "hermes_os_core"),
]


def _extract_js_array(text: str, key: str) -> str:
    """Extract a top-level JavaScript array assigned to an object key.

    The dashboard node objects can contain nested arrays such as impact_scope.
    A plain split on the first `]` truncates the nodes array, so parse brackets
    while respecting quoted strings.
    """
    marker = f'"{key}": ['
    start = text.find(marker)
    if start == -1:
        raise ValueError(f"dashboard.html does not contain expected {key} array")
    i = text.find("[", start)
    depth = 0
    in_string = False
    escape = False
    quote = ""
    for pos in range(i, len(text)):
        ch = text[pos]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_string = False
            continue
        if ch in ('"', "'"):
            in_string = True
            quote = ch
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[i + 1 : pos]
    raise ValueError(f"unterminated {key} array")


def parse_dashboard(path: Path):
    text = path.read_text(encoding="utf-8")
    nodes_part = _extract_js_array(text, "nodes")
    links_part = _extract_js_array(text, "links")
    node_ids = re.findall(r'\{\s*"id":\s*"([^"]+)"', nodes_part)
    links = re.findall(
        r'\{\s*"source":\s*"([^"]+)",\s*"target":\s*"([^"]+)",\s*"type":\s*"([^"]+)"',
        links_part,
    )
    return node_ids, links


def connected_components(node_ids, links):
    node_set = set(node_ids)
    adj = collections.defaultdict(set)
    for source, target, _type in links:
        if source in node_set and target in node_set:
            adj[source].add(target)
            adj[target].add(source)
    seen = set()
    comps = []
    for node in node_ids:
        if node in seen:
            continue
        stack = [node]
        seen.add(node)
        comp = []
        while stack:
            current = stack.pop()
            comp.append(current)
            for nxt in adj[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        comps.append(comp)
    return comps


def validate(path: Path):
    node_ids, links = parse_dashboard(path)
    node_set = set(node_ids)
    duplicate_nodes = sorted(k for k, v in collections.Counter(node_ids).items() if v > 1)
    duplicate_links = [list(k) for k, v in collections.Counter(links).items() if v > 1]
    missing_link_references = [
        {
            "source": source,
            "target": target,
            "type": link_type,
            "source_exists": source in node_set,
            "target_exists": target in node_set,
        }
        for source, target, link_type in links
        if source not in node_set or target not in node_set
    ]
    comps = connected_components(node_ids, links)
    pair_set = {(source, target) for source, target, _ in links}
    missing_required_links = [list(pair) for pair in REQUIRED_LINKS if pair not in pair_set]
    report = {
        "dashboard": str(path),
        "nodes": len(node_ids),
        "links": len(links),
        "duplicate_nodes": duplicate_nodes,
        "duplicate_links": duplicate_links,
        "missing_link_references": missing_link_references,
        "connected_components": len(comps),
        "component_sizes": sorted((len(c) for c in comps), reverse=True),
        "isolated_nodes": sorted(c[0] for c in comps if len(c) == 1),
        "missing_required_links": missing_required_links,
    }
    report["ok"] = not (
        duplicate_nodes
        or duplicate_links
        or missing_link_references
        or missing_required_links
        or len(comps) != 1
    )
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dashboard", nargs="?", default=str(DEFAULT_DASHBOARD))
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    args = parser.parse_args(argv)
    path = Path(args.dashboard).expanduser()
    report = validate(path)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        status = "OK" if report["ok"] else "FAIL"
        print(
            f"{status}: nodes={report['nodes']} links={report['links']} "
            f"components={report['connected_components']} isolated={len(report['isolated_nodes'])} "
            f"missing_refs={len(report['missing_link_references'])} "
            f"missing_required={len(report['missing_required_links'])}"
        )
        if not report["ok"]:
            print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
