-- Hermes Fact Store SQLite migration for Fact / Fact+ / Fact* / Fact+*
-- Canonical schema-upgrade companion for fact_migrate.py.
--
-- If a legacy database still uses fact_records, rename it first:
--   ALTER TABLE fact_records RENAME TO facts;
--
-- Then apply the column additions below against the facts table.

BEGIN TRANSACTION;

ALTER TABLE facts ADD COLUMN source TEXT DEFAULT 'unknown';
ALTER TABLE facts ADD COLUMN fact_type TEXT DEFAULT 'fact';
ALTER TABLE facts ADD COLUMN fact_star INTEGER DEFAULT 0;
ALTER TABLE facts ADD COLUMN fact_plus INTEGER DEFAULT 0;
ALTER TABLE facts ADD COLUMN verify_before_use INTEGER DEFAULT 0;
ALTER TABLE facts ADD COLUMN importance_level TEXT DEFAULT 'normal';
ALTER TABLE facts ADD COLUMN star_reason TEXT;
ALTER TABLE facts ADD COLUMN learning_policy_id TEXT;
ALTER TABLE facts ADD COLUMN verified_by TEXT;
ALTER TABLE facts ADD COLUMN last_verified_at TEXT;
ALTER TABLE facts ADD COLUMN verification_status TEXT DEFAULT 'unverified';
ALTER TABLE facts ADD COLUMN confidence_score REAL DEFAULT 0.5;
ALTER TABLE facts ADD COLUMN impact_scope TEXT;
ALTER TABLE facts ADD COLUMN rollback_required INTEGER DEFAULT 0;
ALTER TABLE facts ADD COLUMN related_entities TEXT;
ALTER TABLE facts ADD COLUMN created_by TEXT;
ALTER TABLE facts ADD COLUMN updated_by TEXT;
ALTER TABLE facts ADD COLUMN notes TEXT;

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

CREATE INDEX IF NOT EXISTS idx_facts_trust    ON facts(trust_score DESC);
CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
CREATE INDEX IF NOT EXISTS idx_facts_type     ON facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_facts_star     ON facts(fact_star);
CREATE INDEX IF NOT EXISTS idx_facts_verify   ON facts(verify_before_use);
CREATE INDEX IF NOT EXISTS idx_facts_vstatus  ON facts(verification_status);
CREATE INDEX IF NOT EXISTS idx_entities_name  ON entities(name);

INSERT INTO facts_fts(facts_fts) VALUES('rebuild');

COMMIT;
