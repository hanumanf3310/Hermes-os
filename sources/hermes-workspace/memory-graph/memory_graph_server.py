#!/usr/bin/env python3
"""Hermes Memory Graph server.

Serves dashboard.html and a live /api/fact-graph endpoint from the shared
Hermes Fact Store SQLite database so the dashboard can be opened from mobile
with a single public URL.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

WORKSPACE_DIR = Path("/home/hanuman3310/hermes-workspace/memory-graph")
HERMES_AGENT_DIR = Path("/home/hanuman3310/hermes-agent")
if str(HERMES_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(HERMES_AGENT_DIR))

from plugins.memory.holographic.store import MemoryStore
from fact_store_api import FACT_DB as FACT_STORE_DB, create_fact_record, delete_fact_record, get_fact_record, list_fact_records, update_fact_record

FACT_DB = FACT_STORE_DB
DEFAULT_PORT = int(os.environ.get("HERMES_MEMORY_GRAPH_PORT", "9130"))


def _parse_list_field(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [part.strip() for part in text.split(",") if part.strip()]
    return []


def _parse_bool_param(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _fact_graph_node_id(fact_id: int) -> str:
    return f"fact_{fact_id}"


def build_fact_graph(limit: int = 200, fact_type: str = "fact_star") -> dict:
    store = MemoryStore(FACT_DB)
    try:
        facts = store.list_facts(limit=limit, fact_type=fact_type)
        nodes = []
        links = []
        for fact in facts:
            node_id = _fact_graph_node_id(int(fact["fact_id"]))
            ftype = fact.get("fact_type") or "fact"
            is_star = bool(fact.get("fact_star")) or ftype == "fact_star"
            is_plus = bool(fact.get("fact_plus")) or ftype == "fact_plus"
            content = fact.get("content", "")
            nodes.append(
                {
                    "id": node_id,
                    "name": content if len(content) <= 24 else content[:24],
                    "type": ftype,
                    "color": "#f43f5e" if is_star else ("#f59e0b" if is_plus else "#a855f7"),
                    "size": 24 if is_star else (20 if is_plus else 18),
                    "desc": content,
                    "fact_id": fact.get("fact_id"),
                    "fact_type": ftype,
                    "fact_star": is_star,
                    "fact_plus": is_plus,
                    "verify_before_use": bool(fact.get("verify_before_use")),
                    "importance_level": fact.get("importance_level"),
                    "star_reason": fact.get("star_reason"),
                    "verification_status": fact.get("verification_status"),
                    "impact_scope": fact.get("impact_scope"),
                    "learning_policy_id": fact.get("learning_policy_id"),
                    "category": fact.get("category"),
                    "tags": fact.get("tags"),
                    "trust_score": fact.get("trust_score"),
                    "related_entities": fact.get("related_entities"),
                    "source": fact.get("source"),
                }
            )
            links.append({"source": "fact_store", "target": node_id, "type": "contains"})
            if is_star:
                links.append({"source": node_id, "target": "hermes_os_core", "type": "fact-star"})
            elif is_plus:
                links.append({"source": node_id, "target": "memory_enhancement", "type": "fact-plus"})

            scope = _parse_list_field(fact.get("impact_scope"))
            scope_lower = {str(item).lower() for item in scope}
            if {"hermes_os", "hermes-os", "hermes os"} & scope_lower:
                links.append({"source": node_id, "target": "hermes_os_core", "type": "impact-scope"})
            if "learning" in scope_lower:
                links.append({"source": node_id, "target": "memory_enhancement", "type": "impact-scope"})

            content_lower = content.lower()
            if "thclaws" in content_lower:
                links.append({"source": node_id, "target": "proj_thclaws_harness", "type": "mentions"})
            if "calendar" in content_lower:
                links.append({"source": node_id, "target": "cat_productivity", "type": "mentions"})
            if "approval" in content_lower or "security" in content_lower:
                links.append({"source": node_id, "target": "cat_hermes_os", "type": "governance"})

        deduped = []
        seen = set()
        for link in links:
            key = (link["source"], link["target"], link.get("type", ""))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(link)

        return {
            "generated_at": time.time(),
            "source_db": str(FACT_DB),
            "nodes": nodes,
            "links": deduped,
            "stats": {
                "fact_count": len(facts),
                "fact_star_count": sum(1 for f in facts if f.get("fact_star") or f.get("fact_type") == "fact_star"),
                "fact_plus_count": sum(1 for f in facts if f.get("fact_plus") or f.get("fact_type") == "fact_plus"),
                "fact_plus_star_count": sum(1 for f in facts if f.get("fact_type") == "fact_plus_star" or (f.get("fact_star") and f.get("fact_plus"))),
            },
        }
    finally:
        store.close()


class MemoryGraphHandler(BaseHTTPRequestHandler):
    server_version = "HermesMemoryGraph/1.0"

    def _send(self, status: int, body: bytes, content_type: str = "text/plain; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, status: int = 200):
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_OPTIONS(self):
        self._send(HTTPStatus.NO_CONTENT, b"")

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        payload = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in {"/", "/dashboard.html"}:
            return self._serve_file(WORKSPACE_DIR / "dashboard.html")
        if path == "/health":
            return self._send_json({"ok": True, "source_db": str(FACT_DB), "port": DEFAULT_PORT})
        if path == "/api/facts":
            query = parse_qs(parsed.query)
            try:
                limit = int(query.get("limit", ["50"])[0])
                payload = list_fact_records(
                    db_path=FACT_DB,
                    category=query.get("category", [None])[0],
                    min_trust=float(query.get("min_trust", ["0"])[0]),
                    limit=limit,
                    fact_type=query.get("fact_type", [None])[0],
                    fact_star=_parse_bool_param(query.get("fact_star", [None])[0]),
                    fact_plus=_parse_bool_param(query.get("fact_plus", [None])[0]),
                    verify_before_use=_parse_bool_param(query.get("verify_before_use", [None])[0]),
                    verification_status=query.get("verification_status", [None])[0],
                )
                return self._send_json(payload)
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=500)
        if path.startswith("/api/facts/"):
            try:
                fact_id = int(path.rsplit("/", 1)[-1])
                fact = get_fact_record(fact_id, db_path=FACT_DB)
                if fact is None:
                    return self._send_json({"error": "fact not found"}, status=404)
                return self._send_json({"ok": True, "status": "ok", "fact": fact, "fact_id": fact_id})
            except ValueError:
                return self._send_json({"error": "invalid fact id"}, status=400)
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=500)
        if path == "/api/fact-graph":
            query = parse_qs(parsed.query)
            limit = int(query.get("limit", ["200"])[0])
            fact_type = query.get("fact_type", ["fact_star"])[0]
            try:
                return self._send_json(build_fact_graph(limit=limit, fact_type=fact_type))
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=500)

        file_path = WORKSPACE_DIR / path.lstrip("/")
        if file_path.exists() and file_path.is_file():
            return self._serve_file(file_path)

        return self._send_json({"error": "not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/facts":
            return self._send_json({"error": "not found"}, status=404)
        try:
            payload = self._read_json_body()
            result = create_fact_record(payload, db_path=FACT_DB)
            return self._send_json(result, status=201)
        except json.JSONDecodeError as exc:
            return self._send_json({"error": f"invalid json: {exc}"}, status=400)
        except (ValueError, KeyError) as exc:
            return self._send_json({"error": str(exc)}, status=400)
        except Exception as exc:
            return self._send_json({"error": str(exc)}, status=500)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        prefix = "/api/facts/"
        if not parsed.path.startswith(prefix):
            return self._send_json({"error": "not found"}, status=404)
        try:
            fact_id = int(parsed.path[len(prefix):])
            payload = self._read_json_body()
            result = update_fact_record(fact_id, payload, db_path=FACT_DB)
            return self._send_json(result)
        except ValueError as exc:
            return self._send_json({"error": str(exc)}, status=400)
        except KeyError as exc:
            return self._send_json({"error": str(exc)}, status=404)
        except Exception as exc:
            return self._send_json({"error": str(exc)}, status=500)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        prefix = "/api/facts/"
        if not parsed.path.startswith(prefix):
            return self._send_json({"error": "not found"}, status=404)
        try:
            fact_id = int(parsed.path[len(prefix):])
            result = delete_fact_record(fact_id, db_path=FACT_DB)
            return self._send_json(result)
        except ValueError as exc:
            return self._send_json({"error": str(exc)}, status=400)
        except KeyError as exc:
            return self._send_json({"error": str(exc)}, status=404)
        except Exception as exc:
            return self._send_json({"error": str(exc)}, status=500)

    def _serve_file(self, file_path: Path):
        if not file_path.exists():
            return self._send_json({"error": "not found"}, status=404)
        mime, _ = mimetypes.guess_type(str(file_path))
        body = file_path.read_bytes()
        self._send(200, body, mime or "application/octet-stream")

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")


def main():
    port = DEFAULT_PORT
    host = os.environ.get("HERMES_MEMORY_GRAPH_HOST", "127.0.0.1")
    httpd = ThreadingHTTPServer((host, port), MemoryGraphHandler)
    print(f"Hermes Memory Graph server listening on http://{host}:{port}")
    print(f"Dashboard: http://{host}:{port}/dashboard.html")
    print(f"Fact Store: {FACT_DB}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
