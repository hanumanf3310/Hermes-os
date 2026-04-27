#!/usr/bin/env python3
"""Shared helpers for Hermes Fact Store write APIs and migrations.

This module keeps the dashboard backend and migration script on the same
validation/writing path as the MemoryStore plugin.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

WORKSPACE_ROOT = Path("/home/hanuman3310/hermes-workspace/memory-graph")
HERMES_AGENT_ROOT = Path("/home/hanuman3310/hermes-agent")
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(HERMES_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_AGENT_ROOT))

from hermes_constants import get_hermes_home
from fact_validator import normalize_fact_record, validate_fact_record
from plugins.memory.holographic.store import MemoryStore

FACT_DB = get_hermes_home() / "memory_store.db"
LEGACY_FACT_DB_TABLE = "fact_records"
FACT_TABLE = "facts"

MIGRATION_COLUMNS: list[tuple[str, str]] = [
    ("source", "TEXT DEFAULT 'unknown'"),
    ("fact_type", "TEXT DEFAULT 'fact'"),
    ("fact_star", "INTEGER DEFAULT 0"),
    ("fact_plus", "INTEGER DEFAULT 0"),
    ("verify_before_use", "INTEGER DEFAULT 0"),
    ("importance_level", "TEXT DEFAULT 'normal'"),
    ("star_reason", "TEXT"),
    ("learning_policy_id", "TEXT"),
    ("verified_by", "TEXT"),
    ("last_verified_at", "TEXT"),
    ("verification_status", "TEXT DEFAULT 'unverified'"),
    ("confidence_score", "REAL DEFAULT 0.5"),
    ("impact_scope", "TEXT"),
    ("rollback_required", "INTEGER DEFAULT 0"),
    ("related_entities", "TEXT"),
    ("created_by", "TEXT"),
    ("updated_by", "TEXT"),
    ("notes", "TEXT"),
]

MIGRATION_INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_facts_trust    ON facts(trust_score DESC)",
    "CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category)",
    "CREATE INDEX IF NOT EXISTS idx_facts_type     ON facts(fact_type)",
    "CREATE INDEX IF NOT EXISTS idx_facts_star     ON facts(fact_star)",
    "CREATE INDEX IF NOT EXISTS idx_facts_verify   ON facts(verify_before_use)",
    "CREATE INDEX IF NOT EXISTS idx_facts_vstatus  ON facts(verification_status)",
    "CREATE INDEX IF NOT EXISTS idx_entities_name  ON entities(name)",
]

MIGRATION_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS entities (
    entity_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    entity_type TEXT DEFAULT 'unknown',
    aliases     TEXT DEFAULT '',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_entities (
    fact_id   INTEGER REFERENCES facts(fact_id),
    entity_id INTEGER REFERENCES entities(entity_id),
    PRIMARY KEY (fact_id, entity_id)
);

CREATE TABLE IF NOT EXISTS memory_banks (
    bank_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name  TEXT NOT NULL UNIQUE,
    vector     BLOB NOT NULL,
    dim        INTEGER NOT NULL,
    fact_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts
    USING fts5(content, tags, content=facts, content_rowid=fact_id);

CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(rowid, content, tags)
        VALUES (new.fact_id, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, content, tags)
        VALUES ('delete', old.fact_id, old.content, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, content, tags)
        VALUES ('delete', old.fact_id, old.content, old.tags);
    INSERT INTO facts_fts(rowid, content, tags)
        VALUES (new.fact_id, new.content, new.tags);
END;
"""


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_mapping(value: Any) -> bool:
    return isinstance(value, dict)


def _coerce_tags_text(tags: Any) -> str:
    if tags is None:
        return ""
    if isinstance(tags, str):
        return tags
    if isinstance(tags, list):
        return ",".join(str(tag).strip() for tag in tags if str(tag).strip())
    return str(tags)


def _strip_internal_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(record)
    cleaned.pop("retrieval_count", None)
    cleaned.pop("helpful_count", None)
    cleaned.pop("hrr_vector", None)
    return cleaned


def get_fact_store(db_path: str | Path | None = None) -> MemoryStore:
    return MemoryStore(db_path=db_path or FACT_DB)


def get_fact_record(fact_id: int, db_path: str | Path | None = None) -> dict | None:
    store = get_fact_store(db_path)
    try:
        return store.get_fact(int(fact_id))
    finally:
        store.close()


def list_fact_records(
    db_path: str | Path | None = None,
    *,
    category: str | None = None,
    min_trust: float = 0.0,
    limit: int = 50,
    fact_type: str | None = None,
    fact_star: bool | None = None,
    fact_plus: bool | None = None,
    verify_before_use: bool | None = None,
    verification_status: str | None = None,
) -> dict:
    store = get_fact_store(db_path)
    try:
        facts = store.list_facts(
            category=category,
            min_trust=min_trust,
            limit=limit,
            fact_type=fact_type,
            fact_star=fact_star,
            fact_plus=fact_plus,
            verify_before_use=verify_before_use,
            verification_status=verification_status,
        )
        return {
            "ok": True,
            "status": "ok",
            "count": len(facts),
            "limit": limit,
            "filters": {
                "category": category,
                "min_trust": min_trust,
                "fact_type": fact_type,
                "fact_star": fact_star,
                "fact_plus": fact_plus,
                "verify_before_use": verify_before_use,
                "verification_status": verification_status,
            },
            "facts": facts,
        }
    finally:
        store.close()


