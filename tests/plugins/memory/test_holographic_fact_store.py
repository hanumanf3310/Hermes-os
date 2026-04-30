from __future__ import annotations

import json
import sqlite3

import pytest

from plugins.memory.holographic import HolographicMemoryProvider
from plugins.memory.holographic.store import MemoryStore


def _table_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(facts)").fetchall()
    return {row[1] for row in rows}


def test_fact_store_schema_has_fact_star_fields(tmp_path):
    db_path = tmp_path / "memory_store.db"
    store = MemoryStore(db_path=db_path)
    cols = _table_columns(store._conn)

    expected = {
        "source",
        "fact_type",
        "fact_star",
        "fact_plus",
        "verify_before_use",
        "importance_level",
        "star_reason",
        "learning_policy_id",
        "verified_by",
        "last_verified_at",
        "verification_status",
        "confidence_score",
        "impact_scope",
        "rollback_required",
        "related_entities",
        "created_by",
        "updated_by",
        "notes",
    }
    assert expected.issubset(cols)


def test_add_and_filter_fact_star_and_fact_plus(tmp_path):
    store = MemoryStore(db_path=tmp_path / "memory_store.db")

    regular_id = store.add_fact("Boss likes concise summaries", category="user_pref")
    plus_id = store.add_fact(
        "Track this for learning",
        category="project",
        fact_type="fact_plus",
        learning_policy_id="policy-001",
        impact_scope='["learning"]',
    )
    star_id = store.add_fact(
        "Hermes OS-impacting change must be verified before use",
        category="policy",
        fact_type="fact_star",
        star_reason="affects routing and rollback safety",
        impact_scope='["hermes_os", "safety"]',
        verified_by="Boss",
    )

    regular = store.list_facts(limit=10, fact_type="fact")
    stars = store.list_facts(limit=10, fact_star=True)
    pluses = store.list_facts(limit=10, fact_plus=True)

    assert {f["fact_id"] for f in regular} == {regular_id}
    assert {f["fact_id"] for f in stars} == {star_id}
    assert {f["fact_id"] for f in pluses} == {plus_id}

    star = stars[0]
    assert star["fact_type"] == "fact_star"
    assert star["fact_star"] is True
    assert star["verify_before_use"] is True
    assert star["importance_level"] == "critical"
    assert star["star_reason"] == "affects routing and rollback safety"
    assert star["impact_scope"] == ["hermes_os", "safety"]

    search = store.search_facts("verified", fact_star=True)
    assert [f["fact_id"] for f in search] == [star_id]


def test_fact_plus_star_requires_learn_and_verify(tmp_path):
    store = MemoryStore(db_path=tmp_path / "memory_store.db")

    fact_id = store.add_fact(
        "System-impacting change that should also feed learning",
        category="policy",
        fact_type="fact_plus_star",
        fact_plus=True,
        fact_star=True,
        verify_before_use=True,
        importance_level="critical",
        star_reason="affects Hermes OS and learning policy",
        learning_policy_id="policy-002",
        verification_status="verified",
        verified_by="Boss",
        impact_scope='["policy", "routing", "hermes_os", "learning"]',
    )

    rows = store.list_facts(limit=10, fact_type="fact_plus_star")
    assert len(rows) == 1
    row = rows[0]
    assert row["fact_id"] == fact_id
    assert row["fact_plus"] is True
    assert row["fact_star"] is True
    assert row["verify_before_use"] is True
    assert row["importance_level"] == "critical"
    assert row["verification_status"] == "verified"
    assert row["learning_policy_id"] == "policy-002"


def test_validator_rejects_invalid_fact_plus_star(tmp_path):
    store = MemoryStore(db_path=tmp_path / "memory_store.db")

    with pytest.raises(ValueError):
        store.add_fact(
            "Broken composite fact",
            category="policy",
            fact_type="fact_plus_star",
            fact_plus=True,
            fact_star=True,
            verify_before_use=True,
            importance_level="critical",
            star_reason=None,
            learning_policy_id=None,
            verification_status="verified",
        )


def test_update_fact_can_promote_to_fact_star(tmp_path):
    store = MemoryStore(db_path=tmp_path / "memory_store.db")
    fact_id = store.add_fact("temporary note", category="general")

    updated = store.update_fact(
        fact_id,
        fact_type="fact_star",
        star_reason="now affects Hermes OS behavior",
        verification_status="verified",
        verified_by="Boss",
    )
    assert updated is True

    rows = store.list_facts(limit=10, fact_star=True)
    assert len(rows) == 1
    fact = rows[0]
    assert fact["fact_id"] == fact_id
    assert fact["fact_type"] == "fact_star"
    assert fact["verify_before_use"] is True
    assert fact["verification_status"] == "verified"
    assert fact["verified_by"] == "Boss"


def test_provider_handles_fact_star_fields(tmp_path):
    provider = HolographicMemoryProvider(config={"db_path": str(tmp_path / "memory_store.db")})
    provider.initialize(session_id="test-session")

    result = json.loads(
        provider.handle_tool_call(
            "fact_store",
            {
                "action": "add",
                "content": "Fact star via tool",
                "category": "policy",
                "fact_type": "fact_star",
                "star_reason": "must verify before use",
                "impact_scope": "hermes_os,safety",
            },
        )
    )
    assert result["fact_id"] >= 1
    assert result["status"] == "added"

    listed = json.loads(
        provider.handle_tool_call(
            "fact_store",
            {
                "action": "list",
                "fact_star": True,
                "limit": 10,
            },
        )
    )
    assert listed["count"] == 1
    fact = listed["facts"][0]
    assert fact["fact_star"] is True
    assert fact["verify_before_use"] is True
    assert fact["importance_level"] == "critical"
