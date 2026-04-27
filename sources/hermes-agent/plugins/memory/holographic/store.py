"""
SQLite-backed fact store with entity resolution and trust scoring.
Single-user Hermes memory store plugin.
"""

import re
import sqlite3
import threading
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from . import holographic as hrr
except ImportError:
    import holographic as hrr  # type: ignore[no-redef]

MEMORY_GRAPH_ROOT = Path("/home/hanuman3310/hermes-workspace/memory-graph")
if str(MEMORY_GRAPH_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORY_GRAPH_ROOT))

try:
    from fact_validator import normalize_fact_record, validate_fact_record
except Exception as exc:  # pragma: no cover - import-time guard
    raise RuntimeError(f"Unable to import Fact+* validator: {exc}") from exc

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    fact_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    content         TEXT NOT NULL UNIQUE,
    category        TEXT DEFAULT 'general',
    tags            TEXT DEFAULT '',
    source          TEXT DEFAULT 'unknown',
    fact_type       TEXT DEFAULT 'fact',
    fact_star       INTEGER DEFAULT 0,
    fact_plus       INTEGER DEFAULT 0,
    verify_before_use INTEGER DEFAULT 0,
    importance_level TEXT DEFAULT 'normal',
    star_reason     TEXT,
    learning_policy_id TEXT,
    verified_by     TEXT,
    last_verified_at TEXT,
    verification_status TEXT DEFAULT 'unverified',
    trust_score     REAL DEFAULT 0.5,
    confidence_score REAL DEFAULT 0.5,
    retrieval_count INTEGER DEFAULT 0,
    helpful_count   INTEGER DEFAULT 0,
    impact_scope    TEXT DEFAULT '["none"]',
    rollback_required INTEGER DEFAULT 0,
    related_entities TEXT DEFAULT '[]',
    created_by      TEXT,
    updated_by      TEXT,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hrr_vector      BLOB
);

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

CREATE INDEX IF NOT EXISTS idx_facts_trust    ON facts(trust_score DESC);
CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
CREATE INDEX IF NOT EXISTS idx_facts_type     ON facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_facts_star     ON facts(fact_star);
CREATE INDEX IF NOT EXISTS idx_facts_verify   ON facts(verify_before_use);
CREATE INDEX IF NOT EXISTS idx_facts_vstatus  ON facts(verification_status);
CREATE INDEX IF NOT EXISTS idx_entities_name  ON entities(name);

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

