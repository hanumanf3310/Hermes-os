from __future__ import annotations

import json
import sqlite3
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
HERMES_AGENT_ROOT = Path("/home/hanuman3310/hermes-agent")
if str(HERMES_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_AGENT_ROOT))

import memory_graph_server as mgs
from fact_store_api import migrate_fact_store_db
from plugins.memory.holographic.store import MemoryStore


FACT_CREATE_PAYLOAD = {
    "content": "Hermes OS-impacting change must be verified before use",
    "category": "policy",
    "fact_type": "fact_plus_star",
    "fact_star": True,
    "fact_plus": True,
    "verify_before_use": True,
    "importance_level": "critical",
    "star_reason": "affects routing and rollback safety",
    "learning_policy_id": "policy-777",
    "verification_status": "verified",
    "verified_by": "Boss",
    "impact_scope": ["policy", "learning", "hermes_os"],
    "tags": ["update", "fact"],
    "related_entities": ["Hermes OS", "Fact Store"],
}


def _table_columns(conn: sqlite3.Connection) -> set[str]:
    return {row[1] for row in conn.execute("PRAGMA table_info(facts)").fetchall()}


def _request_json(url: str, payload: dict | None = None, method: str = "GET") -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body)


@pytest.fixture()
def fact_graph_server(tmp_path, monkeypatch):
    db_path = tmp_path / "memory_store.db"
    monkeypatch.setattr(mgs, "FACT_DB", db_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), mgs.MemoryGraphHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", db_path
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_fact_migration_script_renames_legacy_table_and_adds_columns(tmp_path):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE fact_records (
            fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL UNIQUE,
            category TEXT DEFAULT 'general',
            tags TEXT DEFAULT '',
            trust_score REAL DEFAULT 0.5,
            retrieval_count INTEGER DEFAULT 0,
            helpful_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            hrr_vector BLOB
        )
        """
    )
    conn.execute(
        "INSERT INTO fact_records (content, category, tags) VALUES (?, ?, ?)",
        ("Legacy fact", "general", ""),
    )
    conn.commit()
    conn.close()

    result = migrate_fact_store_db(db_path)

    assert result["ok"] is True
    assert result["renamed_legacy_table"] is True
    assert "fact_type" in result["added_columns"]

    conn = sqlite3.connect(db_path)
    try:
        columns = _table_columns(conn)
        assert {"fact_type", "fact_star", "fact_plus", "verify_before_use", "importance_level"}.issubset(columns)
        row = conn.execute("SELECT content FROM facts WHERE fact_id = 1").fetchone()
        assert row[0] == "Legacy fact"
    finally:
        conn.close()


def test_memory_graph_api_lists_gets_updates_and_deletes_fact_records(fact_graph_server):
    base_url, db_path = fact_graph_server

    status, created = _request_json(f"{base_url}/api/facts", FACT_CREATE_PAYLOAD, method="POST")
    assert status == 201
    fact_id = created["fact_id"]

    status, listed = _request_json(f"{base_url}/api/facts?fact_type=fact_plus_star&limit=10", None, method="GET")
    assert status == 200
    assert listed["ok"] is True
    assert listed["status"] == "ok"
    assert listed["count"] >= 1
    assert any(item["fact_id"] == fact_id for item in listed["facts"])

    status, fetched = _request_json(f"{base_url}/api/facts/{fact_id}", None, method="GET")
    assert status == 200
    assert fetched["ok"] is True
    assert fetched["fact"]["fact_id"] == fact_id
    assert fetched["fact"]["fact_type"] == "fact_plus_star"

    status, updated = _request_json(
        f"{base_url}/api/facts/{fact_id}",
        {"notes": "Dashboard-approved update", "verified_by": "Boss"},
        method="PATCH",
    )
    assert status == 200
    assert updated["ok"] is True

    status, deleted = _request_json(f"{base_url}/api/facts/{fact_id}", None, method="DELETE")
    assert status == 200
    assert deleted["ok"] is True
    assert deleted["status"] == "deleted"

    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _request_json(f"{base_url}/api/facts/{fact_id}", None, method="GET")
    assert excinfo.value.code == 404


def test_memory_graph_api_can_create_and_update_fact_records(fact_graph_server):
    base_url, db_path = fact_graph_server

    status, created = _request_json(f"{base_url}/api/facts", FACT_CREATE_PAYLOAD, method="POST")
    assert status == 201
    assert created["ok"] is True
    assert created["status"] == "created"
    fact_id = created["fact_id"]

    store = MemoryStore(db_path=db_path)
    try:
        fact = store.get_fact(fact_id)
        assert fact is not None
        assert fact["fact_type"] == "fact_plus_star"
        assert fact["fact_star"] is True
        assert fact["fact_plus"] is True
        assert fact["verify_before_use"] is True
        assert fact["importance_level"] == "critical"
        assert fact["verification_status"] == "verified"
    finally:
        store.close()

    status, updated = _request_json(
        f"{base_url}/api/facts/{fact_id}",
        {"notes": "Dashboard-approved update", "verified_by": "Boss"},
        method="PATCH",
    )
    assert status == 200
    assert updated["ok"] is True
    assert updated["status"] == "updated"

    store = MemoryStore(db_path=db_path)
    try:
        fact = store.get_fact(fact_id)
        assert fact is not None
        assert fact["notes"] == "Dashboard-approved update"
        assert fact["verified_by"] == "Boss"
    finally:
        store.close()

    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _request_json(
            f"{base_url}/api/facts",
            {
                "content": "Broken star fact",
                "category": "policy",
                "fact_type": "fact_plus_star",
                "fact_star": True,
                "fact_plus": True,
                "importance_level": "critical",
                "star_reason": "missing learning policy",
            },
            method="POST",
        )
    assert excinfo.value.code == 400