def validate_fact_payload(payload: Dict[str, Any], *, strict: bool = True) -> Dict[str, Any]:
    normalized = normalize_fact_record(_strip_internal_fields(payload))
    result = validate_fact_record(normalized, strict=strict)
    if not result.ok:
        raise ValueError("; ".join(result.errors))
    return normalized


def create_fact_record(payload: Dict[str, Any], db_path: str | Path | None = None) -> dict:
    if not _is_mapping(payload):
        raise ValueError("payload must be an object/dict")
    if not str(payload.get("content", "")).strip():
        raise ValueError("content must not be empty")

    store = get_fact_store(db_path)
    try:
        tags = _coerce_tags_text(payload.get("tags"))
        content = str(payload.get("content", "")).strip()
        category = str(payload.get("category", "general"))
        metadata = {
            key: value
            for key, value in payload.items()
            if key not in {"content", "category", "tags", "fact_id"}
        }
        fact_id = store.add_fact(content, category=category, tags=tags, **metadata)
        return {
            "ok": True,
            "status": "created",
            "fact_id": fact_id,
            "fact": store.get_fact(fact_id),
        }
    finally:
        store.close()


def update_fact_record(
    fact_id: int,
    payload: Dict[str, Any],
    db_path: str | Path | None = None,
) -> dict:
    if not _is_mapping(payload):
        raise ValueError("payload must be an object/dict")

    store = get_fact_store(db_path)
    try:
        tags = payload.get("tags")
        tags_text = _coerce_tags_text(tags) if tags is not None else None
        content = payload.get("content")
        content_text = str(content).strip() if content is not None else None
        category = payload.get("category")
        category_text = str(category).strip() if category is not None else None
        metadata = {
            key: value
            for key, value in payload.items()
            if key not in {"content", "category", "tags", "fact_id"}
        }
        updated = store.update_fact(
            int(fact_id),
            content=content_text,
            tags=tags_text,
            category=category_text,
            **metadata,
        )
        if not updated:
            raise KeyError(f"fact_id {fact_id} not found")
        fact = store.get_fact(int(fact_id))
        return {
            "ok": True,
            "status": "updated",
            "fact_id": int(fact_id),
            "fact": fact,
        }
    finally:
        store.close()


def delete_fact_record(fact_id: int, db_path: str | Path | None = None) -> dict:
    store = get_fact_store(db_path)
    try:
        removed = store.remove_fact(int(fact_id))
        if not removed:
            raise KeyError(f"fact_id {fact_id} not found")
        return {
            "ok": True,
            "status": "deleted",
            "fact_id": int(fact_id),
        }
    finally:
        store.close()


def migrate_fact_store_db(db_path: str | Path = FACT_DB) -> dict:
    """Safely upgrade an existing SQLite fact store to the Fact+* schema."""

    db_path = Path(db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            ).fetchall()
        }
        renamed_legacy_table = False
        if FACT_TABLE not in tables:
            if LEGACY_FACT_DB_TABLE in tables:
                conn.execute(f"ALTER TABLE {LEGACY_FACT_DB_TABLE} RENAME TO {FACT_TABLE}")
                renamed_legacy_table = True
            else:
                raise RuntimeError(f"Neither '{FACT_TABLE}' nor '{LEGACY_FACT_DB_TABLE}' exists in {db_path}")

        existing_columns = {
            row[1]
            for row in conn.execute(f"PRAGMA table_info({FACT_TABLE})").fetchall()
        }
        added_columns: list[str] = []
        for column, ddl in MIGRATION_COLUMNS:
            if column not in existing_columns:
                conn.execute(f"ALTER TABLE {FACT_TABLE} ADD COLUMN {column} {ddl}")
                added_columns.append(column)

        conn.execute(
            f"UPDATE {FACT_TABLE} SET impact_scope = COALESCE(impact_scope, '[\"none\"]') "
            f"WHERE impact_scope IS NULL OR impact_scope = ''"
        )
        conn.execute(
            f"UPDATE {FACT_TABLE} SET related_entities = COALESCE(related_entities, '[]') "
            f"WHERE related_entities IS NULL OR related_entities = ''"
        )

        conn.executescript(MIGRATION_TABLES_SQL)
        conn.execute("INSERT INTO facts_fts(facts_fts) VALUES('rebuild')")

        for index_sql in MIGRATION_INDEXES:
            conn.execute(index_sql)

        conn.commit()
        return {
            "ok": True,
            "db_path": str(db_path),
            "renamed_legacy_table": renamed_legacy_table,
            "added_columns": added_columns,
            "index_count": len(MIGRATION_INDEXES),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dump_fact_record(record: Dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True)