CREATE TABLE IF NOT EXISTS memory_banks (
    bank_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name  TEXT NOT NULL UNIQUE,
    vector     BLOB NOT NULL,
    dim        INTEGER NOT NULL,
    fact_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Trust adjustment constants
_HELPFUL_DELTA   =  0.05
_UNHELPFUL_DELTA = -0.10
_TRUST_MIN       =  0.0
_TRUST_MAX       =  1.0

# Entity extraction patterns
_RE_CAPITALIZED  = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')
_RE_DOUBLE_QUOTE = re.compile(r'"([^"]+)"')
_RE_SINGLE_QUOTE = re.compile(r"'([^']+)'")
_RE_AKA          = re.compile(
    r'(\w+(?:\s+\w+)*)\s+(?:aka|also known as)\s+(\w+(?:\s+\w+)*)',
    re.IGNORECASE,
)


def _clamp_trust(value: float) -> float:
    return max(_TRUST_MIN, min(_TRUST_MAX, value))


def _json_text(value, default):
    if value is None:
        return json.dumps(default)
    if isinstance(value, str):
        try:
            json.loads(value)
            return value
        except Exception:
            return json.dumps(default)
    return json.dumps(value)


def _json_load(value, default):
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    if isinstance(value, str) and value:
        try:
            return json.loads(value)
        except Exception:
            return default
    return default


def _to_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return default


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validated_fact_or_raise(candidate: dict) -> dict:
    candidate = dict(candidate)
    candidate.pop("helpful_count", None)
    candidate.pop("retrieval_count", None)
    normalized = normalize_fact_record(candidate)
    result = validate_fact_record(normalized, strict=True)
    if not result.ok:
        raise ValueError("; ".join(result.errors))
    return normalized


_FACT_TYPE_DEFAULTS = {
    "fact": {
        "fact_star": False,
        "fact_plus": False,
        "verify_before_use": False,
        "importance_level": "normal",
    },
    "fact_plus": {
        "fact_star": False,
        "fact_plus": True,
        "verify_before_use": False,
        "importance_level": "important",
    },
    "fact_star": {
        "fact_star": True,
        "fact_plus": False,
        "verify_before_use": True,
        "importance_level": "critical",
    },
}


class MemoryStore:
    """SQLite-backed fact store with entity resolution and trust scoring."""

    def __init__(
        self,
        db_path: "str | Path | None" = None,
        default_trust: float = 0.5,
        hrr_dim: int = 1024,
    ) -> None:
        if db_path is None:
            from hermes_constants import get_hermes_home
            db_path = str(get_hermes_home() / "memory_store.db")
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.default_trust = _clamp_trust(default_trust)
        self.hrr_dim = hrr_dim
        self._hrr_available = hrr._HAS_NUMPY
        self._conn: sqlite3.Connection = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=10.0,
        )
        self._lock = threading.RLock()
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create tables, indexes, and triggers if they do not exist. Enable WAL mode."""
        self._conn.execute("PRAGMA journal_mode=WAL")

        # Create only the core tables first so legacy databases can be migrated
        # before we attempt to add indexes or FTS triggers on new columns.
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS facts (
                fact_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                content         TEXT NOT NULL UNIQUE,
                category        TEXT DEFAULT 'general',
                tags            TEXT DEFAULT '',
                trust_score     REAL DEFAULT 0.5,
                retrieval_count INTEGER DEFAULT 0,
                helpful_count   INTEGER DEFAULT 0,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hrr_vector      BLOB
            );

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
            """
        )

        # Safe migration path for existing databases: add any missing columns.
        columns = {row[1] for row in self._conn.execute("PRAGMA table_info(facts)").fetchall()}
        migrations = [
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
        for column, ddl in migrations:
            if column not in columns:
                self._conn.execute(f"ALTER TABLE facts ADD COLUMN {column} {ddl}")

        self._conn.execute(
            "UPDATE facts SET impact_scope = COALESCE(impact_scope, '[\"none\"]') "
            "WHERE impact_scope IS NULL OR impact_scope = ''"
        )
        self._conn.execute(
            "UPDATE facts SET related_entities = COALESCE(related_entities, '[]') "
            "WHERE related_entities IS NULL OR related_entities = ''"
        )

        # Add indexes/triggers after all columns exist.
        self._conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_facts_trust    ON facts(trust_score DESC);
            CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
            CREATE INDEX IF NOT EXISTS idx_facts_type     ON facts(fact_type);
            CREATE INDEX IF NOT EXISTS idx_facts_star     ON facts(fact_star);
            CREATE INDEX IF NOT EXISTS idx_facts_verify   ON facts(verify_before_use);
            CREATE INDEX IF NOT EXISTS idx_facts_vstatus  ON facts(verification_status);
            CREATE INDEX IF NOT EXISTS idx_entities_name  ON entities(name);

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
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _normalize_fact_payload(self, payload: dict) -> dict:
        """Normalize fact metadata into a consistent storage shape."""
        fact_type = payload.get("fact_type")
        fact_star = _to_bool(payload.get("fact_star"), False)
        fact_plus = _to_bool(payload.get("fact_plus"), False)
        verify_before_use = _to_bool(payload.get("verify_before_use"), False)
        importance_level = payload.get("importance_level")
        star_reason = payload.get("star_reason")
        learning_policy_id = payload.get("learning_policy_id")

        if fact_type is None:
            if fact_star and fact_plus:
                fact_type = "fact_plus_star"
            elif fact_star:
                fact_type = "fact_star"
            elif fact_plus:
                fact_type = "fact_plus"
            else:
                fact_type = "fact"

        if fact_type not in _FACT_TYPE_DEFAULTS and fact_type != "fact_plus_star":
            raise ValueError(f"invalid fact_type: {fact_type}")

        defaults = {
            "fact_plus_star": {
                "fact_star": True,
                "fact_plus": True,
                "verify_before_use": True,
                "importance_level": "critical",
            },
            **_FACT_TYPE_DEFAULTS,
        }[fact_type]

        fact_star = _to_bool(fact_star or defaults["fact_star"])
        fact_plus = _to_bool(fact_plus or defaults["fact_plus"])
        verify_before_use = _to_bool(verify_before_use or defaults["verify_before_use"])
        importance_level = importance_level or defaults["importance_level"]

        if fact_type == "fact_star":
            fact_star = True
            fact_plus = False
            verify_before_use = True
            importance_level = "critical"
        elif fact_type == "fact_plus":
            fact_star = False
            fact_plus = True
        elif fact_type == "fact_plus_star":
            fact_star = True
            fact_plus = True
            verify_before_use = True
            importance_level = "critical"

        related_entities = payload.get("related_entities")
        if related_entities is None:
            related_entities = []
        elif isinstance(related_entities, str):
            parsed_related = _json_load(related_entities, None)
            if isinstance(parsed_related, list):
                related_entities = [item for item in parsed_related if isinstance(item, str)]
            else:
                related_entities = [item.strip() for item in related_entities.split(",") if item.strip()]

        impact_scope = payload.get("impact_scope")
        if impact_scope is None:
            impact_scope = ["none"]
        elif isinstance(impact_scope, str):
            parsed_scope = _json_load(impact_scope, None)
            if isinstance(parsed_scope, list):
                impact_scope = parsed_scope
            else:
                impact_scope = [item.strip() for item in impact_scope.split(",") if item.strip()]
            if not impact_scope:
                impact_scope = ["none"]

        verification_status = payload.get("verification_status") or ("verified" if fact_star else "unverified")
        last_verified_at = payload.get("last_verified_at")
        if not last_verified_at and verification_status == "verified" and fact_star:
            last_verified_at = _now_iso()

        return {
            "source": payload.get("source", "unknown"),
            "fact_type": fact_type,
            "fact_star": int(fact_star),
            "fact_plus": int(fact_plus),
            "verify_before_use": int(verify_before_use),
            "importance_level": importance_level,
            "star_reason": star_reason,
            "learning_policy_id": learning_policy_id,
            "verified_by": payload.get("verified_by"),
            "last_verified_at": last_verified_at,
            "verification_status": verification_status,
            "confidence_score": float(payload.get("confidence_score", 0.5)),
            "impact_scope": _json_text(impact_scope, ["none"]),
            "rollback_required": int(_to_bool(payload.get("rollback_required"), False)),
            "related_entities": _json_text(related_entities, []),
            "created_by": payload.get("created_by"),
            "updated_by": payload.get("updated_by"),
            "notes": payload.get("notes"),
        }

    def add_fact(
        self,
        content: str,
        category: str = "general",
        tags: str = "",
        **metadata,
    ) -> int:
        """Insert a fact and return its fact_id.

        Deduplicates by content (UNIQUE constraint). On duplicate, returns
        the existing fact_id and updates metadata if explicit fact fields were
        provided. Extracts entities from the content and links them to the fact.
        """
        with self._lock:
            content = content.strip()
            if not content:
                raise ValueError("content must not be empty")

            normalized = self._normalize_fact_payload(metadata)
            candidate = {
                "fact_id": 1,
                "content": content,
                "category": category,
                "tags": tags.split(",") if tags else [],
                "source": normalized["source"],
                "fact_type": normalized["fact_type"],
                "fact_star": bool(normalized["fact_star"]),
                "fact_plus": bool(normalized["fact_plus"]),
                "verify_before_use": bool(normalized["verify_before_use"]),
                "importance_level": normalized["importance_level"],
                "star_reason": normalized["star_reason"],
                "learning_policy_id": normalized["learning_policy_id"],
                "verified_by": normalized["verified_by"],
                "last_verified_at": normalized["last_verified_at"],
                "verification_status": normalized["verification_status"],
                "trust_score": self.default_trust,
                "confidence_score": normalized["confidence_score"],
                "impact_scope": _json_load(normalized["impact_scope"], ["none"]),
                "rollback_required": bool(normalized["rollback_required"]),
                "related_entities": _json_load(normalized["related_entities"], []),
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "created_by": normalized["created_by"],
                "updated_by": normalized["updated_by"],
                "notes": normalized["notes"],
            }
            _validated_fact_or_raise(candidate)
            try:
                cur = self._conn.execute(
                    """
                    INSERT INTO facts (
                        content, category, tags, source, fact_type, fact_star, fact_plus,
                        verify_before_use, importance_level, star_reason, learning_policy_id,
                        verified_by, last_verified_at, verification_status, trust_score,
                        confidence_score, retrieval_count, helpful_count, impact_scope,
                        rollback_required, related_entities, created_by, updated_by, notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        content,
                        category,
                        tags,
                        normalized["source"],
                        normalized["fact_type"],
                        normalized["fact_star"],
                        normalized["fact_plus"],
                        normalized["verify_before_use"],
                        normalized["importance_level"],
                        normalized["star_reason"],
                        normalized["learning_policy_id"],
                        normalized["verified_by"],
                        normalized["last_verified_at"],
                        normalized["verification_status"],
                        self.default_trust,
                        normalized["confidence_score"],
                        0,
                        0,
                        normalized["impact_scope"],
                        normalized["rollback_required"],
                        normalized["related_entities"],
                        normalized["created_by"],
                        normalized["updated_by"],
                        normalized["notes"],
                    ),
                )
                self._conn.commit()
                fact_id: int = cur.lastrowid  # type: ignore[assignment]
            except sqlite3.IntegrityError:
                row = self._conn.execute(
                    "SELECT fact_id FROM facts WHERE content = ?", (content,)
                ).fetchone()
                if row is None:
                    raise
                fact_id = int(row["fact_id"])
                if metadata:
                    self.update_fact(fact_id, category=category, tags=tags, **metadata)
                return fact_id

            # Entity extraction and linking
            extracted_entities = self._extract_entities(content)
            provided_entities = _json_load(normalized["related_entities"], [])
            all_entities = []
            seen = set()
            for name in [*extracted_entities, *provided_entities]:
                if name and name.lower() not in seen:
                    seen.add(name.lower())
                    all_entities.append(name)

            if all_entities:
                self._conn.execute("DELETE FROM fact_entities WHERE fact_id = ?", (fact_id,))
                for name in all_entities:
                    entity_id = self._resolve_entity(name)
                    self._link_fact_entity(fact_id, entity_id)
                self._conn.commit()

            # Compute HRR vector after entity linking
            self._compute_hrr_vector(fact_id, content)
            self._rebuild_bank(category)

            return fact_id

    def search_facts(
        self,
        query: str,
        category: str | None = None,
        min_trust: float = 0.3,
        limit: int = 10,
        fact_type: str | None = None,
        fact_star: bool | None = None,
        fact_plus: bool | None = None,
        verify_before_use: bool | None = None,
        verification_status: str | None = None,
    ) -> list[dict]:
        """Full-text search over facts using FTS5.

        Returns a list of fact dicts ordered by FTS5 rank, then trust_score
        descending. Also increments retrieval_count for matched facts.
        """
        with self._lock:
            query = query.strip()
            if not query:
                return []

            params: list = [query, min_trust]
            clauses = ["f.trust_score >= ?"]
            if category is not None:
                clauses.append("f.category = ?")
                params.append(category)
            if fact_type is not None:
                clauses.append("f.fact_type = ?")
                params.append(fact_type)
            if fact_star is not None:
                clauses.append("f.fact_star = ?")
                params.append(1 if fact_star else 0)
            if fact_plus is not None:
                clauses.append("f.fact_plus = ?")
                params.append(1 if fact_plus else 0)
            if verify_before_use is not None:
                clauses.append("f.verify_before_use = ?")
                params.append(1 if verify_before_use else 0)
            if verification_status is not None:
                clauses.append("f.verification_status = ?")
                params.append(verification_status)
            params.append(limit)

            sql = f"""
                SELECT f.*, fts.rank AS fts_rank
                FROM facts f
                JOIN facts_fts fts ON fts.rowid = f.fact_id
                WHERE facts_fts MATCH ?
                  AND {' AND '.join(clauses)}
                ORDER BY fts.rank, f.trust_score DESC
                LIMIT ?
            """

            rows = self._conn.execute(sql, params).fetchall()
            results = [self._row_to_dict(r) for r in rows]

            if results:
                ids = [r["fact_id"] for r in results]
                placeholders = ",".join("?" * len(ids))
                self._conn.execute(
                    f"UPDATE facts SET retrieval_count = retrieval_count + 1 WHERE fact_id IN ({placeholders})",
                    ids,
                )
                self._conn.commit()

            return results

    def update_fact(
        self,
        fact_id: int,
        content: str | None = None,
        trust_delta: float | None = None,
        tags: str | None = None,
        category: str | None = None,
        **metadata,
    ) -> bool:
        """Partially update a fact. Trust is clamped to [0, 1].

        Returns True if the row existed, False otherwise.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM facts WHERE fact_id = ?", (fact_id,)
            ).fetchone()
            if row is None:
                return False

            assignments: list[str] = ["updated_at = CURRENT_TIMESTAMP"]
            params: list = []

            if content is not None:
                assignments.append("content = ?")
                params.append(content.strip())
            if trust_delta is not None:
                new_trust = _clamp_trust(float(row["trust_score"]) + float(trust_delta))
                assignments.append("trust_score = ?")
                params.append(new_trust)
            if tags is not None:
                assignments.append("tags = ?")
                params.append(tags)
            if category is not None:
                assignments.append("category = ?")
                params.append(category)

            if metadata:
                normalized = self._normalize_fact_payload(metadata)
                candidate = self._row_to_dict(row)
                candidate.update(
                    {
                        "content": content.strip() if content is not None else candidate["content"],
                        "category": category if category is not None else candidate["category"],
                        "tags": tags.split(",") if tags is not None and tags else candidate["tags"],
                        "source": normalized["source"],
                        "fact_type": normalized["fact_type"],
                        "fact_star": bool(normalized["fact_star"]),
                        "fact_plus": bool(normalized["fact_plus"]),
                        "verify_before_use": bool(normalized["verify_before_use"]),
                        "importance_level": normalized["importance_level"],
                        "star_reason": normalized["star_reason"],
                        "learning_policy_id": normalized["learning_policy_id"],
                        "verified_by": normalized["verified_by"],
                        "last_verified_at": normalized["last_verified_at"],
                        "verification_status": normalized["verification_status"],
                        "confidence_score": normalized["confidence_score"],
                        "impact_scope": _json_load(normalized["impact_scope"], ["none"]),
                        "rollback_required": bool(normalized["rollback_required"]),
                        "related_entities": _json_load(normalized["related_entities"], []),
                        "created_by": normalized["created_by"],
                        "updated_by": normalized["updated_by"],
                        "notes": normalized["notes"],
                    }
                )
                candidate["fact_id"] = fact_id
                candidate["updated_at"] = _now_iso()
                _validated_fact_or_raise(candidate)
                for key in [
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
                ]:
                    assignments.append(f"{key} = ?")
                    params.append(normalized[key])

            if len(assignments) == 1:
                return True

            params.append(fact_id)
            self._conn.execute(
                f"UPDATE facts SET {', '.join(assignments)} WHERE fact_id = ?",
                params,
            )

            if content is not None or tags is not None:
                # Keep the FTS mirror synchronized for content/tags changes.
                self._conn.execute(
                    "DELETE FROM facts_fts WHERE rowid = ?", (fact_id,)
                )
                self._conn.execute(
                    "INSERT INTO facts_fts(rowid, content, tags) VALUES (?, ?, ?)",
                    (fact_id, content.strip() if content is not None else row["content"], tags if tags is not None else row["tags"]),
                )

            if content is not None or category is not None:
                self._rebuild_bank(category or row["category"])

            self._conn.commit()
            return True

    def remove_fact(self, fact_id: int) -> bool:
        """Delete a fact and its entity links. Returns True if the row existed."""
        with self._lock:
            row = self._conn.execute(
                "SELECT fact_id, category FROM facts WHERE fact_id = ?", (fact_id,)
            ).fetchone()
            if row is None:
                return False

            self._conn.execute(
                "DELETE FROM fact_entities WHERE fact_id = ?", (fact_id,)
            )
            self._conn.execute("DELETE FROM facts WHERE fact_id = ?", (fact_id,))
            self._conn.commit()
            self._rebuild_bank(row["category"])
            return True

    def list_facts(
        self,
        category: str | None = None,
        min_trust: float = 0.0,
        limit: int = 50,
        fact_type: str | None = None,
        fact_star: bool | None = None,
        fact_plus: bool | None = None,
        verify_before_use: bool | None = None,
        verification_status: str | None = None,
    ) -> list[dict]:
        """Browse facts ordered by trust_score descending.

        Optionally filter by category, fact type, verification flags, and
        minimum trust score.
        """
        with self._lock:
            clauses = ["trust_score >= ?"]
            params: list = [min_trust]
            if category is not None:
                clauses.append("category = ?")
                params.append(category)
            if fact_type is not None:
                clauses.append("fact_type = ?")
                params.append(fact_type)
            if fact_star is not None:
                clauses.append("fact_star = ?")
                params.append(1 if fact_star else 0)
            if fact_plus is not None:
                clauses.append("fact_plus = ?")
                params.append(1 if fact_plus else 0)
            if verify_before_use is not None:
                clauses.append("verify_before_use = ?")
                params.append(1 if verify_before_use else 0)
            if verification_status is not None:
                clauses.append("verification_status = ?")
                params.append(verification_status)
            params.append(limit)

            sql = f"""
                SELECT *
                FROM facts
                WHERE {' AND '.join(clauses)}
                ORDER BY trust_score DESC, updated_at DESC
                LIMIT ?
            """
            rows = self._conn.execute(sql, params).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def record_feedback(self, fact_id: int, helpful: bool) -> dict:
        """Record user feedback and adjust trust asymmetrically.

        helpful=True  -> trust += 0.05, helpful_count += 1
        helpful=False -> trust -= 0.10

        Returns a dict with fact_id, old_trust, new_trust, helpful_count.
        Raises KeyError if fact_id does not exist.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT fact_id, trust_score, helpful_count FROM facts WHERE fact_id = ?",
                (fact_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"fact_id {fact_id} not found")

            old_trust: float = row["trust_score"]
            delta = _HELPFUL_DELTA if helpful else _UNHELPFUL_DELTA
            new_trust = _clamp_trust(old_trust + delta)

            helpful_increment = 1 if helpful else 0
            self._conn.execute(
                """
                UPDATE facts
                SET trust_score    = ?,
                    helpful_count  = helpful_count + ?,
                    updated_at     = CURRENT_TIMESTAMP
                WHERE fact_id = ?
                """,
                (new_trust, helpful_increment, fact_id),
            )
            self._conn.commit()

            return {
                "fact_id":      fact_id,
                "old_trust":    old_trust,
                "new_trust":    new_trust,
                "helpful_count": row["helpful_count"] + helpful_increment,
            }

    # ------------------------------------------------------------------
    # Entity helpers
    # ------------------------------------------------------------------

    def _extract_entities(self, text: str) -> list[str]:
        """Extract entity candidates from text using simple regex rules.

        Rules applied (in order):
        1. Capitalized multi-word phrases  e.g. "John Doe"
        2. Double-quoted terms             e.g. "Python"
        3. Single-quoted terms             e.g. 'pytest'
        4. AKA patterns                    e.g. "Guido aka BDFL" -> two entities

        Returns a deduplicated list preserving first-seen order.
        """
        seen: set[str] = set()
        candidates: list[str] = []

        def _add(name: str) -> None:
            stripped = name.strip()
            if stripped and stripped.lower() not in seen:
                seen.add(stripped.lower())
                candidates.append(stripped)

        for m in _RE_CAPITALIZED.finditer(text):
            _add(m.group(1))

        for m in _RE_DOUBLE_QUOTE.finditer(text):
            _add(m.group(1))

        for m in _RE_SINGLE_QUOTE.finditer(text):
            _add(m.group(1))

        for m in _RE_AKA.finditer(text):
            _add(m.group(1))
            _add(m.group(2))

        return candidates

    def _resolve_entity(self, name: str) -> int:
        """Find an existing entity by name or alias (case-insensitive) or create one.

        Returns the entity_id.
        """
        # Exact name match
        row = self._conn.execute(
            "SELECT entity_id FROM entities WHERE name LIKE ?", (name,)
        ).fetchone()
        if row is not None:
            return int(row["entity_id"])

        # Search aliases — aliases stored as comma-separated; use LIKE with % boundaries
        alias_row = self._conn.execute(
            """
            SELECT entity_id FROM entities
            WHERE ',' || aliases || ',' LIKE '%,' || ? || ',%'
            """,
            (name,),
        ).fetchone()
        if alias_row is not None:
            return int(alias_row["entity_id"])

        # Create new entity
        cur = self._conn.execute(
            "INSERT INTO entities (name) VALUES (?)", (name,)
        )
        self._conn.commit()
        return int(cur.lastrowid)  # type: ignore[return-value]

    def _link_fact_entity(self, fact_id: int, entity_id: int) -> None:
        """Insert into fact_entities, silently ignore if the link already exists."""
        self._conn.execute(
            """
            INSERT OR IGNORE INTO fact_entities (fact_id, entity_id)
            VALUES (?, ?)
            """,
            (fact_id, entity_id),
        )
        self._conn.commit()

    def _compute_hrr_vector(self, fact_id: int, content: str) -> None:
        """Compute and store HRR vector for a fact. No-op if numpy unavailable."""
        with self._lock:
            if not self._hrr_available:
                return

            # Get entities linked to this fact
            rows = self._conn.execute(
                """
                SELECT e.name FROM entities e
                JOIN fact_entities fe ON fe.entity_id = e.entity_id
                WHERE fe.fact_id = ?
                """,
                (fact_id,),
            ).fetchall()
            entities = [row["name"] for row in rows]

            vector = hrr.encode_fact(content, entities, self.hrr_dim)
            self._conn.execute(
                "UPDATE facts SET hrr_vector = ? WHERE fact_id = ?",
                (hrr.phases_to_bytes(vector), fact_id),
            )
            self._conn.commit()

    def _rebuild_bank(self, category: str) -> None:
        """Full rebuild of a category's memory bank from all its fact vectors."""
        with self._lock:
            if not self._hrr_available:
                return

            bank_name = f"cat:{category}"
            rows = self._conn.execute(
                "SELECT hrr_vector FROM facts WHERE category = ? AND hrr_vector IS NOT NULL",
                (category,),
            ).fetchall()

            if not rows:
                self._conn.execute("DELETE FROM memory_banks WHERE bank_name = ?", (bank_name,))
                self._conn.commit()
                return

            vectors = [hrr.bytes_to_phases(row["hrr_vector"]) for row in rows]
            bank_vector = hrr.bundle(*vectors)
            fact_count = len(vectors)

            # Check SNR
            hrr.snr_estimate(self.hrr_dim, fact_count)

            self._conn.execute(
                """
                INSERT INTO memory_banks (bank_name, vector, dim, fact_count, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(bank_name) DO UPDATE SET
                    vector = excluded.vector,
                    dim = excluded.dim,
                    fact_count = excluded.fact_count,
                    updated_at = excluded.updated_at
                """,
                (bank_name, hrr.phases_to_bytes(bank_vector), self.hrr_dim, fact_count),
            )
            self._conn.commit()

    def rebuild_all_vectors(self, dim: int | None = None) -> int:
        """Recompute all HRR vectors + banks from text. For recovery/migration.

        Returns the number of facts processed.
        """
        with self._lock:
            if not self._hrr_available:
                return 0

            if dim is not None:
                self.hrr_dim = dim

            rows = self._conn.execute(
                "SELECT fact_id, content, category FROM facts"
            ).fetchall()

            categories: set[str] = set()
            for row in rows:
                self._compute_hrr_vector(row["fact_id"], row["content"])
                categories.add(row["category"])

            for category in categories:
                self._rebuild_bank(category)

            return len(rows)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def get_fact(self, fact_id: int) -> dict | None:
        """Return a single fact by id, or None if it does not exist."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM facts WHERE fact_id = ?", (int(fact_id),)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a sqlite3.Row to a plain dict."""
        data = dict(row)
        data.pop("hrr_vector", None)
        for key in ("fact_star", "fact_plus", "verify_before_use", "rollback_required"):
            if key in data and data[key] is not None:
                data[key] = bool(data[key])
        for key, default in (("tags", []), ("impact_scope", ["none"]), ("related_entities", [])):
            if key in data:
                data[key] = _json_load(data[key], default)
        return data

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
